import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, update

# 添加 backend 目录到 sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from app.core.database import AsyncSessionLocal
from app.models.ai_configuration import AIConfiguration

async def fix_data():
    print("正在检查并修复 is_active = NULL 的数据...")
    async with AsyncSessionLocal() as db:
        # 1. 检查
        stmt = select(AIConfiguration).where(AIConfiguration.is_active == None)
        result = await db.execute(stmt)
        configs = result.scalars().all()

        count = len(configs)
        print(f"发现 {count} 条记录的 is_active 为 NULL。")

        if count > 0:
            for c in configs:
                print(f"  - 修复: Key={c.key}, ID={c.id}")

            # 2. 批量更新
            update_stmt = (
                update(AIConfiguration)
                .where(AIConfiguration.is_active == None)
                .values(is_active=True)
            )
            await db.execute(update_stmt)
            await db.commit()
            print(f"✅ 成功修复 {count} 条记录。")
        else:
            print("✅ 数据完整，无需修复。")

if __name__ == "__main__":
    asyncio.run(fix_data())
