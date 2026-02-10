#!/bin/bash
# 后台启动 Celery Worker 脚本

echo "=========================================="
echo "后台启动 Celery Worker"
echo "=========================================="

cd "$(dirname "$0")"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️  未找到虚拟环境"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 后台启动 Celery worker，输出到日志文件
echo "启动 Celery worker（后台运行）..."
nohup celery -A app.core.celery_app worker --loglevel=info > logs/celery_worker.log 2>&1 &

CELERY_PID=$!
echo "✅ Celery worker 已启动，PID: $CELERY_PID"
echo "   日志文件: backend/logs/celery_worker.log"
echo ""
echo "查看日志: tail -f backend/logs/celery_worker.log"
echo "停止 worker: kill $CELERY_PID"
echo "=========================================="
