#!/bin/bash
# Celery Worker 和 Beat 启动脚本
# 使用前台模式避免 macOS 兼容性问题

set -e

cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 设置日志目录
LOG_DIR="../logs"
mkdir -p "$LOG_DIR"

# 停止旧的进程
echo "停止旧的 Celery 进程..."
pkill -9 -f "celery" 2>/dev/null || true
sleep 2

echo ""
echo "=== Celery 启动说明 ==="
echo "由于 macOS 兼容性问题，建议使用以下方式启动："
echo ""
echo "方式 1: 使用 tmux/screen（推荐）"
echo "  tmux new -s celery-worker"
echo "  cd backend && source venv/bin/activate"
echo "  celery -A app.core.celery_app worker --loglevel=info"
echo ""
echo "  # 新开一个窗口"
echo "  tmux new -s celery-beat"
echo "  cd backend && source venv/bin/activate"
echo "  celery -A app.core.celery_app beat --loglevel=info"
echo ""
echo "方式 2: 使用 nohup（后台运行）"
echo "  nohup celery -A app.core.celery_app worker --loglevel=info > ../logs/celery_worker.log 2>&1 &"
echo "  nohup celery -A app.core.celery_app beat --loglevel=info > ../logs/celery_beat.log 2>&1 &"
echo ""
echo "方式 3: 仅启动 Worker（不启动定时任务监控）"
echo "  celery -A app.core.celery_app worker --loglevel=info"
echo ""
echo "=== 当前操作 ==="
echo "正在使用 nohup 启动..."
echo ""

# 使用 nohup 启动 Worker
nohup celery -A app.core.celery_app worker --loglevel=info > "$LOG_DIR/celery_worker.log" 2>&1 &
WORKER_PID=$!
echo "Worker PID: $WORKER_PID"

sleep 3

# 使用 nohup 启动 Beat
nohup celery -A app.core.celery_app b-loglevel=info > "$LOG_DIR/celery_beat.log" 2>&1 &
BEAT_PID=$!
echo "Beat PID: $BEAT_PID"

sleep 3

# 验证启动
echo ""
echo "=== 验证启动状态 ==="

if ps -p $WORKER_PID > /dev/null 2>&1; then
    echo "✓ Celery Worker 正在运行 (PID: $WORKER_PID)"
else
    echo "✗ Celery Worker 启动失败"
    echo "查看日志: cat $LOG_DIR/celery_worker.log"
    exit 1
fi

if ps -p $BEAT_PID > /dev/null 2>&1; then
    echo "✓ Celery Beat 正在运行 (PID: $BEAT_PID)"
else
    echo "✗ Celery Beat 启动失败"
    echo "查看日志: cat $LOG_DIR/celery_beat.log"
fi

echo ""
echo "=== 查看日志 ==="
echo "  Worker: tail -f $LOG_DIR/celery_worker.log"
echo "  Beat:   tail -f $LOG_DIR/celery_beat.log"
echo ""
echo "=== 停止服务 ==="
echo "  pkill -f 'celery.*worker'"
echo "  pkill -f 'celery.*beat'"
