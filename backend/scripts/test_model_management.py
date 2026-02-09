"""模型管理功能测试脚本

测试核心功能：
1. 加密服务
2. ModelConfigService
3. get_adapter 函数
4. CreditsService 计费规则
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.encryption import EncryptionService
from app.ai.adapters.model_config_service import ModelConfigService
from app.ai.adapters import get_adapter
from app.core.credits import CreditsService


async def test_encryption_service():
    """测试加密服务"""
    print("\n" + "="*60)
    print("测试 1: 加密服务")
    print("="*60)

    try:
        encryption = EncryptionService()

        # 测试加密和解密
        test_key = "sk-test1234567890abcdefghijklmnopqrstuvwxyz"
        print(f"原始 API Key: {test_key}")

        encrypted = encryption.encrypt(test_key)
        print(f"加密后: {encrypted[:50]}...")

        decrypted = encryption.decrypt(encrypted)
        print(f"解密后: {decrypted}")

        if decrypted == test_key:
            print("✅ 加密/解密测试通过")
            return True
        else:
            print("❌ 加密/解密测试失败")
            return False
    except Exception as e:
        print(f"❌ 加密服务测试失败: {e}")
        return False


async def test_model_config_service():
    """测试模型配置服务"""
    print("\n" + "="*60)
    print("测试 2: ModelConfigService")
    print("="*60)

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with AsyncSessionLocal() as db:
            config_service = ModelConfigService(db)

            # 测试获取默认模型配置
            print("\n测试获取默认模型配置...")
            config = await config_service.get_model_config()

            if config:
                print(f"✅ 成功获取默认模型配置:")
                print(f"  - 提供商: {config['provider_key']}")
                print(f"  - 模型: {config['model_key']}")
                print(f"  - API Key: {config['api_key'][:10]}...")
                print(f"  - 最大 Token: {config['max_tokens']}")
                return True
            else:
                print("⚠️  数据库中没有配置，将使用环境变量降级")
                return True
    except Exception as e:
        print(f"❌ ModelConfigService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def test_get_adapter():
    """测试 get_adapter 函数"""
    print("\n" + "="*60)
    print("测试 3: get_adapter 函数")
    print("="*60)

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with AsyncSessionLocal() as db:
            # 测试从数据库获取适配器
            print("\n测试从数据库获取适配器...")
            adapter = await get_adapter(db=db)

            if adapter:
                print(f"✅ 成功创建适配器: {type(adapter).__name__}")
                return True
            else:
                print("❌ 创建适配器失败")
                return False
    except Exception as e:
        print(f"❌ get_adapter 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def test_credits_service():
    """测试积分服务计费规则"""
    print("\n" + "="*60)
    print("测试 4: CreditsService 计费规则")
    print("="*60)

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with AsyncSessionLocal() as db:
            credits_service = CreditsService(db)

            # 测试获取计费规则
            print("\n测试获取默认计费规则...")
            input_price, output_price = await credits_service.get_pricing_rule()
            print(f"  - 输入价格: {input_price} 积分/1K tokens")
            print(f"  - 输出价格: {output_price} 积分/1K tokens")

            # 测试计算积分消耗
            print("\n测试计算积分消耗...")
            input_tokens = 1000
            output_tokens = 500
            credits = await credits_service.calculate_model_credits(
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            print(f"  - 输入: {input_tokens} tokens")
            print(f"  - 输出: {output_tokens} tokens")
            print(f"  - 总消耗: {credits} 积分")

            print("✅ CreditsService 测试通过")
            return True
    except Exception as e:
        print(f"❌ CreditsService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("模型管理功能测试")
    print("="*60)

    results = []

    # 运行测试
    results.append(("加密服务", await test_encryption_service()))
    results.append(("ModelConfigService", await test_model_config_service()))
    results.append(("get_adapter", await test_get_adapter()))
    results.append(("CreditsService", await test_credits_service()))

    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
