"""初始化内置 Skills

统一使用模板驱动方式，废弃 module_path + class_name 方式。
实际的 Skill 定义在 init_simple_system.py 中。
"""
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# 系统内置 Skill 归属的固定 owner_id（不需要真实用户）
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def init_builtin_skills(db: AsyncSession):
    """初始化内置 Skills 到数据库

    注意：此函数已废弃，实际初始化逻辑在 init_simple_system.py 中。
    保留此函数是为了兼容现有的启动流程。
    """
    # 导入并调用统一的初始化函数
    from app.core.init_simple_system import init_simple_system

    try:
        await init_simple_system(db)
    except Exception as e:
        print(f"初始化 Skills 时出错: {e}")
        # 不抛出异常，允许应用继续启动
