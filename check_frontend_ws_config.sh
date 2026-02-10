#!/bin/bash

echo "🔍 检查前端 WebSocket 配置"
echo "=========================================="
echo ""

# 1. 检查前端服务
echo "1️⃣  前端服务状态:"
if lsof -i:5173 > /dev/null 2>&1; then
    echo "   ✅ 前端服务运行中 (http://localhost:5173)"
else
    echo "   ❌ 前端服务未运行"
    exit 1
fi
echo ""

# 2. 检查后端服务
echo "2️⃣  后端服务状态:"
if lsof -i:8000 > /dev/null 2>&1; then
    echo "   ✅ 后端服务运行中 (http://localhost:8000)"
else
    echo "   ❌ 后端服务未运行"
    exit 1
fi
echo ""

# 3. 检查 Vite 代理配置
echo "3️⃣  Vite 代理配置:"
echo "   文件: frontend/vite.config.ts"
grep -A 5 "proxy:" frontend/vite.config.ts | sed 's/^/   /'
echo ""

# 4. 检查环境变量
echo "4️⃣  环境变量:"
if [ -f "frontend/.env" ]; then
    echo "   文件: frontend/.env"
    cat frontend/.env | sed 's/^/   /'
else
    echo "   ⚠️  未找到 .env 文件"
fi
echo ""

# 5. 检查 WebSocket Hook
echo "5️⃣  WebSocket Hook 配置:"
echo "   文件: frontend/src/hooks/useWebSocket.ts"
echo "   URL 构建逻辑:"
grep -A 3 "const protocol" frontend/src/hooks/useWebSocket.ts | sed 's/^/   /'
echo ""

# 6. 测试 API 连接
echo "6️⃣  测试后端 API:"
response=$(curl -s http://localhost:8000/health)
if [ $? -eq 0 ]; then
    echo "   ✅ 后端健康检查: $response"
else
    echo "   ❌ 后端连接失败"
fi
echo ""

# 7. 检查 WebSocket 路由
echo "7️⃣  WebSocket 路由注册:"
echo "   文件: backend/app/api/v1/router.py"
grep "websocket" backend/app/api/v1/router.py | sed 's/^/   /'
echo ""

echo "=========================================="
echo "✅ 配置检查完成"
echo ""
echo "📝 WebSocket 连接流程:"
echo "   前端: ws://localhost:5173/api/v1/ws/breakdown/{taskId}"
echo "   ↓ (Vite 代理)"
echo "   后端: ws://localhost:8000/api/v1/ws/breakdown/{taskId}"
echo ""
