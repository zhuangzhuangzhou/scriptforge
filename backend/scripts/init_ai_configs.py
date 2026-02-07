import asyncio
import os
import sys
import re
from pathlib import Path

# 添加 backend 目录到 sys.path，以便导入 app 模块
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.ai_configuration import AIConfiguration

# 基础路径
PROJECT_ROOT = backend_dir.parent
DOCS_DIR = PROJECT_ROOT / "docs" / "ai_flow_desc"

# 映射配置
CONFIG_MAPPING = [
    {
        "file_path": DOCS_DIR / "webtoon-skill" / "adapt-method.md",
        "key": "adapt_method_default",
        "category": "adapt_method",
        "default_desc": "系统默认：网文改编漫剧创作方法论"
    },
    {
        "file_path": DOCS_DIR / "webtoon-skill" / "output-style.md",
        "key": "output_style_default",
        "category": "adapt_method",
        "default_desc": "系统默认：输出风格规范"
    },
    {
        "file_path": DOCS_DIR / "breakdown-aligner.md",
        "key": "qa_breakdown_default",
        "category": "quality_rule",
        "default_desc": "系统默认：剧情拆解质量校验规则"
    }
]

def parse_markdown(content: str):
    """简单的 Frontmatter 解析器"""
    frontmatter = {}
    body = content

    # 匹配 YAML Frontmatter
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        yaml_str = match.group(1)
        body = match.group(2).strip()

        # 简单解析 YAML (key: value)
        for line in yaml_str.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                frontmatter[k.strip()] = v.strip()

    return frontmatter, body

async def init_configs():
    print("开始初始化 AI 配置...")

    async with AsyncSessionLocal() as db:
        for item in CONFIG_MAPPING:
            file_path = item["file_path"]
            key = item["key"]
            category = item["category"]

            if not file_path.exists():
                print(f"⚠️ 文件不存在，跳过: {file_path}")
                continue

            print(f"处理文件: {file_path.name} -> Key: {key}")

            try:
                content = file_path.read_text(encoding='utf-8')
                meta, body = parse_markdown(content)

                # 构造存储的 JSON Value
                # 我们保留原始 Markdown 内容，同时也提取元数据
                config_value = {
                    "content": content,     # 完整原始内容
                    "body": body,           # 去除 Frontmatter 的正文
                    "meta": meta            # 提取的元数据
                }

                # 优先使用文件中的 description，否则使用默认
                description = meta.get("description", item["default_desc"])

                # 查询是否存在 (系统配置 user_id=None)
                stmt = select(AIConfiguration).where(
                    AIConfiguration.key == key,
                    AIConfiguration.user_id == None
                )
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  - 更新现有配置: {key}")
                    existing.value = config_value
                    existing.description = description
                    existing.category = category
                    existing.is_active = True
                else:
                    print(f"  - 创建新配置: {key}")
                    new_config = AIConfiguration(
                        key=key,
                        value=config_value,
                        description=description,
                        category=category,
                        user_id=None,
                        is_active=True
                    )
                    db.add(new_config)

            except Exception as e:
                print(f"❌ 处理 {key} 时出错: {str(e)}")

        await db.commit()
        print("✅ 配置初始化完成")

if __name__ == "__main__":
    asyncio.run(init_configs())
