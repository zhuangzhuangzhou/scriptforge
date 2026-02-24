"""测试新批次的拆解"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.batch import Batch

async def find_next_batch():
    async with AsyncSessionLocal() as db:
        # 查找下一个 pending 批次
        result = await db.execute(
            select(Batch)
            .where(Batch.breakdown_status == "pending")
            .order_by(Batch.batch_number)
            .limit(1)
        )
        batch = result.scalar_one_or_none()
        
        if batch:
            print(f"✅ 找到下一个待测试批次:")
            print(f"   - 批次号: {batch.batch_number}")
            print(f"   - 批次ID: {batch.id}")
            print(f"   - 项目ID: {batch.project_id}")
            print(f"\n📝 请在前端触发此批次的拆解,然后我会监控状态更新")
        else:
            print("❌ 没有找到 pending 状态的批次")

if __name__ == "__main__":
    asyncio.run(find_next_batch())
