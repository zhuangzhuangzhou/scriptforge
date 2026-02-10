#!/bin/bash
# Celery Worker 重启脚本

echo "=========================================="
echo "Celery Worker 重启脚本"
echo "=========================================="

# 查找并停止现有的 Celery worker 进程
echo ""
echo "1. 查找现有的 Celery worker 进程..."
CELERY_PIDS=$(ps aux | grep 'celery.*worker' | grep -v grep | awk '{print $2}')

if [ -z "$CELERY_PIDS" ]; then
    echo "   ℹ️  没有发现运行中的 Celery worker"
else
    echo "   发现以下 Celery worker 进程:"
    ps aux | grep 'celery.*worker' | grep -v grep
    
    echo ""
    echo "2. 停止现有的 Celery worker..."
    for PID in $CELERY_PIDS; do
        echo "   停止进程 $PID..."
        kill -TERM $PID
    done
    
    # 等待进程退出
    echo "   等待进程退出..."
    sleep 3
    
    # 检查是否还有残留进程
    REMAINING=$(ps aux | grep 'celery.*worker' | grep -v grep | wc -l)
    if [ $REMAINING -gt 0 ]; then
        echo "   ⚠️  仍有进程未退出，强制终止..."
        for PID in $CELERY_PIDS; do
            kill -9 $PID 2>/dev/null
        done
    fi
    
    echo "   ✅ 已停止所有 Celery worker"
fi

echo ""
echo "3. 启动新的 Celery worker..."
echo "   使用虚拟环境: backend/venv/"

# 激活虚拟环境并启动 Celery
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "   ✅ 虚拟环境已激活"
else
    echo "   ⚠️  未找到虚拟环境，使用系统 Python"
fi

echo ""
echo "   启动命令: celery -A app.core.celery_app worker --loglevel=info"
echo ""
echo "=========================================="
echo "Celery Worker 正在运行..."
echo "按 Ctrl+C 停止"
echo "=========================================="
echo ""

# 启动 Celery worker
celery -A app.core.celery_app worker --loglevel=info
