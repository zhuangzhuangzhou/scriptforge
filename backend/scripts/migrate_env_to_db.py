"""
环境变量迁移脚本

将现有的环境变量配置（OPENAI_API_KEY, ANTHROPIC_API_KEY 等）迁移到数据库

运行方式：
cd backend
python3 scripts/migrate_env_to_db.py
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.encryption import encryption_service
from app.models.ai_model_provider import AIModelProvider
from app.models.ai_model import AIModel
from app.models.ai_model_credential import AIModelCredential


async def migrate_openai(db: AsyncSession):
    """迁移 OpenAI 配置"""
    print("\n检查 OpenAI 配置...")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  未找到 OPENAI_API_KEY 环境变量")
        return False

    # 查找 OpenAI 提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.provider_key == "openai")
    )
    provider = result.scalar_one_or_none()

    if not provider:
        print("❌ 未找到 OpenAI 提供商，请先运行初始化脚本")
        return False

    # 检查是否已有凭证
    result = await db.execute(
        select(AIModelCredential).where(
            AIModelCredential.provider_id == provider.id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        print("⚠️  OpenAI 凭证已存在，跳过")
        return True

    # 创建凭证
    encrypted_key = encryption_service.encrypt(api_key)
    credential = AIModelCredential(
        provider_id=provider.id,
        credential_name="从环境变量迁移",
        api_key_encrypted=encrypted_key,
        is_active=True,
        is_system_default=True,
    )
    db.add(credential)
    await db.commit()

    print(f"✅ 已迁移 OpenAI API Key: {api_key[:10]}...")
    return True


async def migrate_anthropic(db: AsyncSession):
    """迁移 Anthropic 配置"""
    print("\n检查 Anthropic 配置...")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  未找到 ANTHROPIC_API_KEY 环境变量")
        return False

    # 查找 Anthropic 提供商
    result = await db.execute(
        select(AIModelProvider).where(AIModelProvider.provider_key == "anthropic")
    )
    provider = result.scalar_one_or_none()

    if not provider:
        print("❌ 未找到 Anthropic 提供商，请先运行初始化脚本")
        return False

    # 检查是否已有凭证
    result = await db.execute(
        select(AIModelCredential).where(
            AIModelCredential.provider_id == provider.id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        print("⚠️  Anthropic 凭证已存在，跳过")
        return True

    # 创建凭证
    encrypted_key = encryption_service.encrypt(api_key)
    credential = AIModelCredential(
        provider_id=provider.id,
        credential_name="从环境变量迁移",
        api_key_encrypted=encrypted_key,
        is_active=True,
        is_system_default=True,
    )
    db.add(credential)
    await db.commit()

    print(f"✅ 已迁移 Anthropic API Key: {api_key[:10]}...")
    return True


async def main():
    """主函数"""
    print("="*60)
    print("环境变量迁移脚本")
    print("="*60)

    print("\n此脚本将把环境变量中的 API Key 迁移到数据库")
    print("迁移的配置：")
    print("  - OPENAI_API_KEY")
    print("  - ANTHROPIC_API_KEY")

    # 检查加密密钥
    if not os.getenv("ENCRYPTION_KEY"):
        print("\n❌ 错误: 未设置 ENCRYPTION_KEY 环境变量")
        print("请先生成并设置加密密钥：")
        print('python3 -c "import os, base64; print(\'ENCRYPTION_KEY=\' + base64.b64encode(os.urandom(32)).decode())"')
        return

    async for db in get_db():
        results = []

        # 迁移 OpenAI
        results.append(await migrate_openai(db))

        # 迁移 Anthropic
        results.append(await migrate_anthropic(db))

        # 打印总结
        print("\n" + "="*60)
        print("迁移总结")
        print("="*60)

        success_count = sum(1 for r in results if r)
        print(f"成功迁移: {success_count} 个配置")

        if success_count > 0:
            print("\n✅ 迁移完成！")
            print("\n下一步：")
            print("1. 访问管理界面验证配置: http://localhost:3000/admin/models")
            print("2. 在凭证管理页面测试 API Key 是否有效")
            print("3. 如果测试通过，可以考虑从环境变量中移除 API Key")
        else:
            print("\n⚠️  没有配置需要迁移")

        break


if __name__ == "__main__":
    asyncio.run(main())
