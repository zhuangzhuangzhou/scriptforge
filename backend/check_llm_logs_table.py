"""检查 llm_call_logs 表是否存在"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check_table():
    async with AsyncSessionLocal() as db:
        # 查询所有表
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%llm%'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        
        print("📋 数据库中与 LLM 相关的表:")
        if tables:
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("   ❌ 没有找到任何与 LLM 相关的表")
        
        # 检查是否有 llm_call_logs 表
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'llm_call_logs'
            )
        """))
        exists = result.scalar()
        
        print(f"\n🔍 llm_call_logs 表是否存在: {'✅ 是' if exists else '❌ 否'}")

if __name__ == "__main__":
    asyncio.run(check_table())
