#!/bin/bash

# ==================== 配置区 ====================
SERVER_USER="root"
SERVER_IP="43.129.75.170"
REMOTE_BASE="/mnt"
REMOTE_PROJECT_DIR="$REMOTE_BASE/jim"
LOCAL_PROJECT_DIR="./jim"
# ===============================================

echo "🚀 [1/6] 准备本地代码包..."
# 排除大型依赖目录，只打包源代码
# 注意：Windows 环境下建议在 Git Bash 中运行此脚本
tar -czf jim-deploy.tar.gz \
    --exclude=".git" \
    --exclude="node_modules" \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude="*.log" \
    --exclude=".env.local" \
    -C "$LOCAL_PROJECT_DIR" .

echo "📦 [2/6] 上传代码包到服务器..."
scp jim-deploy.tar.gz $SERVER_USER@$SERVER_IP:$REMOTE_BASE/

echo "📂 [3/6] 解压并清理环境..."
ssh $SERVER_USER@$SERVER_IP "
    mkdir -p $REMOTE_PROJECT_DIR && \
    tar -xzf $REMOTE_BASE/jim-deploy.tar.gz -C $REMOTE_PROJECT_DIR && \
    rm $REMOTE_BASE/jim-deploy.tar.gz && \
    cp $REMOTE_PROJECT_DIR/backend/.env.production $REMOTE_PROJECT_DIR/backend/.env
"
rm jim-deploy.tar.gz  # 清理本地临时包

echo "🔨 [4/6] 智能更新服务 (最小化停机时间)..."
ssh $SERVER_USER@$SERVER_IP "
    cd $REMOTE_PROJECT_DIR && \
    docker compose up -d --build
"

echo "🗄️ [5/6] 数据库迁移 (Alembic)..."
ssh $SERVER_USER@$SERVER_IP "
    sleep 5 && \
    docker exec novel-script-backend alembic upgrade head
"

echo "🌐 [6/6] 刷新宿主机 Nginx 并进行健康检查..."
ssh $SERVER_USER@$SERVER_IP "
    systemctl reload nginx && \
    sleep 5 && \
    echo '' && \
    echo '--- 服务状态检查 ---' && \
    curl -s -o /dev/null -w '前端首页 (80): %{http_code}\n' http://localhost/ && \
    curl -s -o /dev/null -w '后端健康检查 (8000): %{http_code}\n' http://localhost:8000/health && \
    curl -s -o /dev/null -w 'API 代理路径: %{http_code}\n' http://localhost/api/v1/health
"

echo ""
echo "✨ 部署成功完成！"
echo "📱 访问地址: http://$SERVER_IP"
