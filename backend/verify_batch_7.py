"""监控批次 7 的状态更新"""
import asyncio
import time
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch
from app.models.ai_task import AITask

async def monitor_batch_status(batch_id: str, timeout: int = 300):
    """监控批次状态变化
    
    Args:
        batch_id: 批次ID
        timeout: 超时时间(秒)
    """
    start_time = time.time()
    last_status = None
    last_task_status = None
    
    print(f"🔍 开始监控批次 7 ({batch_id})")
    print(f"⏱️  超时时间: {timeout} 秒")
    print("-" * 60)
    
    while time.time() - start_time < timeout:
        async with AsyncSessionLocal() as db:
            # 查询批次状态
            batch_result = await db.execute(
                select(Batch).where(Batch.id == batch_id)
            )
            batch = batch_result.scalar_one_or_none()
            
            if not batch:
                print("❌ 批次不存在")
                return False
            
            # 查询最新任务状态
            task_result = await db.execute(
                select(AITask)
                .where(AITask.batch_id == batch_id)
                .order_by(AITask.created_at.desc())
                .limit(1)
            )
            task = task_result.scalar_one_or_none()
            
            # 检测状态变化
            current_batch_status = batch.breakdown_status
            current_task_status = task.status if task else None
            
            if current_batch_status != last_status or current_task_status != last_task_status:
                elapsed = int(time.time() - start_time)
                print(f"[{elapsed}s] 批次状态: {current_batch_status} | 任务状态: {current_task_status or 'N/A'}")
                
                last_status = current_batch_status
                last_task_status = current_task_status
            
            # 检查是否完成
            if task and task.status == "completed":
                await asyncio.sleep(2)  # 等待2秒,确保批次状态有时间更新
                
                # 重新查询批次状态
                batch_result = await db.execute(
                    select(Batch).where(Batch.id == batch_id)
                )
                batch = batch_result.scalar_one()
                
                if batch.breakdown_status == "completed":
                    print("\n✅ 验证成功!")
                    print(f"   - 任务状态: {task.status}")
                    print(f"   - 批次状态: {batch.breakdown_status}")
                    print(f"   - 状态更新正常 ✓")
                    print(f"\n🎉 修复生效! llm_call_logs 表创建后,批次状态能正确更新了")
                    return True
                elif batch.breakdown_status in ["in_progress", "processing"]:
                    print("\n⚠️  检测到问题!")
                    print(f"   - 任务状态: {task.status} (已完成)")
                    print(f"   - 批次状态: {batch.breakdown_status} (未更新)")
                    print(f"   - 这说明问题仍然存在!")
                    return False
            
            # 检查是否失败
            if task and task.status == "failed":
                print(f"\n⚠️  任务失败")
                print(f"   - 任务状态: {task.status}")
                print(f"   - 批次状态: {current_batch_status}")
                if task.error_message:
                    print(f"   - 错误信息: {task.error_message[:200]}")
                return False
        
        await asyncio.sleep(5)  # 每5秒检查一次
    
    print(f"\n⏱️  超时 ({timeout}秒)")
    return False

if __name__ == "__main__":
    batch_id = "9e6c9f12-e7c8-473e-ae2d-0efe68aa2baa"
    result = asyncio.run(monitor_batch_status(batch_id))
    exit(0 if result else 1)
