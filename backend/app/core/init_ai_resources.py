"""初始化系统内置 AI 资源文档

在应用启动时自动创建内置的改编方法论、输出风格、模板、示例等资源。
"""
from __future__ import annotations

from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ai_resource import AIResource
import uuid


# 资源文件所在目录（相对于项目根目录）
RESOURCE_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "ai_flow_desc" / "webtoon-skill"

# ==================== 内置资源定义 ====================

BUILTIN_RESOURCES = [
    # ========== 方法论（methodology）：改编方法论文档 ==========
    {
        "name": "adapt_method_default",
        "display_name": "网文改编方法论（通用版）",
        "description": "网文改编漫剧创作方法论，适用于60万-300万字长篇小说改编为动态漫剧，包含小说解析、冲突提取、情绪钩子识别、剧情拆解、分集标注、节奏控制等全流程指导",
        "category": "methodology",
        "file_path": "adapt-method.md",
    },
    {
        "name": "adapt_method_core",
        "display_name": "核心原则",
        "description": "网文改编漫剧核心原则，所有阶段必读的基础方法论，包含改编公式、情绪钩子类型、冲突分级、节奏控制等",
        "category": "methodology",
        "file_path": "adapt-method-core.md",
    },
    {
        "name": "adapt_method_breakdown",
        "display_name": "剧情拆解方法论",
        "description": "剧情拆解专用方法论，用于从小说章节中提取剧情点并标注分集，包含拆解公式、分集标准、压缩策略等",
        "category": "methodology",
        "file_path": "adapt-method-breakdown.md",
    },
    {
        "name": "adapt_method_script",
        "display_name": "剧本创作方法论",
        "description": "单集剧本创作专用方法论，用于将剧情点转化为完整剧本，包含格式规范、对话写作、视觉化转换等",
        "category": "methodology",
        "file_path": "adapt-method-script.md",
    },
    # ========== 方法论 - 类型专属文档 ==========
    {
        "name": "adapt_method_type_xuanhuan",
        "display_name": "玄幻/武侠类型指南",
        "description": "玄幻/武侠类型专属改编指南，包含境界体系、打脸节奏、战斗压缩等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-xuanhuan.md",
        "metadata": {"novel_type": "xuanhuan"},
    },
    {
        "name": "adapt_method_type_dushi",
        "display_name": "都市/现代类型指南",
        "description": "都市/现代类型专属改编指南，包含身份反差、财富展示、商战压缩等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-dushi.md",
        "metadata": {"novel_type": "dushi"},
    },
    {
        "name": "adapt_method_type_yanqing",
        "display_name": "言情/古言类型指南",
        "description": "言情/古言类型专属改编指南，包含虐心节奏、甜宠技巧、误会设计等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-yanqing.md",
        "metadata": {"novel_type": "yanqing"},
    },
    {
        "name": "adapt_method_type_xuanyi",
        "display_name": "悬疑/推理类型指南",
        "description": "悬疑/推理类型专属改编指南，包含悬念设置、反转设计、紧张氛围等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-xuanyi.md",
        "metadata": {"novel_type": "xuanyi"},
    },
    {
        "name": "adapt_method_type_kehuan",
        "display_name": "科幻/末世类型指南",
        "description": "科幻/末世类型专属改编指南，包含异能系统、危机升级、团队战斗等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-kehuan.md",
        "metadata": {"novel_type": "kehuan"},
    },
    {
        "name": "adapt_method_type_chongsheng",
        "display_name": "重生复仇类型指南",
        "description": "重生复仇类型专属改编指南，包含重生开场、先知优势、复仇节奏等",
        "category": "methodology",
        "file_path": "adapt-method-types/type-chongsheng.md",
        "metadata": {"novel_type": "chongsheng"},
    },
    # ========== 输出风格（output_style）==========
    {
        "name": "output_style_default",
        "display_name": "改编输出风格",
        "description": "网文改编漫剧的输出风格，语言简洁有力、视觉冲击强烈、节奏极快无尿点、情绪钩子密集爆发",
        "category": "output_style",
        "file_path": "output-style.md",
    },
    # ========== 质检标准（qa_rules）==========
    {
        "name": "adapt_method_rules",
        "display_name": "改编禁忌与质量标准",
        "description": "改编禁忌与质量标准，用于质检阶段评估改编质量，包含致命错误、核心原则、评分标准、降级策略等",
        "category": "qa_rules",
        "file_path": "adapt-method-rules.md",
    },
    # ========== 模板案例（template）==========
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
        "category": "template",
        "file_path": "examples/plot-breakdown-example.md",
    },
]

