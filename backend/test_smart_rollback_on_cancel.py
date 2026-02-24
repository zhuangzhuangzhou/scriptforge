#!/usr/bin/env python3
"""测试停止任务时的智能回滚机制

场景：
1. 批次已有成功的拆解结果
2. 用户启动新的拆解任务
3. 用户停止任务
4. 验证批次状态是否智能回滚到 completed（而不是 pending）
"""
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.core.database import SyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.models.plot_breakdown import PlotBreakdown
from app.tasks.breakdown_tasks import _check_previous_breakdown_success
from app.core.status import TaskStatus, BatchStatus

def test_smart_rollback_on_cancel():
    """测试停止任务时的智能回滚"""
    db = SyncSessionLocal()

    try:
        # 使用你的实际批次 ID
        batch_id = "42b45748-ccca-44b9-976c-c45b3b92fe12"

        print("=" * 60)
        print("智能回滚机制测试 - 停止任务场景")
        print("=" * 60)
        print()

        # 1. 查询批次信息
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            print(f"❌ 未找到批次: {batch_id}")
            return

        print(f"📦 批次信息:")
        print(f"   ID: {batch.id}")
        print(f"   批次号: {batch.batch_number}")
        print(f"   当前状态: {batch.breakdown_status}")
        print()

        # 2. 查询所有任务
        tasks = db.query(AITask).filter(
            AITask.batch_id == batch_id,
            AITask.task_type == "breakdown"
        ).order_by(AITask.created_at).all()

        print(f"📋 任务列表 (共{len(tasks)}个):")
        completed_tasks = []
        for i, task in enumerate(tasks, 1):
            status_emoji = "✅" if task.status == TaskStatus.COMPLETED else "❌"
            print(f"   {status_emoji} 任务{i}: {task.status} (进度: {task.progress}%)")
            if task.status == TaskStatus.COMPLETED:
                completed_tasks.append(task)
        print()

        # 3. 查询拆解结果
        breakdowns = db.query(PlotBreakdown).filter(
            PlotBreakdown.batch_id == batch_id
        ).order_by(PlotBreakdown.created_at.desc()).all()

        print(f"📊 拆解结果 (共{len(breakdowns)}个):")
        for i, bd in enumerate(breakdowns, 1):
            plot_points_count = len(bd.plot_points) if bd.plot_points else 0
            qa_emoji = "✅" if bd.qa_status == "PASS" else "⚠️"
            print(f"   {qa_emoji} 记录{i}: {plot_points_count}个剧情点, QA: {bd.qa_status}")
        print()

        # 4. 测试智能回滚逻辑
        print("🔍 测试智能回滚逻辑:")
        print()

        # 模拟最新任务（假设是被取消的任务）
        latest_task = tasks[-1] if tasks else None
        if not latest_task:
            print("❌ 没有任务可测试")
            return

        # 检查是否有之前的成功结果
        has_previous_success = _check_previous_breakdown_success(
            db=db,
            batch_id=batch_id,
            current_task_id=str(latest_task.id)
        )

        print(f"   当前任务ID: {latest_task.id}")
        print(f"   当前任务状态: {latest_task.status}")
        print(f"   是否有之前的成功结果: {'✅ 是' if has_previous_success else '❌ 否'}")
        print()

        # 5. 判断应该回滚到什么状态
        if has_previous_success:
            expected_status = BatchStatus.COMPLETED
            print(f"✅ 智能回滚判断: 应该保持 {expected_status} 状态")
            print(f"   原因: 批次有 {len(completed_tasks)} 个已完成的任务和 {len(breakdowns)} 个拆解结果")
        else:
            expected_status = BatchStatus.PENDING
            print(f"⚠️  智能回滚判断: 应该回滚到 {expected_status} 状态")
            print(f"   原因: 批次没有之前的成功拆解结果")
        print()

        # 6. 验证当前状态
        print("📋 状态验证:")
        if batch.breakdown_status == expected_status:
            print(f"   ✅ 批次状态正确: {batch.breakdown_status}")
        else:
            print(f"   ❌ 批次状态不正确:")
            print(f"      当前: {batch.breakdown_status}")
            print(f"      期望: {expected_status}")
        print()

        # 7. 显示详细的拆解结果信息
        if has_previous_success and breakdowns:
            latest_breakdown = breakdowns[0]
            print("📄 最新拆解结果详情:")
            print(f"   ID: {latest_breakdown.id}")
            print(f"   剧情点数量: {len(latest_breakdown.plot_points) if latest_breakdown.plot_points else 0}")
            print(f"   QA状态: {latest_breakdown.qa_status}")
            print(f"   QA分数: {latest_breakdown.qa_score}")
            print(f"   创建时间: {latest_breakdown.created_at}")
            print()

        print("=" * 60)
        print("测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_smart_rollback_on_cancel()
