#!/bin/bash

echo "=" * 60
echo "🔍 检查所有服务状态"
echo "=========================================="

# 1. 后端服务
echo ""
echo "1️⃣  后端服务 (FastAPI):"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 运行中 (http://localhost:8000)"
    curl -s http://localhost:8000/health
else
    echo "   ❌ 未运行"
fi

# 2. Celery Worker
echo ""
echo "2️⃣  Celery Worker:"
CELERY_COUNT=$(ps aux | grep -E "celery.*worker" | grep -v grep | wc -l)
if [ $CELERY_COUNT -gt 0 ]; then
    echo "   ✅ 运行中 ($CELERY_COUNT 个进程)"
    ps aux | grep -E "celery.*worker" | grep -v grep | head -1 | awk '{print "   PID:", $2}'
else
    echo "   ❌ 未运行"
fi

# 3. 前端服务
echo ""
echo "3️⃣  前端服务 (Vite):"
if lsof -i:5173 > /dev/null 2>&1; then
    echo "   ✅ 运行中 (http://localhost:5173)"
else
    echo "   ❌ 未运行"
fi

# 4. SSH 隧道
echo ""
echo "4️⃣  SSH 隧道:"
TUNNEL_OK=true
for port in 5433 6380 9000; do
    if lsof -i:$port > /dev/null 2>&1; then
        echo "   ✅ 端口 $port: 已连接"
    else
        echo "   ❌ 端口 $port: 未连接"
        TUNNEL_OK=false
    fi
done

echo ""
echo "=========================================="
if [ "$TUNNEL_OK" = true ]; then
    echo "✅ 所有服务正常运行"
else
    echo "⚠️  部分服务未运行"
fi
echo "=========================================="
