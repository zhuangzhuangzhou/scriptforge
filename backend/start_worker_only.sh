#!/bin/bash
# 仅启动 Celery Worker（不启动 Beat）
# 这是 macOS 上最稳定的方式

cd "$(dirname "$0")"
source venv/bin/activate

echo "=== 启动 Celery Worker ==="
echo ""
echo "提示："
echo "  - 任务可以正常执行（剧本生成、剧情拆解）"
echo "  - 没有自动监控，需要通过管理端页面手动清理卡住的任务"
echo "  - 访问 /admin/tasks 查看任务状态"
echo ""
echo "按 Ctrl+C 停止 Worker"
echo ""

# 前台运行 Worker
celery -A app.core.celery_app worker --loglevel=info
