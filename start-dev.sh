#!/bin/bash

# 小说改编剧本系统 - 开发环境启动脚本

echo "🚀 启动小说改编剧本系统..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 SSH 隧道是否已建立
check_ssh_tunnel() {
    echo -e "${YELLOW}检查 SSH 隧道...${NC}"
    if lsof -i:5433 > /dev/null 2>&1 && lsof -i:6380 > /dev/null 2>&1 && lsof -i:9000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ SSH 隧道已建立${NC}"
        return 0
    else
        echo -e "${RED}✗ SSH 隧道未建立${NC}"
        echo -e "${YELLOW}请先运行以下命令建立 SSH 隧道：${NC}"
        echo "ssh -o ServerAliveInterval=60 -L 5433:127.0.0.1:35432 -L 6380:127.0.0.1:6379 -L 9000:127.0.0.1:19000 root@REMOVED_IP"
        return 1
    fi
}

# 启动后端服务
start_backend() {
    echo -e "${YELLOW}启动后端服务...${NC}"
    cd backend
    
    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        echo -e "${RED}✗ 虚拟环境不存在，正在创建...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # 杀掉已存在的进程
    lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
    
    # 启动 FastAPI
    echo -e "${GREEN}✓ 启动 FastAPI (http://localhost:8000)${NC}"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    
    cd ..
}

# 启动 Celery Worker
start_celery() {
    echo -e "${YELLOW}启动 Celery Worker...${NC}"
    cd backend
    source venv/bin/activate
    
    # 杀掉已存在的 Celery 进程
    pkill -f "celery.*worker" 2>/dev/null || true
    
    celery -A app.core.celery_app worker --loglevel=info > ../celery.log 2>&1 &
    echo -e "${GREEN}✓ Celery Worker 已启动${NC}"
    
    cd ..
}

# 启动前端服务
start_frontend() {
    echo -e "${YELLOW}启动前端服务...${NC}"
    cd frontend
    
    # 检查依赖
    if [ ! -d "node_modules" ]; then
        echo -e "${RED}✗ 依赖未安装，正在安装...${NC}"
        npm install
    fi
    
    echo -e "${GREEN}✓ 启动 Vite (http://localhost:5173)${NC}"
    npm run dev > ../frontend.log 2>&1 &
    
    cd ..
}

# 主流程
main() {
    # 检查 SSH 隧道
    if ! check_ssh_tunnel; then
        exit 1
    fi
    
    # 启动服务
    start_backend
    sleep 3
    start_celery
    sleep 2
    start_frontend
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 所有服务已启动！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "前端地址: ${YELLOW}http://localhost:5173${NC}"
    echo -e "后端地址: ${YELLOW}http://localhost:8000${NC}"
    echo -e "API 文档: ${YELLOW}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "日志文件:"
    echo -e "  - backend.log (后端日志)"
    echo -e "  - celery.log (Celery 日志)"
    echo -e "  - frontend.log (前端日志)"
    echo ""
    echo -e "停止服务: ${YELLOW}./stop-dev.sh${NC}"
    echo ""
}

main
