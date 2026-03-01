"""
生产环境数据库初始化脚本
一次性创建所有表并注入管理员账号
"""
import asyncio
from sqlalchemy import text
from app.core.database import engine, Base

# 导入所有模型，确保 Base.metadata 能感知到所有表
from app.models.user import User
from app.models.project import Project
from app.models.api_log import APILog
from app.models.skill import Skill
from app.models.agent import AgentDefinition, SimpleAgent
from app.models.ai_resource import AIResource
from app.models.ai_model import AIModel
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model_pricing import AIModelPricing
from app.models.ai_model_credential import AIModelCredential
from app.models.model_config import ModelConfig
from app.models.pipeline import Pipeline
from app.models.batch import Batch
from app.models.chapter import Chapter
from app.models.script import Script
from app.models.plot_breakdown import PlotBreakdown
from app.models.system_model_config import SystemModelConfig
from app.models.announcement import Announcement
from app.models.billing import Billing
from app.models.feedback import Feedback


async def init_db():
    print("正在创建所有数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"成功创建 {len(Base.metadata.tables)} 张表")

    print("\n正在注入管理员账号...")
    async with engine.begin() as conn:
        # 密码 admin123 的 bcrypt 哈希值
        await conn.execute(text("""
            INSERT INTO users (
                id, email, username, hashed_password, full_name,
                is_active, is_superuser, role, credits,
                created_at, updated_at
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440000',
                'admin@example.com',
                'admin',
                '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6L6s57OTWzKu7V7m',
                'Administrator',
                true, true, 'admin', 9999,
                NOW(), NOW()
            )
            ON CONFLICT (email) DO NOTHING
        """))
    print("管理员账号注入完成")
    print("\n初始化完成！")
    print("  账号: admin@example.com")
    print("  密码: admin123")


if __name__ == "__main__":
    asyncio.run(init_db())
