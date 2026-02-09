#!/usr/bin/env python3
"""
批次 API 调试脚本
用于测试 /projects/{project_id}/batches 端点的返回数据
"""

import asyncio
import sys
sys.path.insert(0, '/Users/zhouqiang/Data/jim/backend')

from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.batch import Batch
from app.models.user import User
from sqlalchemy import select
import json

async def test_batches_api():
    async with AsyncSessionLocal() as db:
        # 获取一个测试项目
        result = await db.execute(
            select(Project).limit(1)
        )
        project = result.scalar_one_or_none()

        if not project:
            print("❌ 没有找到测试项目")
            return

        print(f"✅ 测试项目: {project.name} (ID: {project.id})")

        # 获取该项目的批次
        batches_result = await db.execute(
            select(Batch)
            .where(Batch.project_id == project.id)
            .order_by(Batch.batch_number)
            .limit(20)
        )
        batches = batches_result.scalars().all()

        # 计算总数
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count()).select_from(Batch).where(Batch.project_id == project.id)
        )
        total = count_result.scalar() or 0

        print(f"✅ 批次总数: {total}")
        print(f"✅ 查询到的批次数: {len(batches)}")

        # 模拟 API 返回的数据结构
        response_data = {
            "items": [
                {
                    "id": str(b.id),
                    "project_id": str(b.project_id),
                    "batch_number": b.batch_number,
                    "start_chapter": b.start_chapter,
                    "end_chapter": b.end_chapter,
                    "total_chapters": b.total_chapters,
                    "total_words": b.total_words,
                    "breakdown_status": b.breakdown_status,
                    "script_status": b.script_status
                }
                for b in batches
            ],
            "total": total
        }

        print("\n📦 API 返回的数据结构:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        # 验证数据结构
        print("\n🔍 数据结构验证:")
        print(f"  - 'items' 字段存在: {'items' in response_data}")
        print(f"  - 'total' 字段存在: {'total' in response_data}")
        print(f"  - 'items' 是列表: {isinstance(response_data.get('items'), list)}")
        print(f"  - 'total' 是数字: {isinstance(response_data.get('total'), int)}")

        if len(batches) > 0:
            print(f"\n📋 第一个批次的数据:")
            print(json.dumps(response_data['items'][0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(test_batches_api())
