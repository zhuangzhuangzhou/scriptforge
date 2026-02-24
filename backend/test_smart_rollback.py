"""测试智能回滚机制

场景：
1. 批次第一次拆解成功
2. 批次第二次拆解失败
3. 验证批次状态是否回滚到 completed
"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown


async def test_smart_rollback():
    async with AsyncSessionLocal() as db:
        # 测试批次 ID
        batch_id = "48a28941-bb13-423f-b02a-51ca8f04e1e7"

        print("=" * 60)
        print("智能回滚机制测试")
        print("=" * 60)
        print()

        # 1. 查询批次信息
        batch_result = await db.execute(
            select(Batch).where(Batch.id == batch_id)
        )
        batch = batch_result.scalar_one_or_none()

        if not batch:
            print(f"❌ 批次不存在: {batch_id}")
            return

        print(f"📦 批次信息:")
        print(f"  批次号: {batch.batch_number}")
        print(f"  当前状态: {batch.breakdown_status}")
        print()

        # 2. 查询所有任务
        tasks_result = await db.execute(
            select(AITask)
            .where(AITask.batch_id == batch_id)
            .order_by(AITask.created_at)
        )
        tasks = tasks_result.scalars().all()

        print(f"📋 任务历史 ({len(tasks)} 个):")
        for i, task in enumerate(tasks, 1):
            print(f"  {i}. 任务 {str(task.id)[:8]}...")
            print(f"     状态: {task.status}")
            print(f"     创建时间: {task.created_at}")
            print()

        # 3. 查询拆解结果
        breakdown_result = await db.execute(
            select(PlotBreakdown)
            .where(PlotBreakdown.batch_id == batch_id)
            .order_by(PlotBreakdown.created_at)
        )
        breakdowns = breakdown_result.scalars().all()

        print(f"📊 拆解结果 ({len(breakdowns)} 条):")
        for i, bd in enumerate(breakdowns, 1):
            print(f"  {i}. 结果 {str(bd.id)[:8]}...")
            print(f"     任务ID: {str(bd.task_id)[:8] if bd.task_id else 'None'}...")
            print(f"     剧情点数量: {len(bd.plot_points) if bd.plot_points else 0}")
            print(f"     QA状态: {bd.qa_status}")
            print(f"     QA分数: {bd.qa_score}")
            print(f"     创建时间: {bd.created_at}")
            print()

        # 4. 验证智能回滚逻辑
        print("=" * 60)
        print("智能回滚逻辑验证")
        print("=" * 60)
        print()

        # 统计成功和失败的任务
        completed_tasks = [t for t in tasks if t.status == "completed"]
        failed_tasks = [t for t in tasks if t.status == "failed"]

        print(f"✅ 成功任务: {len(completed_tasks)} 个")
        print(f"❌ 失败任务: {len(failed_tasks)} 个")
        print()

        # 检查是否有有效的拆解结果
        valid_breakdowns = [
            bd for bd in breakdowns
            if bd.plot_points and isinstance(bd.plot_points, list) and len(bd.plot_points) > 0
        ]

        print(f"📊 有效拆解结果: {len(valid_breakdowns)} 条")
        print()

        # 预期行为
        if len(completed_tasks) > 0 and len(valid_breakdowns) > 0:
            expected_status = "completed"
            print(f"✅ 预期批次状态: {expected_status}")
            print(f"   原因: 有 {len(completed_tasks)} 个成功任务和 {len(valid_breakdowns)} 个有效结果")
        else:
            expected_status = "failed"
            print(f"❌ 预期批次状态: {expected_status}")
            print(f"   原因: 没有成功任务或有效结果")

        print()
        print(f"📦 实际批次状态: {batch.breakdown_status}")
        print()

        # 判断是否符合预期
        if batch.breakdown_status == expected_status:
            print("✅ 智能回滚机制工作正常！")
        else:
            print(f"⚠️  状态不符合预期")
            print(f"   预期: {expected_status}")
            print(f"   实际: {batch.breakdown_status}")


if __name__ == "__main__":
    asyncio.run(test_smart_rollback())
