#!/usr/bin/env python3
"""
验证管理端 API 修复 - 完整测试
测试所有 4 个接口是否正常工作
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目路径
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.core.database import AsyncSessionLocal

async def test_database_tables():
    """测试数据库表是否存在"""
    print("\n" + "=" * 60)
    print("测试 1: 检查数据库表")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        tables_to_check = ['api_logs', 'llm_call_logs', 'ai_tasks']

        for table_name in tables_to_check:
            query = text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                );
            """)
            result = await db.execute(query)
            exists = result.scalar()

            status = "✅" if exists else "❌"
            print(f"{status} 表 {table_name}: {'存在' if exists else '不存在'}")

            if not exists and table_name == 'api_logs':
                return False

    return True

async def test_stuck_tasks_query():
    """测试卡住任务查询"""
    print("\n" + "=" * 60)
    print("测试 2: 卡住任务查询 (/admin/tasks/stuck)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # 模拟接口查询逻辑
            from datetime import datetime, timedelta, timezone
            from sqlalchemy import select, and_, or_
            from app.models.ai_task import AITask
            from app.models.project import Project
            from app.models.user import User
            from app.models.batch import Batch
            from app.core.status import TaskStatus

            now = datetime.now(timezone.utc)
            timeout_time = now - timedelta(seconds=3600)
            stale_time = now - timedelta(seconds=1800)

            query = (
                select(AITask, User, Project, Batch)
                .outerjoin(Project, AITask.project_id == Project.id)
                .outerjoin(User, Project.user_id == User.id)
                .outerjoin(Batch, AITask.batch_id == Batch.id)
                .where(
                    and_(
                        AITask.status.in_([
                            TaskStatus.RUNNING,
                            TaskStatus.IN_PROGRESS,
                            TaskStatus.QUEUED
                        ]),
                        or_(
                            AITask.created_at < timeout_time,
                            AITask.updated_at < stale_time
                        )
                    )
                )
                .limit(1)
            )

            result = await db.execute(query)
            rows = result.all()

            print(f"✅ 查询成功: 找到 {len(rows)} 个卡住的任务")
            return True

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False

async def test_logs_stats_query():
    """测试日志统计查询"""
    print("\n" + "=" * 60)
    print("测试 3: 日志统计查询 (/admin/logs/stats)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            from datetime import datetime, timedelta, timezone
            from sqlalchemy import select, func, case
            from app.models.ai_task import AITask
            from app.core.status import TaskStatus

            now = datetime.now(timezone.utc)
            seven_days_ago = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

            # 测试 GROUP BY 查询
            day_column = func.date_trunc('day', AITask.created_at)
            daily_query = (
                select(
                    day_column.label("day"),
                    func.count(AITask.id).label("total"),
                    func.count(case((AITask.status == TaskStatus.COMPLETED, 1))).label("success")
                )
                .where(AITask.created_at >= seven_days_ago)
                .group_by(day_column)
                .order_by(day_column)
            )

            result = await db.execute(daily_query)
            rows = result.all()

            print(f"✅ 查询成功: 获取到 {len(rows)} 天的统计数据")
            return True

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False

async def test_llm_logs_query():
    """测试 LLM 日志查询"""
    print("\n" + "=" * 60)
    print("测试 4: LLM 日志查询 (/admin/llm-logs)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select, func
            from app.models.llm_call_log import LLMCallLog

            # 测试查询
            count_query = select(func.count(LLMCallLog.id))
            result = await db.execute(count_query)
            count = result.scalar()

            print(f"✅ 查询成功: 表中有 {count} 条记录")
            return True

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False

async def test_api_logs_query():
    """测试 API 日志查询"""
    print("\n" + "=" * 60)
    print("测试 5: API 日志查询 (/v1/admin/api-logs)")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select, func
            from app.models.api_log import APILog

            # 测试查询
            count_query = select(func.count(APILog.id))
            result = await db.execute(count_query)
            count = result.scalar()

            print(f"✅ 查询成功: 表中有 {count} 条记录")
            return True

        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False

async def main():
    print("=" * 60)
    print("管理端 API 修复 - 完整验证")
    print("=" * 60)

    tests = []

    # 测试 1: 数据库表
    result = await test_database_tables()
    tests.append(("数据库表检查", result))

    if not result:
        print("\n⚠️  api_logs 表不存在,跳过后续测试")
        return 1

    # 测试 2: 卡住任务查询
    result = await test_stuck_tasks_query()
    tests.append(("卡住任务查询", result))

    # 测试 3: 日志统计查询
    result = await test_logs_stats_query()
    tests.append(("日志统计查询", result))

    # 测试 4: LLM 日志查询
    result = await test_llm_logs_query()
    tests.append(("LLM 日志查询", result))

    # 测试 5: API 日志查询
    result = await test_api_logs_query()
    tests.append(("API 日志查询", result))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for name, result in tests:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
