"""手动创建 llm_call_logs 表"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def create_table():
    async with AsyncSessionLocal() as db:
        # 创建表
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS llm_call_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES ai_tasks(id) ON DELETE SET NULL,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                provider VARCHAR(50) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                skill_name VARCHAR(100),
                stage VARCHAR(100),
                prompt_tokens INTEGER,
                temperature FLOAT,
                max_tokens INTEGER,
                response TEXT,
                response_tokens INTEGER,
                total_tokens INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'success',
                error_message TEXT,
                latency_ms INTEGER,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        # 创建索引
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_created_at ON llm_call_logs(created_at)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_task_id ON llm_call_logs(task_id)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_user_id ON llm_call_logs(user_id)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_provider ON llm_call_logs(provider)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_model_name ON llm_call_logs(model_name)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_skill_name ON llm_call_logs(skill_name)
        """))
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_llm_call_logs_status ON llm_call_logs(status)
        """))
        
        await db.commit()
        print("✅ llm_call_logs 表创建成功")
        
        # 验证表是否存在
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'llm_call_logs'
            )
        """))
        exists = result.scalar()
        print(f"🔍 验证: llm_call_logs 表存在 = {exists}")

if __name__ == "__main__":
    asyncio.run(create_table())
