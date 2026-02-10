#!/usr/bin/env python3
"""检查服务状态脚本

检查：
1. Redis 连接状态
2. Celery worker 状态
3. WebSocket 端点可用性
4. 数据库连接状态
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis
import asyncio
from sqlalchemy import text
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from celery import Celery


def check_redis():
    """检查 Redis 连接"""
    print("\n=== 检查 Redis 连接 ===")
    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        client.ping()
        print(f"✅ Redis 连接成功: {settings.REDIS_URL}")
        
        # 测试发布订阅
        test_channel = "test:channel"
        client.publish(test_channel, "test message")
        print(f"✅ Redis Pub/Sub 测试成功")
        
        client.close()
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


def check_celery():
    """检查 Celery worker 状态"""
    print("\n=== 检查 Celery Worker ===")
    try:
        from app.core.celery_app import celery_app
        
        # 检查活跃的 worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print(f"✅ 发现 {len(active_workers)} 个活跃的 Celery worker:")
            for worker_name, tasks in active_workers.items():
                print(f"   - {worker_name}: {len(tasks)} 个活跃任务")
            return True
        else:
            print("❌ 没有发现活跃的 Celery worker")
            print("   请运行: celery -A app.core.celery_app worker --loglevel=info")
            return False
    except Exception as e:
        print(f"❌ Celery 检查失败: {e}")
        return False


async def check_database():
    """检查数据库连接"""
    print("\n=== 检查数据库连接 ===")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()
            print(f"✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def check_websocket_endpoint():
    """检查 WebSocket 端点配置"""
    print("\n=== 检查 WebSocket 配置 ===")
    try:
        # 检查 WebSocket 路由是否注册
        from app.api.v1.router import api_router
        
        # 查找 WebSocket 路由
        websocket_routes = []
        for route in api_router.routes:
            if hasattr(route, 'path') and '/ws/' in route.path:
                websocket_routes.append(route.path)
        
        if websocket_routes:
            print(f"✅ 发现 {len(websocket_routes)} 个 WebSocket 端点:")
            for path in websocket_routes:
                print(f"   - {path}")
            return True
        else:
            print("❌ 没有发现 WebSocket 端点")
            return False
    except Exception as e:
        print(f"❌ WebSocket 配置检查失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("服务状态检查")
    print("=" * 60)
    
    results = {
        "Redis": check_redis(),
        "Database": asyncio.run(check_database()),
        "Celery": check_celery(),
        "WebSocket": check_websocket_endpoint()
    }
    
    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)
    
    all_ok = True
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service}: {'正常' if status else '异常'}")
        if not status:
            all_ok = False
    
    print("\n" + "=" * 60)
    
    if all_ok:
        print("✅ 所有服务运行正常")
        print("\n建议：")
        print("1. 如果 WebSocket 连接仍然失败，检查前端 WebSocket URL 配置")
        print("2. 确保 Celery worker 已重启以加载最新代码")
        print("3. 检查防火墙是否阻止 WebSocket 连接")
    else:
        print("❌ 部分服务异常，请根据上述提示修复")
        print("\n常见问题：")
        print("- Redis 连接失败：检查 Redis 是否运行，SSH 隧道是否正常")
        print("- Celery worker 未运行：运行 celery -A app.core.celery_app worker --loglevel=info")
        print("- 数据库连接失败：检查数据库配置和连接")
    
    print("=" * 60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
