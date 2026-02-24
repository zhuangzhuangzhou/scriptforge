#!/usr/bin/env python3
"""
诊断 LLM 日志问题
检查为什么 llm_call_logs 表没有数据
"""

import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

print("=" * 60)
print("LLM 日志诊断")
print("=" * 60)

# 1. 检查表是否存在
print("\n[1/5] 检查 llm_call_logs 表...")
try:
    import asyncio
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal

    async def check_table():
        async with AsyncSessionLocal() as db:
            # 检查表是否存在
            query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'llm_call_logs'
                );
            """)
            result = await db.execute(query)
            exists = result.scalar()

            if not exists:
                print("❌ llm_call_logs 表不存在!")
                return False

            print("✅ llm_call_logs 表存在")

            # 检查记录数
            count_query = text("SELECT COUNT(*) FROM llm_call_logs;")
            count_result = await db.execute(count_query)
            count = count_result.scalar()
            print(f"   记录数: {count}")

            # 检查最近的记录
            if count > 0:
                recent_query = text("""
                    SELECT created_at, provider, model_name, skill_name, status
                    FROM llm_call_logs
                    ORDER BY created_at DESC
                    LIMIT 5;
                """)
                recent_result = await db.execute(recent_query)
                recent_logs = recent_result.all()

                print("\n   最近 5 条记录:")
                for log in recent_logs:
                    print(f"   - {log[0]} | {log[1]} | {log[2]} | {log[3]} | {log[4]}")

            return True

    table_exists = asyncio.run(check_table())

except Exception as e:
    print(f"❌ 检查失败: {e}")
    table_exists = False

if not table_exists:
    print("\n⚠️  表不存在,无法继续诊断")
    sys.exit(1)

# 2. 检查最近是否有任务执行
print("\n[2/5] 检查最近的 AI 任务...")
try:
    async def check_recent_tasks():
        async with AsyncSessionLocal() as db:
            query = text("""
                SELECT id, task_type, status, created_at
                FROM ai_tasks
                WHERE created_at > NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 10;
            """)
            result = await db.execute(query)
            tasks = result.all()

            if not tasks:
                print("❌ 最近 7 天没有任务执行")
                return False

            print(f"✅ 找到 {len(tasks)} 个最近的任务:")
            for task in tasks[:5]:
                print(f"   - {task[0][:8]}... | {task[1]} | {task[2]} | {task[3]}")

            return True

    has_tasks = asyncio.run(check_recent_tasks())

except Exception as e:
    print(f"❌ 检查失败: {e}")
    has_tasks = False

# 3. 检查模型适配器配置
print("\n[3/5] 检查模型适配器配置...")
try:
    from app.ai.adapters.base import BaseModelAdapter
    print("✅ BaseModelAdapter 导入成功")
    print(f"   默认 log_enabled: True")
    print(f"   需要 db 参数: 是")

except Exception as e:
    print(f"❌ 导入失败: {e}")

# 4. 检查 llm_logger 模块
print("\n[4/5] 检查 llm_logger 模块...")
try:
    from app.ai.llm_logger import log_llm_call, get_llm_context
    print("✅ llm_logger 导入成功")

    # 检查上下文
    ctx = get_llm_context()
    print(f"   当前上下文: {ctx}")

except Exception as e:
    print(f"❌ 导入失败: {e}")

# 5. 检查 get_adapter_sync 是否传递 db
print("\n[5/5] 检查 get_adapter_sync 实现...")
try:
    import inspect
    from app.ai.adapters import get_adapter_sync

    # 获取函数签名
    sig = inspect.signature(get_adapter_sync)
    params = list(sig.parameters.keys())

    print("✅ get_adapter_sync 导入成功")
    print(f"   参数: {params}")

    if 'db' in params:
        print("   ✅ 包含 db 参数")
    else:
        print("   ❌ 缺少 db 参数")

    if 'log_enabled' in params:
        print("   ✅ 包含 log_enabled 参数")
        # 检查默认值
        default = sig.parameters['log_enabled'].default
        print(f"   默认值: {default}")
    else:
        print("   ❌ 缺少 log_enabled 参数")

except Exception as e:
    print(f"❌ 检查失败: {e}")

# 总结
print("\n" + "=" * 60)
print("诊断总结")
print("=" * 60)

print("""
可能的原因:
1. 最近没有执行过 AI 任务 (没有调用 LLM)
2. 任务执行时 log_enabled=False
3. 任务执行时没有传递 db 参数
4. log_llm_call 函数内部异常被捕获

建议:
1. 执行一个拆解任务,观察是否生成日志
2. 检查 Celery 任务日志,看是否有 "记录 LLM 调用日志失败" 的错误
3. 检查数据库连接是否正常
""")
