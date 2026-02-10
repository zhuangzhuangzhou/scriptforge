#!/usr/bin/env python3
"""测试 WebSocket 基本连接"""
import asyncio
import websockets
import json


async def test_ws_basic():
    """测试基本 WebSocket 连接"""
    # 测试一个简单的 WebSocket 端点
    uri = "ws://localhost:8000/api/v1/ws/breakdown/test-task-id"
    
    print(f"🔗 尝试连接: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功！")
            
            # 尝试接收第一条消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                data = json.loads(message)
                print(f"📨 收到消息: {data}")
            except asyncio.TimeoutError:
                print("⏱️  3秒内没有收到消息（这是正常的，因为任务不存在）")
            
            return True
    
    except ConnectionRefusedError:
        print(f"❌ 连接被拒绝")
        print(f"   请确认后端服务器正在运行在 localhost:8000")
        return False
    
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_redis_connection():
    """测试 Redis 连接"""
    print("\n🔍 测试 Redis 连接...")
    
    try:
        import redis.asyncio as redis
        from app.core.config import settings
        
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        print("✅ Redis 连接成功")
        await client.close()
        return True
    
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("WebSocket 连接测试")
    print("=" * 60)
    
    # 测试 Redis
    redis_ok = await test_redis_connection()
    
    # 测试 WebSocket
    print("\n" + "=" * 60)
    print("测试 WebSocket 连接")
    print("=" * 60)
    ws_ok = await test_ws_basic()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"Redis: {'✅ 正常' if redis_ok else '❌ 失败'}")
    print(f"WebSocket: {'✅ 正常' if ws_ok else '❌ 失败'}")
    
    if not redis_ok:
        print("\n⚠️  Redis 不可用会导致 WebSocket 日志推送功能无法工作")
        print("   但 WebSocket 进度推送仍然可以通过数据库轮询工作")


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    asyncio.run(main())
