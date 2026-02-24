"""
调查批次 42b45748-ccca-44b9-976c-c45b3b92fe12 失败原因
"""
import asyncio
from sqlalchemy import select, desc
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown

async def investigate_batch_failure():
    batch_id = "42b45748-ccca-44b9-976c-c45b3b92fe12"

    async with AsyncSessionLocal() as session:
        # 1. 获取批次详细信息
        print("=" * 80)
        print("1. 批次详细信息")
        print("=" * 80)
        result = await session.execute(
            select(Batch).where(Batch.id == batch_id)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            print(f"❌ 批次 {batch_id} 不存在")
            return

        print(f"批次ID: {batch.id}")
        print(f"项目ID: {batch.project_id}")
        print(f"拆解状态: {batch.breakdown_status}")
        print(f"脚本状态: {batch.script_status}")
        print(f"章节范围: {batch.start_chapter} - {batch.end_chapter}")
        print(f"总章节数: {batch.total_chapters}")
        print(f"总字数: {batch.total_words}")
        print(f"创建时间: {batch.created_at}")
        print(f"更新时间: {batch.updated_at}")

        # 2. 查找关联的 AI 任务
        print("\n" + "=" * 80)
        print("2. 关联的 AI 任务")
        print("=" * 80)
        result = await session.execute(
            select(AITask)
            .where(AITask.batch_id == batch_id)
            .order_by(desc(AITask.created_at))
        )
        tasks = result.scalars().all()

        if not tasks:
            print("❌ 没有找到关联的 AI 任务")
        else:
            print(f"找到 {len(tasks)} 个关联任务:\n")
            for i, task in enumerate(tasks, 1):
                print(f"任务 #{i}:")
                print(f"  任务ID: {task.id}")
                print(f"  任务类型: {task.task_type}")
                print(f"  状态: {task.status}")
                print(f"  Celery任务ID: {task.celery_task_id}")
                print(f"  创建时间: {task.created_at}")
                print(f"  开始时间: {task.started_at}")
                print(f"  完成时间: {task.completed_at}")
                print(f"  错误信息: {task.error_message or '无'}")
                print(f"  重试次数: {task.retry_count}")
                print()

        # 3. 检查是否有成功的拆解结果
        print("=" * 80)
        print("3. 拆解结果检查")
        print("=" * 80)
        result = await session.execute(
            select(PlotBreakdown)
            .where(PlotBreakdown.batch_id == batch_id)
            .order_by(PlotBreakdown.chapter_number)
        )
        breakdowns = result.scalars().all()

        if not breakdowns:
            print("❌ 没有找到任何拆解结果")
            print("   → 这意味着任务在生成任何结果之前就失败了")
        else:
            print(f"✅ 找到 {len(breakdowns)} 个章节的拆解结果:\n")
            for bd in breakdowns:
                print(f"  章节 {bd.chapter_number}:")
                print(f"    剧情点数量: {bd.plot_point_count}")
                print(f"    创建时间: {bd.created_at}")

        # 4. 分析失败原因
        print("\n" + "=" * 80)
        print("4. 失败原因分析")
        print("=" * 80)

        if tasks:
            latest_task = tasks[0]

            if latest_task.error_message:
                print(f"🔍 最新任务的错误信息:")
                print(f"   {latest_task.error_message}")

                # 分析错误类型
                error_msg = latest_task.error_message.lower()
                if "quota" in error_msg or "配额" in error_msg:
                    print("\n💡 失败原因: API 配额不足")
                elif "timeout" in error_msg or "超时" in error_msg:
                    print("\n💡 失败原因: 任务执行超时")
                elif "model" in error_msg or "模型" in error_msg:
                    print("\n💡 失败原因: 模型调用错误")
                elif "terminated" in error_msg or "终止" in error_msg:
                    print("\n💡 失败原因: 任务被系统自动终止")
                else:
                    print("\n💡 失败原因: 其他错误（见上方错误信息）")
            else:
                print("⚠️  任务没有记录错误信息")

                # 检查任务状态
                if latest_task.status == "failed":
                    print("   任务状态为 failed，但没有错误信息")
                    print("   可能原因:")
                    print("   - 系统自动终止（task_monitor.py）")
                    print("   - 管理员手动停止")
                    print("   - Celery worker 崩溃")

                # 检查时间
                if latest_task.started_at:
                    if latest_task.completed_at:
                        duration = (latest_task.completed_at - latest_task.started_at).total_seconds()
                        print(f"   任务执行时长: {duration:.1f} 秒")
                        if duration > 3600:
                            print("   → 任务执行超过1小时，可能被系统自动终止")
                    else:
                        print("   任务已开始但未完成，可能被中断")

        # 5. 给出建议
        print("\n" + "=" * 80)
        print("5. 处理建议")
        print("=" * 80)

        if breakdowns:
            print("✅ 该批次有之前的成功拆解结果")
            print("   建议: 可以尝试重新提交任务，系统会保护已有的结果")
        else:
            print("❌ 该批次没有任何成功的拆解结果")
            print("   建议: 检查错误原因后重新提交任务")

        if tasks and tasks[0].error_message:
            error_msg = tasks[0].error_message.lower()
            if "quota" in error_msg or "配额" in error_msg:
                print("   → 需要充值 API 配额后重试")
            elif "timeout" in error_msg or "超时" in error_msg:
                print("   → 可以尝试减少章节范围或优化提示词")

if __name__ == "__main__":
    asyncio.run(investigate_batch_failure())
