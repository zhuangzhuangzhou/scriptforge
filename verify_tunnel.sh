#!/bin/bash

echo "🔍 检查 SSH 隧道状态..."
echo ""

# 检查端口
check_port() {
    local port=$1
    local service=$2
    if lsof -i:$port > /dev/null 2>&1; then
        echo "✅ $service (端口 $port): 已连接"
        return 0
    else
        echo "❌ $service (端口 $port): 未连接"
        return 1
    fi
}

check_port 5433 "PostgreSQL"
check_port 6380 "Redis"
check_port 9000 "MinIO"

echo ""
echo "💡 如果有端口未连接，请运行："
echo "ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP"
