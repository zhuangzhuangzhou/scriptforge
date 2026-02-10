#!/bin/bash

# 小说改编剧本系统 - 服务启动脚本（前台显示）

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🚀 启动小说改编剧本系统..."
echo ""

# 检查 SSH 隧道
echo -e "${YELLOW}[1/4] 检查 SSH 隧道...${NC}"
if lsof -i:5433 > /dev/null 2>&1 && lsof -i:6380 > /dev/null 2>&1 && lsof -i:9000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH 隧道已建立${NC}"
else
    echo -e "${RED}✗ SSH 隧道未建立，请先运行：${NC}"
    echo "ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP"
    exit 1
fi
echo ""

# 启动后端
echo -e "${YELLOW}[2/4] 启动后端服务...${NC}"
cd backend
source venv/bin/activate

# 清理旧进程
lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
sleep 1

# 启动 FastAPI
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端启动
sleep 3
if lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
    echo -e "  地址: http://localhost:8000"
    echo -e "  文档: http://localhost:8000/docs"
else
    echo -e "${RED}✗ 后端服务启动失败，请查看 backend.log${NC}"
    cd ..
    exit 1
fi
cd ..
echo ""

# 启动 Celery
echo -e "${YELLOW}[3/4] 启动 Celery Worker...${NC}"
cd backend
source venv/bin/activate

# 清理旧进程
pkill -f "celery.*worker" 2>/dev/null || true
sleep 1

nohup celery -A app.core.celery_app worker --loglevel=info > ../celery.log 2>&1 &
CELERY_PID=$!
sleep 2

echo -e "${GREEN}✓ Celery Worker 已启动 (PID: $CELERY_PID)${NC}"
cd ..
echo ""

# 启动前端
echo -e "${YELLOW}[4/4] 启动前端服务...${NC}"
cd frontend

# 清理旧进程
lsof -t -i:5173 | xargs kill -9 2>/dev/null || true
sleep 1

nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端启动
sleep 3
if lsof -i:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
    echo -e "  地址: http://localhost:5173"
else
    echo -e "${RED}✗ 前端服务启动失败，请查看 frontend.log${NC}"
    cd ..
    exit 1
fi
cd ..
echo ""

# 显示总结
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有服务已成功启动！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📱 访问地址:"
echo -e "  前端: ${YELLOW}http://localhost:5173${NC}"
echo -e "  后端: ${YELLOW}http://localhost:8000${NC}"
echo -e "  API 文档: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "📋 进程 ID:"
echo -e "  后端: $BACKEND_PID"
echo -e "  Celery: $CELERY_PID"
echo -e "  前端: $FRONTEND_PID"
echo ""
echo -e "📝 日志文件:"
echo -e "  tail -f backend.log   # 查看后端日志"
echo -e "  tail -f celery.log    # 查看 Celery 日志"
echo -e "  tail -f frontend.log  # 查看前端日志"
echo ""
echo -e "🛑 停止服务:"
echo -e "  ./stop-dev.sh"
echo ""
