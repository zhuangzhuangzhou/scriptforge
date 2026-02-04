# jim/backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# [新增] 替换为阿里云镜像源 (解决 apt-get 卡顿问题)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖 (python-magic 需要 libmagic1)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
# [新增] 使用清华源/阿里源加速 pip 安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制源代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app

# 启动命令：先尝试数据库迁移，再启动服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]