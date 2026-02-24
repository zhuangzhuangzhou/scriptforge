#!/usr/bin/env python3
"""
检查数据库表和迁移历史
"""

import asyncio
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check_tables_and_migrations():
    """检查表和迁移历史"""
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("数据库表检查")
        print("=" * 60)

        # 检查表是否存在
        tables = ['api_logs', 'llm_call_logs', 'ai_tasks', 'alembic_version']

        for table_name in tables:
            query = text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                );
            """)
            result = await db.execute(query)
            exists = result.scalar()

            status = "✅" if exists else "❌"
            print(f"{status} {table_name}: {'存在' if exists else '不存在'}")

            # 如果表存在,检查记录数
            if exists and table_name != 'alembic_version':
                count_query = text(f"SELECT COUNT(*) FROM {table_name};")
                count_result = await db.execute(count_query)
                count = count_result.scalar()
                print(f"   └─ 记录数: {count}")

        print("\n" + "=" * 60)
        print("Alembic 迁移历史")
        print("=" * 60)

        # 检查当前迁移版本
        version_query = text("SELECT version_num FROM alembic_version;")
        version_result = await db.execute(version_query)
        current_version = version_result.scalar()
        print(f"当前版本: {current_version}")

        print("\n" + "=" * 60)
        print("api_logs 表结构")
        print("=" * 60)

        # 检查 api_logs 表结构
        structure_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'api_logs'
            ORDER BY ordinal_position;
        """)
        structure_result = await db.execute(structure_query)
        columns = structure_result.all()

        if columns:
            print(f"{'字段名':<20} {'类型':<20} {'可空':<10}")
            print("-" * 50)
            for col in columns:
                print(f"{col[0]:<20} {col[1]:<20} {col[2]:<10}")
        else:
            print("表不存在或无字段")

if __name__ == "__main__":
    asyncio.run(check_tables_and_migrations())
