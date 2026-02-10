#!/usr/bin/env python3
"""修复 ai_processed 字段"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SyncSessionLocal
from app.models.batch import Batch
from app.models.plot_breakdown import PlotBreakdown


def fix_ai_processed():
    """修复 ai_processed 字段"""
    db = SyncSessionLocal()
    
    try:
        # 查找所有 breakdown_status 为 completed 但 ai_processed 为 False 的批次
        batches = db.query(Batch).filter(
            Batch.breakdown_status == "completed",
            Batch.ai_processed == False
        ).all()
        
        print(f"找到 {len(batches)} 个需要修复的批次\n")
        
        fixed_count = 0
        for batch in batches:
            # 检查是否有对应的拆解结果
            breakdown = db.query(PlotBreakdown).filter(
                PlotBreakdown.batch_id == batch.id
            ).first()
            
            if breakdown:
                print(f"修复批次 {batch.batch_number}:")
                print(f"  Batch ID: {batch.id}")
                print(f"  拆解结果 ID: {breakdown.id}")
                
                # 更新 ai_processed 为 True
                batch.ai_processed = True
                db.commit()
                
                print(f"  ✅ 已更新 ai_processed = True\n")
                fixed_count += 1
            else:
                print(f"⚠️  批次 {batch.batch_number} 没有拆解结果，跳过\n")
        
        print(f"✅ 修复完成，共修复 {fixed_count} 个批次")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_ai_processed()
