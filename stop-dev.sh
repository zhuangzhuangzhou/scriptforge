#!/bin/bash

# 小说改编剧本系统 - 停止开发环境脚本

echo "🛑 停止小说改编剧本系统..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 停止后端服务
echo -e "${YELLOW}停止后端服务 (端口 8000)...${NC}"
lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ 后端服务已停止${NC}"

# 停止 Celery Worker
echo -e "${YELLOW}停止 Celery Worker...${NC}"
pkill -f "celery.*worker" 2>/dev/null || true
echo -e "${GREEN}✓ Celery Worker 已停止${NC}"

# 停止前端服务
echo -e "${YELLOW}停止前端服务 (端口 5173)...${NC}"
lsof -t -i:5173 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ 前端服务已停止${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ 所有服务已停止！${NC}"
echo -e "${GREEN}========================================${NC}"
