#!/usr/bin/env python3
"""修复批次状态不一致问题"""
from sqlalchemy import select, update
from app.core.database import SyncSessionLocal
from app.models.ai_task import AITask
from app.models.batch import Batch

def fix_batch_status():
    """修复批次状态与任务状态不一致的问题"""
    db = SyncSessionLocal()

    try:
        print("=" * 60)
        print("🔧 开始修复批次状态不一致问题")
        print("=" * 60)

        # 查找所有状态不一致的批次
        inconsistent_result = db.execute(
            select(Batch, AITask).join(
                AITask, Batch.id == AITask.batch_id
            ).where(
                AITask.status.in_(['queued', 'running']),
                Batch.breakdown_status == 'pending'
            )
        )

        inconsistent = inconsistent_result.all()

        if not inconsistent:
            print("\n✅ 未发现状态不一致的批次")
            return

        print(f"\n发现 {len(inconsistent)} 个状态不一致的批次")
        print("\n开始修复...")

        # 按批次ID分组
        batch_ids = set()
        for batch, task in inconsistent:
            batch_ids.add(batch.id)

        # 更新批次状态
        for batch_id in batch_ids:
            batch = db.query(Batch).filter(Batch.id == batch_id).first()
            if batch:
                old_status = batch.breakdown_status
                batch.breakdown_status = 'queued'
                print(f"  批次 {batch.batch_number}: {old_status} → queued")

        # 提交更改
        db.commit()

        print(f"\n✅ 成功修复 {len(batch_ids)} 个批次的状态")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_batch_status()
