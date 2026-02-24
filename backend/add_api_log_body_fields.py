#!/usr/bin/env python3
"""
添加 request_body 和 response_body 字段到 api_logs 表
"""

import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def add_body_fields():
    """添加请求体和响应体字段"""
    async with AsyncSessionLocal() as db:
        try:
            print("📝 添加 request_body 字段...")
            await db.execute(text("""
                ALTER TABLE api_logs
                ADD COLUMN IF NOT EXISTS request_body TEXT;
            """))

            print("📝 添加 response_body 字段...")
            await db.execute(text("""
                ALTER TABLE api_logs
                ADD COLUMN IF NOT EXISTS response_body TEXT;
            """))

            await db.commit()
            print("✅ 字段添加成功!")

        except Exception as e:
            await db.rollback()
            print(f"❌ 添加失败: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_body_fields())
