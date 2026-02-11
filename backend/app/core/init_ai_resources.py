"""初始化系统内置 AI 资源文档

在应用启动时自动创建内置的改编方法论、输出风格、模板、示例等资源。
"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ai_resource import AIResource
import uuid


# 资源文件所在目录（相对于项目根目录）
RESOURCE_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "ai_flow_desc" / "webtoon-skill"

# ==================== 内置资源定义 ====================

BUILTIN_RESOURCES = [
    {
        "name": "adapt_method_default",
        "display_name": "网文改编方法论（通用版）",
        "description": "网文改编漫剧创作方法论，适用于60万-300万字长篇小说改编为动态漫剧，包含小说解析、冲突提取、情绪钩子识别、剧情拆解、分集标注、节奏控制等全流程指导",
        "category": "adapt_method",
        "file_path": "adapt-method.md",
    },
    {
        "name": "output_style_default",
        "display_name": "改编输出风格",
        "description": "网文改编漫剧的输出风格，语言简洁有力、视觉冲击强烈、节奏极快无尿点、情绪钩子密集爆发",
        "category": "output_style",
        "file_path": "output-style.md",
    },
    {
        "name": "plot_breakdown_template_default",
        "display_name": "剧情拆解格式模板",
        "description": "剧情拆解的标准输出格式模板，定义了剧情列表的结构和使用说明",
        "category": "template",
        "file_path": "templates/plot-breakdown-template.md",
    },
    {
        "name": "plot_breakdown_example_default",
        "display_name": "剧情拆解示例",
        "description": "剧情拆解的完整示例，以《我的治愈系游戏》为例展示标准拆解格式",
        "category": "example",
        "file_path": "examples/plot-breakdown-example.md",
    },
]


def _load_resource_content(relative_path: str) -> str:
    """从文件系统加载资源内容"""
    file_path = RESOURCE_BASE_DIR / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"资源文件不存在: {file_path}")
    return file_path.read_text(encoding="utf-8")


# ==================== 初始化函数 ====================

async def init_builtin_resources(db: AsyncSession):
    """初始化系统内置 AI 资源文档"""
    print("初始化内置 AI 资源文档...")

    created_count = 0
    for res_def in BUILTIN_RESOURCES:
        # 按 name + is_builtin 查询是否已存在
        result = await db.execute(
            select(AIResource).where(
                AIResource.name == res_def["name"],
                AIResource.is_builtin == True,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  - 资源已存在: {res_def['display_name']}")
            continue

        # 加载 Markdown 内容
        content = _load_resource_content(res_def["file_path"])

        resource = AIResource(
            id=uuid.uuid4(),
            name=res_def["name"],
            display_name=res_def["display_name"],
            description=res_def["description"],
            category=res_def["category"],
            content=content,
            is_builtin=True,
            owner_id=None,
            visibility="public",
            is_active=True,
            version=1,
        )
        db.add(resource)
        created_count += 1
        print(f"  + 创建资源: {res_def['display_name']}")

    await db.commit()
    print(f"完成 AI 资源初始化（新建 {created_count} 个，共 {len(BUILTIN_RESOURCES)} 个内置资源）")
