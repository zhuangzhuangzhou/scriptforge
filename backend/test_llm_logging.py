"""测试 LLM 日志记录功能"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.llm_call_log import LLMCallLog
from app.ai.adapters import get_adapter
from app.ai.llm_logger import set_llm_context, clear_llm_context


async def test_llm_logging():
    """测试 LLM 日志记录"""
    print("=" * 60)
    print("测试 LLM 日志记录功能")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. 清空测试前的上下文
        clear_llm_context()

        # 2. 设置测试上下文
        set_llm_context(
            task_id="test-task-123",
            user_id="test-user-456",
            project_id="test-project-789",
            skill_name="test_skill",
            stage="testing"
        )

        print("\n✅ 已设置 LLM 上下文")

        # 3. 获取适配器（传入数据库会话）
        try:
            adapter = await get_adapter(
                provider="openai",
                db=db,
                log_enabled=True
            )
            print(f"✅ 获取适配器成功: {adapter.__class__.__name__}")
            print(f"   - Provider: {adapter.provider_name}")
            print(f"   - Model: {adapter.model_name}")
            print(f"   - DB Session: {type(adapter._db).__name__}")
            print(f"   - Is Async DB: {adapter._is_async_db}")
            print(f"   - Log Enabled: {adapter._log_enabled}")
        except Exception as e:
            print(f"❌ 获取适配器失败: {e}")
            import traceback
            traceback.print_exc()
            return

        # 4. 查询日志记录前的数量
        stmt = select(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(5)
        result = await db.execute(stmt)
        logs_before = result.scalars().all()
        count_before = len(logs_before)
        print(f"\n📊 测试前最近 5 条日志记录:")
        for log in logs_before:
            print(f"   - {log.created_at}: {log.provider}/{log.model_name} - {log.status}")

        # 5. 调用 LLM（这会触发日志记录）
        print("\n🚀 开始调用 LLM...")
        try:
            response = adapter.generate(
                prompt="请用一句话介绍你自己",
                temperature=0.7,
                max_tokens=100
            )
            print(f"✅ LLM 调用成功")
            print(f"   响应长度: {len(response)} 字符")
            print(f"   响应预览: {response[:100]}...")
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            import traceback
            traceback.print_exc()

        # 6. 等待一下确保日志写入
        await asyncio.sleep(1)

        # 7. 查询日志记录后的数量
        await db.commit()  # 确保提交
        result = await db.execute(stmt)
        logs_after = result.scalars().all()
        count_after = len(logs_after)

        print(f"\n📊 测试后最近 5 条日志记录:")
        for log in logs_after:
            print(f"   - {log.created_at}: {log.provider}/{log.model_name} - {log.status}")
            if log.task_id:
                print(f"     Task ID: {log.task_id}")
            if log.skill_name:
                print(f"     Skill: {log.skill_name}")

        # 8. 验证结果
        print("\n" + "=" * 60)
        if count_after > count_before:
            print("✅ 测试通过：LLM 日志记录成功！")
            print(f"   新增日志记录: {count_after - count_before} 条")
        else:
            print("❌ 测试失败：没有新的日志记录")
        print("=" * 60)

        # 9. 清理上下文
        clear_llm_context()


if __name__ == "__main__":
    asyncio.run(test_llm_logging())
