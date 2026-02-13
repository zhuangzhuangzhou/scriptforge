from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.ai.adapters import get_adapter
from app.ai.pipeline_executor import PipelineExecutor
from app.core.progress import update_pipeline_execution
from app.core.quota import QuotaService
from app.core.credits import CreditsService, BREAKDOWN_BASE_CREDITS, SCRIPT_BASE_CREDITS
from app.models.pipeline import Pipeline, PipelineStage, PipelineExecution, PipelineExecutionLog
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@celery_app.task(bind=True)
def run_pipeline_task(
    self,
    execution_id: str,
    pipeline_id: str,
    project_id: str,
    batch_id: str,
    breakdown_id: str,
    user_id: str
):
    """执行 Pipeline"""
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            completed_stages = []
            reserved_credits = 0
            try:
                await update_pipeline_execution(
                    db,
                    execution_id,
                    status="running",
                    progress=0,
                    current_step="初始化任务"
                )
                await _add_execution_log(db, execution_id, None, "execution_started", "Pipeline执行开始", None)

                # 验证执行记录存在
                result = await db.execute(
                    select(PipelineExecution).where(PipelineExecution.id == execution_id)
                )
                execution = result.scalar_one_or_none()
                if not execution:
                    raise ValueError("Pipeline执行记录不存在")

                # 加载 Pipeline
                pipeline_result = await db.execute(
                    select(Pipeline).where(Pipeline.id == pipeline_id)
                )
                pipeline = pipeline_result.scalar_one_or_none()
                if not pipeline:
                    raise ValueError("Pipeline不存在")

                # 解析阶段名称（优先 stages_config）
                stage_names = []
                stages_config = pipeline.stages_config or []
                if stages_config:
                    stage_names = [s.get("name") for s in stages_config if s.get("name")]
                else:
                    stages_result = await db.execute(
                        select(PipelineStage).where(PipelineStage.pipeline_id == pipeline_id).order_by(PipelineStage.order)
                    )
                    stages = stages_result.scalars().all()
                    stage_names = [s.name for s in stages]

                stage_names = [name for name in stage_names if name]

                # 检查并预占积分（按阶段数计）
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError("用户不存在")

                # 计算所需积分
                from app.core.quota import CREDITS_PRICING
                breakdown_count = sum(1 for name in stage_names if name == "breakdown")
                script_count = sum(1 for name in stage_names if name == "script")
                required_credits = (
                    breakdown_count * CREDITS_PRICING.get("breakdown", 100) +
                    script_count * CREDITS_PRICING.get("script", 50)
                )

                if required_credits > 0:
                    quota_service = QuotaService(db)
                    # 先尝试发放月度积分
                    await quota_service.check_and_grant_monthly_credits(user)

                    if user.credits < required_credits:
                        raise ValueError(f"积分不足，需要 {required_credits}，余额 {user.credits}")

                    # 预扣积分
                    user.credits -= required_credits
                    await db.commit()
                reserved_credits = required_credits if required_credits > 0 else 0

                # 创建模型适配器（从数据库读取配置）
                model_adapter = await get_adapter(
                    user_id=user_id,
                    db=db
                )

                async def progress_callback(step: str, progress: int):
                    await update_pipeline_execution(
                        db,
                        execution_id,
                        progress=progress,
                        current_step=step
                    )

                async def stage_completed_callback(stage_name: str):
                    completed_stages.append(stage_name)
                    await _add_execution_log(
                        db,
                        execution_id,
                        stage_name,
                        "stage_completed",
                        f"阶段完成: {stage_name}",
                        {"completed_stages": completed_stages}
                    )

                async def log_callback(stage: str, event: str, message: str = None, detail: dict = None):
                    await _add_execution_log(db, execution_id, stage, event, message, detail)

                executor = PipelineExecutor(
                    db=db,
                    model_adapter=model_adapter,
                    user_id=user_id
                )

                results = await executor.run_pipeline(
                    pipeline_id=pipeline_id,
                    project_id=project_id,
                    batch_id=batch_id,
                    breakdown_id=breakdown_id,
                    progress_callback=progress_callback,
                    stage_completed_callback=stage_completed_callback,
                    log_callback=log_callback
                )
                # 确保结果包含已完成阶段
                results["completed_stages"] = completed_stages

                # 成功后扣费（按完成阶段计）
                await _consume_stage_credits(
                    db=db,
                    user_id=user_id,
                    execution_id=execution_id,
                    completed_stages=completed_stages
                )

                # 回滚未完成阶段的积分预扣
                await _refund_unused_credits(
                    db=db,
                    user_id=user_id,
                    reserved_credits=reserved_credits,
                    completed_stages=completed_stages
                )

                await update_pipeline_execution(
                    db,
                    execution_id,
                    status="completed",
                    progress=100,
                    current_step="任务完成",
                    result=results
                )
                await _add_execution_log(db, execution_id, None, "execution_completed", "Pipeline执行完成", results)

                return results

            except Exception as e:
                await _add_execution_log(
                    db,
                    execution_id,
                    None,
                    "execution_failed",
                    "Pipeline执行失败",
                    {"error": str(e), "completed_stages": completed_stages}
                )
                # 失败也按已完成阶段结算
                await _consume_stage_credits(
                    db=db,
                    user_id=user_id,
                    execution_id=execution_id,
                    completed_stages=completed_stages
                )

                # 回滚未完成阶段的积分预扣
                await _refund_unused_credits(
                    db=db,
                    user_id=user_id,
                    reserved_credits=reserved_credits,
                    completed_stages=completed_stages
                )

                await update_pipeline_execution(
                    db,
                    execution_id,
                    status="failed",
                    error_message=str(e),
                    result={"completed_stages": completed_stages}
                )
                raise

    return asyncio.run(_run())


