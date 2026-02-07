import asyncio
import os
import sys
import re
from pathlib import Path
from sqlalchemy import select

# 添加 backend 目录到 sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

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
    frontmatter = {}
    body = content
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        yaml_str = match.group(1)
        body = match.group(2).strip()
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
            if not file_path.exists():
                print(f"⚠️ 文件不存在: {file_path}")
                continue

            print(f"处理: {item['key']}")
            try:
                content = file_path.read_text(encoding='utf-8')
                meta, body = parse_markdown(content)
                config_value = {"content": content, "body": body, "meta": meta}

                # 查找系统配置 (user_id=None)
                stmt = select(AIConfiguration).where(
                    AIConfiguration.key == item["key"],
                    AIConfiguration.user_id == None
                )
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  - 更新: {item['key']}")
                    existing.value = config_value
                    existing.description = meta.get("description", item["default_desc"])
                    existing.category = item["category"]
                    existing.is_active = True
                else:
                    print(f"  - 创建: {item['key']}")
                    new_config = AIConfiguration(
                        key=item["key"],
                        value=config_value,
                        description=meta.get("description", item["default_desc"]),
                        category=item["category"],
                        user_id=None,
                        is_active=True
                    )
                    db.add(new_config)
            except Exception as e:
                print(f"❌ 错误: {e}")

        await db.commit()
        print("✅ 完成")

if __name__ == "__main__":
    asyncio.run(init_configs())