# 小说类型映射表（用于动态加载类型专属文档）
NOVEL_TYPE_MAPPING = {
    "xuanhuan": "adapt_method_type_xuanhuan",  # 玄幻/武侠
    "wuxia": "adapt_method_type_xuanhuan",      # 武侠 -> 玄幻
    "dushi": "adapt_method_type_dushi",         # 都市/现代
    "xiandai": "adapt_method_type_dushi",       # 现代 -> 都市
    "yanqing": "adapt_method_type_yanqing",     # 言情/古言
    "guyan": "adapt_method_type_yanqing",       # 古言 -> 言情
    "xuanyi": "adapt_method_type_xuanyi",       # 悬疑/推理
    "tuili": "adapt_method_type_xuanyi",        # 推理 -> 悬疑
    "kehuan": "adapt_method_type_kehuan",       # 科幻/末世
    "moshi": "adapt_method_type_kehuan",        # 末世 -> 科幻
    "chongsheng": "adapt_method_type_chongsheng",  # 重生复仇
    "fuchou": "adapt_method_type_chongsheng",   # 复仇 -> 重生
}


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


# ==================== 资源加载辅助函数 ====================

def get_type_resource_name(novel_type: str) -> str | None:
    """根据小说类型获取对应的资源名称

    Args:
        novel_type: 小说类型（如 xuanhuan, dushi, yanqing 等）

    Returns:
        str | None: 资源名称，如果类型不存在则返回 None
    """
    return NOVEL_TYPE_MAPPING.get(novel_type.lower())


async def load_layered_resources(
    db: AsyncSession,
    stage: str,
    novel_type: str | None = None
) -> dict[str, str]:
    """按阶段加载分层资源文档

    根据不同阶段加载对应的资源文档，实现按需加载，减少 Token 消耗。

    Args:
        db: 数据库会话
        stage: 阶段名称（breakdown / script / qa）
        novel_type: 小说类型（可选，用于加载类型专属文档）

    Returns:
        dict[str, str]: 资源内容字典，key 为资源类型，value 为内容

    加载策略：
        - breakdown（剧情拆解）: core + breakdown + type-{类型}
        - script（剧本创作）: core + script + type-{类型}
        - qa（质检）: core + rules
    """
    resources = {}

    # 1. 始终加载核心文档
    core = await _load_resource_by_name(db, "adapt_method_core")
    if core:
        resources["core"] = core

    # 2. 根据阶段加载专用文档
    if stage == "breakdown":
        breakdown = await _load_resource_by_name(db, "adapt_method_breakdown")
        if breakdown:
            resources["breakdown"] = breakdown
    elif stage == "script":
        script = await _load_resource_by_name(db, "adapt_method_script")
        if script:
            resources["script"] = script
    elif stage == "qa":
        rules = await _load_resource_by_name(db, "adapt_method_rules")
        if rules:
            resources["rules"] = rules

    # 3. 加载类型专属文档（breakdown 和 script 阶段）
    if novel_type and stage in ("breakdown", "script"):
        type_resource_name = get_type_resource_name(novel_type)
        if type_resource_name:
            type_doc = await _load_resource_by_name(db, type_resource_name)
            if type_doc:
                resources["type"] = type_doc

    return resources


async def _load_resource_by_name(db: AsyncSession, name: str) -> str | None:
    """按名称加载资源内容

    Args:
        db: 数据库会话
        name: 资源名称

    Returns:
        str | None: 资源内容，如果不存在则返回 None
    """
    result = await db.execute(
        select(AIResource).where(
            AIResource.name == name,
            AIResource.is_active == True
        )
    )
    resource = result.scalar_one_or_none()
    return resource.content if resource else None


def load_layered_resources_sync(
    db,
    stage: str,
    novel_type: str | None = None
) -> dict[str, str]:
    """按阶段加载分层资源文档（同步版本）

    Args:
        db: 同步数据库会话
        stage: 阶段名称（breakdown / script / qa）
        novel_type: 小说类型（可选）

    Returns:
        dict[str, str]: 资源内容字典
    """
    resources = {}

    # 1. 始终加载核心文档
    core = _load_resource_by_name_sync(db, "adapt_method_core")
    if core:
        resources["core"] = core

    # 2. 根据阶段加载专用文档
    if stage == "breakdown":
        breakdown = _load_resource_by_name_sync(db, "adapt_method_breakdown")
        if breakdown:
            resources["breakdown"] = breakdown
    elif stage == "script":
        script = _load_resource_by_name_sync(db, "adapt_method_script")
        if script:
            resources["script"] = script
    elif stage == "qa":
        rules = _load_resource_by_name_sync(db, "adapt_method_rules")
        if rules:
            resources["rules"] = rules

    # 3. 加载类型专属文档
    if novel_type and stage in ("breakdown", "script"):
        type_resource_name = get_type_resource_name(novel_type)
        if type_resource_name:
            type_doc = _load_resource_by_name_sync(db, type_resource_name)
            if type_doc:
                resources["type"] = type_doc

    return resources


def _load_resource_by_name_sync(db, name: str) -> str | None:
    """按名称加载资源内容（同步版本）"""
    result = db.execute(
        select(AIResource).where(
            AIResource.name == name,
            AIResource.is_active == True
        )
    )
    resource = result.scalar_one_or_none()
    return resource.content if resource else None
