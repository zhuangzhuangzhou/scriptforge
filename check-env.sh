#!/bin/bash

# 环境检查脚本

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔍 检查开发环境..."
echo ""

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}✗ Python 未安装${NC}"
fi

# 检查 Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js: ${NODE_VERSION}${NC}"
else
    echo -e "${RED}✗ Node.js 未安装${NC}"
fi

# 检查 npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓ npm: ${NPM_VERSION}${NC}"
else
    echo -e "${RED}✗ npm 未安装${NC}"
fi

echo ""
echo "📦 检查项目依赖..."
echo ""

# 检查后端虚拟环境
if [ -d "backend/venv" ]; then
    echo -e "${GREEN}✓ 后端虚拟环境已创建${NC}"
else
    echo -e "${YELLOW}⚠ 后端虚拟环境未创建${NC}"
fi

# 检查前端依赖
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓ 前端依赖已安装${NC}"
else
    echo -e "${YELLOW}⚠ 前端依赖未安装${NC}"
fi

echo ""
echo "🔌 检查服务连接..."
echo ""

# 检查 SSH 隧道
if lsof -i:5433 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL 隧道 (5433) 已建立${NC}"
else
    echo -e "${RED}✗ PostgreSQL 隧道 (5433) 未建立${NC}"
fi

if lsof -i:6380 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis 隧道 (6380) 已建立${NC}"
else
    echo -e "${RED}✗ Redis 隧道 (6380) 未建立${NC}"
fi

if lsof -i:9000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MinIO 隧道 (9000) 已建立${NC}"
else
    echo -e "${RED}✗ MinIO 隧道 (9000) 未建立${NC}"
fi

echo ""
echo "🚪 检查端口占用..."
echo ""

# 检查端口占用
if lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ 端口 8000 (后端) 已被占用${NC}"
else
    echo -e "${GREEN}✓ 端口 8000 (后端) 可用${NC}"
fi

if lsof -i:5173 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ 端口 5173 (前端) 已被占用${NC}"
else
    echo -e "${GREEN}✓ 端口 5173 (前端) 可用${NC}"
fi

echo ""
