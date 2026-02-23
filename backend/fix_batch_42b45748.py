"""修复批次 42b45748-ccca-44b9-976c-c45b3b92fe12 的状态

该批次的拆解任务已成功完成，但后续剧本任务被管理员手动停止，
导致整个批次的 breakdown_status 被错误地标记为 failed。

此脚本检查并修复该批次的状态。
"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown
from app.core.status import BatchStatus, TaskStatus


async def fix_batch_status():
    batch_id = "42b45748-ccca-44b9-976c-c45b3b92fe12"

    async with AsyncSessionLocal() as db:
        # 1. 获取批次
        result = await db.execute(select(Batch).where(Batch.id == batch_id))
        batch = result.scalar_one_or_none()

        if not batch:
            print(f"❌ 批次 {batch_id} 不存在")
            return

        print(f"批次 ID: {batch_id}")
        print(f"当前状态:")
        print(f"  breakdown_status: {batch.breakdown_status}")
        print(f"  script_status: {batch.script_status}")

        # 2. 检查拆解任务
        result = await db.execute(
            select(AITask)
            .where(AITask.batch_id == batch_id, AITask.task_type == "breakdown")
            .order_by(AITask.created_at.desc())
        )
        breakdown_tasks = result.scalars().all()

        completed_breakdown = any(t.status == TaskStatus.COMPLETED for t in breakdown_tasks)

        # 3. 检查拆解结果
        result = await db.execute(
            select(PlotBreakdown).where(PlotBreakdown.batch_id == batch_id)
        )
        breakdowns = result.scalars().all()

        print(f"\n拆解任务统计:")
        print(f"  总数: {len(breakdown_tasks)} 个")
        for t in breakdown_tasks:
            print(f"    - {t.id}: {t.status}")
        print(f"  已完成: {sum(1 for t in breakdown_tasks if t.status == TaskStatus.COMPLETED)}")

        print(f"\n拆解结果:")
        print(f"  章节数: {len(breakdowns)} 个")
        for b in breakdowns:
            plot_count = len(b.plot_points) if b.plot_points else 0
            print(f"    - 章节 {b.chapter_number}: {plot_count} 个剧情点")

        # 4. 检查剧本任务
        result = await db.execute(
            select(AITask)
            .where(
                AITask.batch_id == batch_id,
                AITask.task_type.in_(["script", "episode_script"])
            )
            .order_by(AITask.created_at.desc())
        )
        script_tasks = result.scalars().all()

        if script_tasks:
            print(f"\n剧本任务统计:")
            print(f"  总数: {len(script_tasks)} 个")
            for t in script_tasks:
                print(f"    - {t.id}: {t.status} ({t.error_message[:50] if t.error_message else 'N/A'}...)")

        # 5. 修复状态
        has_valid_breakdowns = any(
            b.plot_points and len(b.plot_points) > 0 for b in breakdowns
        )

        if completed_breakdown or has_valid_breakdowns:
            print(f"\n✅ 检测到成功的拆解结果，修复状态...")
            old_status = batch.breakdown_status
            batch.breakdown_status = BatchStatus.COMPLETED
            await db.commit()
            print(f"  breakdown_status: {old_status} → {BatchStatus.COMPLETED}")
            print(f"  script_status: {batch.script_status} (保持不变)")
            print(f"\n🎉 修复完成！用户现在可以继续使用拆解结果。")
        else:
            print(f"\n⚠️ 没有成功的拆解结果，保持 {batch.breakdown_status} 状态")


async def check_all_affected_batches():
    """检查所有可能受影响的批次"""
    print("\n" + "=" * 60)
    print("检查所有可能受影响的批次...")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 查找 breakdown_status=failed 但有成功拆解结果的批次
        result = await db.execute(
            select(Batch).where(Batch.breakdown_status == BatchStatus.FAILED)
        )
        failed_batches = result.scalars().all()

        affected = []
        for batch in failed_batches:
            # 检查是否有成功的拆解结果
            result = await db.execute(
                select(PlotBreakdown)
                .where(PlotBreakdown.batch_id == batch.id)
            )
            breakdowns = result.scalars().all()

            has_valid = any(
                b.plot_points and len(b.plot_points) > 0 for b in breakdowns
            )

            if has_valid:
                affected.append({
                    "batch_id": str(batch.id),
                    "project_id": str(batch.project_id),
                    "breakdown_count": len(breakdowns)
                })

        if affected:
            print(f"\n发现 {len(affected)} 个可能受影响的批次:")
            for b in affected:
                print(f"  - {b['batch_id']} (项目: {b['project_id']}, 章节: {b['breakdown_count']})")
        else:
            print("\n没有发现受影响的批次")


if __name__ == "__main__":
    print("=" * 60)
    print("批次状态修复脚本")
    print("=" * 60)

    asyncio.run(fix_batch_status())
    asyncio.run(check_all_affected_batches())
