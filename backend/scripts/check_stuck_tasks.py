#!/usr/bin/env python3
"""手动检查并终止卡住的任务

使用方法：
    python scripts/check_stuck_tasks.py
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tasks.task_monitor import check_and_terminate_stuck_tasks

if __name__ == "__main__":
    print("开始检查卡住的任务...")
    check_and_terminate_stuck_tasks()
    print("检查完成")
