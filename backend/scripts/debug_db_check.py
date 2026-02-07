import asyncio
import sys
from pathlib import Path
from sqlalchemy import select

# 添加 backend 目录到 sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from app.core.database import AsyncSessionLocal
from app.models.ai_configuration import AIConfiguration

async def check_data():
    print("正在检查数据库中的系统配置...")
    async with AsyncSessionLocal() as db:
        # 查询系统配置 (user_id IS NULL)
        stmt = select(AIConfiguration).where(AIConfiguration.user_id == None)
        result = await db.execute(stmt)
        configs = result.scalars().all()

        print(f"找到 {len(configs)} 条系统默认配置:")
        for c in configs:
            print(f"  - Key: {c.key}, ID: {c.id}, UserID: {c.user_id}, IsActive: {c.is_active}")

        if len(configs) == 0:
            print("❌ 警告：没有找到系统默认配置！")
        else:
            print("✅ 数据库数据正常。")

if __name__ == "__main__":
    asyncio.run(check_data())
