#!/usr/bin/env python3
"""
清空所有项目的剧集拆解数据
用于重新测试

注意：
- plot_breakdowns 表的 batch_id 有外键到 batches
- 需先删除 plot_breakdowns，再删除 batches
"""

import os
import sys

# 设置环境变量，加载配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import sync_engine
from sqlalchemy import text


def clear_breakdown_data():
    """清空所有剧集拆解数据"""

    print("🗑️  开始清空剧集拆解数据...")
    print("-" * 50)

    with sync_engine.connect() as conn:
        # 1. 先清空 plot_breakdowns（删除与 batches 关联的数据）
        result = conn.execute(text("SELECT COUNT(*) FROM plot_breakdowns"))
        plot_count = result.scalar()
        print(f"📊 当前 plot_breakdowns 记录数: {plot_count}")

        conn.execute(text("TRUNCATE TABLE plot_breakdowns RESTART IDENTITY CASCADE"))
        print("✅ 已清空 plot_breakdowns 表")

        # 2. 再清空 batches
        result = conn.execute(text("SELECT COUNT(*) FROM batches"))
        batch_count = result.scalar()
        print(f"📊 当前 batches 记录数: {batch_count}")

        conn.execute(text("TRUNCATE TABLE batches RESTART IDENTITY CASCADE"))
        print("✅ 已清空 batches 表")

        conn.commit()

    print("-" * 50)
    print("🎉 剧集拆解数据已全部清空！")
    print("💡 你可以重新开始测试了")


if __name__ == "__main__":
    clear_breakdown_data()
