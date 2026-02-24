#!/usr/bin/env python3
"""
手动创建 api_logs 表
用于修复表缺失的问题
"""

import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def create_api_logs_table():
    """创建 api_logs 表"""
    async with AsyncSessionLocal() as db:
        try:
            # 检查表是否存在
            check_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'api_logs'
                );
            """)
            result = await db.execute(check_query)
            exists = result.scalar()

            if exists:
                print("✅ api_logs 表已存在")
                return

            print("📝 创建 api_logs 表...")

            # 创建表
            create_table_query = text("""
                CREATE TABLE api_logs (
                    id UUID PRIMARY KEY,
                    method VARCHAR(10) NOT NULL,
                    path VARCHAR(500) NOT NULL,
                    query_params TEXT,
                    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                    user_ip VARCHAR(50),
                    user_agent VARCHAR(500),
                    status_code INTEGER NOT NULL,
                    response_time INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            await db.execute(create_table_query)

            # 创建索引
            print("📝 创建索引...")
            indexes = [
                "CREATE INDEX ix_api_logs_created_at ON api_logs(created_at);",
                "CREATE INDEX ix_api_logs_path ON api_logs(path);",
                "CREATE INDEX ix_api_logs_user_id ON api_logs(user_id);",
                "CREATE INDEX ix_api_logs_status_code ON api_logs(status_code);"
            ]

            for idx_sql in indexes:
                await db.execute(text(idx_sql))

            await db.commit()
            print("✅ api_logs 表创建成功!")

        except Exception as e:
            await db.rollback()
            print(f"❌ 创建失败: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_api_logs_table())