async def _consume_stage_credits(
    db: AsyncSession,
    user_id: str,
    execution_id: str,
    completed_stages: list
):
    """按已完成阶段扣除积分（失败也结算）"""
    if not completed_stages:
        return

    breakdown_count = sum(1 for name in completed_stages if name == "breakdown")
    script_count = sum(1 for name in completed_stages if name == "script")

    credits_service = CreditsService(db)
    if breakdown_count:
        await credits_service.consume_credits(
            user_id=user_id,
            amount=BREAKDOWN_BASE_CREDITS * breakdown_count,
            description=f"Pipeline剧情拆解 - 执行 {execution_id}",
            reference_id=execution_id
        )
    if script_count:
        await credits_service.consume_credits(
            user_id=user_id,
            amount=SCRIPT_BASE_CREDITS * script_count,
            description=f"Pipeline剧本生成 - 执行 {execution_id}",
            reference_id=execution_id
        )

    await db.commit()


async def _refund_unused_credits(
    db: AsyncSession,
    user_id: str,
    reserved_credits: int,
    completed_stages: list
):
    """回滚未完成阶段的积分预扣"""
    if reserved_credits <= 0:
        return

    from app.core.quota import CREDITS_PRICING

    # 计算已完成阶段消耗的积分
    breakdown_count = sum(1 for name in completed_stages if name == "breakdown")
    script_count = sum(1 for name in completed_stages if name == "script")
    used_credits = (
        breakdown_count * CREDITS_PRICING.get("breakdown", 100) +
        script_count * CREDITS_PRICING.get("script", 50)
    )

    unused_credits = reserved_credits - used_credits
    if unused_credits <= 0:
        return

    # 回滚未完成部分
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return

    user.credits += unused_credits
    await db.commit()


async def _add_execution_log(
    db: AsyncSession,
    execution_id: str,
    stage: str,
    event: str,
    message: str,
    detail: dict
):
    log = PipelineExecutionLog(
        execution_id=execution_id,
        stage=stage,
        event=event,
        message=message,
        detail=detail
    )
    db.add(log)
    await db.commit()
