#!/usr/bin/env python3
"""修复批次 42b45748 的状态不一致问题

问题：
- 批次有已完成的任务和拆解结果
- 但 breakdown_status 仍是 pending
- 最新任务处于 cancelling 状态（僵尸任务）

修复：
1. 清理僵尸 cancelling 任务 -> cancelled
2. 将批次状态更新为 completed
"""
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.core.database import SyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from app.core.status import TaskStatus, BatchStatus
from datetime import datetime, timezone

def fix_batch_status():
    db = SyncSessionLocal()

    try:
        batch_id = "42b45748-ccca-44b9-976c-c45b3b92fe12"

        # 1. 查询批次
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            print(f"❌ 未找到批次: {batch_id}")
            return

        print(f"📦 批次信息:")
        print(f"   批次号: {batch.batch_number}")
        print(f"   当前状态: {batch.breakdown_status}")
        print(f"   ai_processed: {batch.ai_processed}")
        print()

        # 2. 查询所有任务
        tasks = db.query(AITask).filter(
            AITask.batch_id == batch_id,
            AITask.task_type == "breakdown"
        ).order_by(AITask.created_at).all()

        print(f"📋 任务列表 (共{len(tasks)}个):")
        completed_tasks = []
        cancelling_tasks = []

        for i, task in enumerate(tasks, 1):
            print(f"   任务{i}: {task.status} (进度: {task.progress}%)")
            if task.status == TaskStatus.COMPLETED:
                completed_tasks.append(task)
            elif task.status == TaskStatus.CANCELLING:
                cancelling_tasks.append(task)
        print()

        # 3. 检查拆解结果
        from app.models.plot_breakdown import PlotBreakdown
        breakdowns = db.query(PlotBreakdown).filter(
            PlotBreakdown.batch_id == batch_id
        ).order_by(PlotBreakdown.created_at.desc()).all()

        print(f"📊 拆解结果 (共{len(breakdowns)}个):")
        for i, bd in enumerate(breakdowns, 1):
            plot_points_count = len(bd.plot_points) if bd.plot_points else 0
            print(f"   记录{i}: {plot_points_count}个剧情点, QA: {bd.qa_status}")
        print()

        # 4. 判断是否需要修复
        has_completed_task = len(completed_tasks) > 0
        has_breakdown_result = len(breakdowns) > 0
        has_cancelling_task = len(cancelling_tasks) > 0

        if not has_completed_task or not has_breakdown_result:
            print("⚠️  批次确实未完成，状态正确，无需修复")
            return

        if batch.breakdown_status == BatchStatus.COMPLETED:
            print("✅ 批次状态已经是 completed，无需修复")
            return

        # 5. 开始修复
        print("🔧 开始修复...")
        print()

        # 5.1 清理僵尸 cancelling 任务
        if has_cancelling_task:
            print(f"   清理 {len(cancelling_tasks)} 个僵尸 cancelling 任务...")
            for task in cancelling_tasks:
                task.status = TaskStatus.CANCELED  # 注意：是 CANCELED 不是 CANCELLED
                task.error_message = "任务已取消（系统自动清理）"
                task.completed_at = datetime.now(timezone.utc)
                print(f"   ✓ 任务 {task.id} -> canceled")

        # 5.2 更新批次状态
        old_status = batch.breakdown_status
        batch.breakdown_status = BatchStatus.COMPLETED
        print(f"   ✓ 批次状态: {old_status} -> {BatchStatus.COMPLETED}")

        # 5.3 提交更改
        db.commit()
        print()
        print("✅ 修复完成！")
        print()

        # 6. 验证修复结果
        db.refresh(batch)
        print("📋 修复后状态:")
        print(f"   breakdown_status: {batch.breakdown_status}")
        print(f"   ai_processed: {batch.ai_processed}")

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_batch_status()
