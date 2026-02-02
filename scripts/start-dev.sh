#!/bin/bash

echo "=== 启动小说改编剧本系统开发环境 ==="

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker 未运行，请先启动 Docker"
    exit 1
fi

# 启动 Docker 服务
echo "1. 启动 Docker 服务 (PostgreSQL, Redis, MinIO)..."
docker-compose up -d

# 等待服务启动
echo "2. 等待服务启动..."
sleep 5

# 检查服务状态
echo "3. 检查服务状态..."
docker-compose ps

echo ""
echo "=== Docker 服务已启动 ==="
echo "PostgreSQL: localhost:5432"
echo "Redis: localhost:6379"
echo "MinIO: localhost:9000 (Console: localhost:9001)"
echo ""
echo "请按照以下步骤启动后端和前端："
echo ""
echo "后端启动："
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "前端启动："
echo "  cd frontend"
echo "  npm run dev"
