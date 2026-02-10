#!/usr/bin/env python3
"""修复失败批次状态的脚本

问题：
- 批次状态为 failed，但前端仍提示"已有任务在执行中"
- 可能存在状态不一致的情况

解决方案：
- 检查所有 failed 状态的批次
- 确保对应的任务状态也是 failed
- 清理状态不一致的数据
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask
from sqlalchemy import select


def fix_failed_batch_status():
    """修复失败批次的状态"""
    db = SyncSessionLocal()
    
    try:
        print("🔍 开始检查失败批次状态...")
        
        # 查找所有 failed 状态的批次
        failed_batches = db.query(Batch).filter(
            Batch.breakdown_status == "failed"
        ).all()
        
        print(f"📊 找到 {len(failed_batches)} 个失败状态的批次")
        
        fixed_count = 0
        inconsistent_count = 0
        
        for batch in failed_batches:
            print(f"\n检查批次 {batch.id} (batch_number: {batch.batch_number})...")
            
            # 查找该批次的所有任务
            tasks = db.query(AITask).filter(
                AITask.batch_id == batch.id,
                AITask.task_type == "breakdown"
            ).all()
            
            if not tasks:
                print(f"  ⚠️  批次 {batch.id} 没有关联的任务记录")
                continue
            
            # 检查是否有非 failed 状态的任务
            non_failed_tasks = [t for t in tasks if t.status not in ["failed", "canceled"]]
            
            if non_failed_tasks:
                print(f"  ⚠️  发现 {len(non_failed_tasks)} 个状态不一致的任务:")
                for task in non_failed_tasks:
                    print(f"     - 任务 {task.id}: 状态 = {task.status}")
                    
                    # 如果任务状态是 queued 或 running，但批次是 failed
                    # 这是不一致的状态，需要修复
                    if task.status in ["queued", "running"]:
                        print(f"     ❌ 将任务 {task.id} 状态从 {task.status} 改为 failed")
                        task.status = "failed"
                        if not task.error_message:
                            import json
                            from datetime import datetime
                            task.error_message = json.dumps({
                                "code": "INCONSISTENT_STATE",
                                "message": "任务状态与批次状态不一致，已自动修复",
                                "failed_at": datetime.utcnow().isoformat(),
                                "fixed_by": "fix_failed_batch_status.py"
                            })
                        inconsistent_count += 1
                        fixed_count += 1
            else:
                print(f"  ✅ 批次 {batch.id} 状态一致")
        
        # 提交更改
        if fixed_count > 0:
            db.commit()
            print(f"\n✅ 已修复 {fixed_count} 个状态不一致的任务")
        else:
            print(f"\n✅ 所有批次状态一致，无需修复")
        
        # 额外检查：查找状态为 queued/running 但批次为 failed 的任务
        print("\n🔍 检查孤立的运行中任务...")
        orphan_tasks = db.query(AITask).join(Batch).filter(
            AITask.task_type == "breakdown",
            AITask.status.in_(["queued", "running"]),
            Batch.breakdown_status == "failed"
        ).all()
        
        if orphan_tasks:
            print(f"⚠️  发现 {len(orphan_tasks)} 个孤立的运行中任务:")
            for task in orphan_tasks:
                print(f"   - 任务 {task.id} (批次 {task.batch_id}): {task.status}")
                task.status = "failed"
                if not task.error_message:
                    import json
                    from datetime import datetime
                    task.error_message = json.dumps({
                        "code": "ORPHANED_TASK",
                        "message": "任务状态与批次状态不一致（孤立任务），已自动修复",
                        "failed_at": datetime.utcnow().isoformat(),
                        "fixed_by": "fix_failed_batch_status.py"
                    })
            db.commit()
            print(f"✅ 已修复 {len(orphan_tasks)} 个孤立任务")
        else:
            print("✅ 没有发现孤立的运行中任务")
        
        print("\n" + "="*60)
        print(f"修复完成！")
        print(f"  - 检查的批次数: {len(failed_batches)}")
        print(f"  - 修复的任务数: {fixed_count}")
        print(f"  - 状态不一致数: {inconsistent_count}")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_failed_batch_status()
