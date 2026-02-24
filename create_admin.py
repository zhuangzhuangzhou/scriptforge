#!/usr/bin/env python3
"""创建管理员账号"""
import asyncio
import sys
import os
from pathlib import Path

# 设置工作目录和环境变量
backend_dir = Path(__file__).parent / 'backend'
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(backend_dir / '.env')

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    async with AsyncSessionLocal() as db:
        # 检查是否已存在
        result = await db.execute(select(User).where(User.username == 'admin'))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"管理员账号已存在: {existing.username} ({existing.email})")
            # 更新密码和角色
            existing.hashed_password = get_password_hash('admin')
            existing.role = 'admin'
            existing.is_active = True
            await db.commit()
            print("✅ 已更新管理员密码为 admin")
        else:
            # 创建新管理员
            admin = User(
                username='admin',
                email='admin@example.com',
                hashed_password=get_password_hash('admin'),
                role='admin',
                is_active=True,
                tier='enterprise',
                credits=999999
            )
            db.add(admin)
            await db.commit()
            print("✅ 创建管理员账号成功")
            print(f"   用户名: admin")
            print(f"   密码: admin")

if __name__ == "__main__":
    asyncio.run(create_admin())
