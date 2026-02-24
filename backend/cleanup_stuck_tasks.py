#!/usr/bin/env python
"""手动清理卡住的任务

由于 Celery Beat 在 macOS 上无法稳定运行，
使用此脚本手动清理超时或停滞的任务。

建议每小时运行一次，或在发现任务卡住时运行。
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks.task_monitor import check_and_terminate_stuck_tasks

if __name__ == "__main__":
    print("=== 开始检查卡住的任务 ===\n")
    try:
        check_and_terminate_stuck_tasks()
        print("\n✓ 检查完成")
    except Exception as e:
        print(f"\n✗ 检查失败: {e}")
        sys.exit(1)
