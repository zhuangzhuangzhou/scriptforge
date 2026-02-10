#!/usr/bin/env python3
"""
WebSocket 连接测试脚本
直接测试后端 WebSocket 端点
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """测试 WebSocket 连接"""

    # 使用一个测试 task_id
    task_id = "test-task-id-12345"

    # 直接连接到后端（不通过 Vite 代理）
    ws_url = f"ws://localhost:8000/api/v1/ws/breakdown/{task_id}"

    print("=" * 60)
    print("WebSocket 连接测试")
    print("=" * 60)
    print(f"测试 URL: {ws_url}")
    print()

    try:
        print("正在连接...")
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 连接成功！")
            print()

            # 等待接收消息
            print("等待接收消息（最多 5 秒）...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"\n📨 收到消息:")
                print("-" * 40)

                try:
                    data = json.loads(message)
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(f"原始消息: {message}")

            except asyncio.TimeoutError:
                print("\n⏱️  5秒内未收到消息（这是正常的，因为任务不存在）")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ 连接失败: HTTP {e.status_code}")
        if e.status_code == 404:
            print("   原因: WebSocket 端点不存在")
            print("   检查: 后端路由是否正确注册")
        elif e.status_code == 500:
            print("   原因: 后端内部错误")
            print("   检查: 后端日志")

    except ConnectionRefusedError:
        print(f"❌ 连接被拒绝")
        print(f"   原因: 后端服务未启动")
        print(f"   解决: 启动后端服务")

    except Exception as e:
        print(f"❌ 连接错误: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

async def test_logs_websocket():
    """测试流式日志 WebSocket 连接"""

    task_id = "test-task-id-12345"
    ws_url = f"ws://localhost:8000/api/v1/ws/breakdown-logs/{task_id}"

    print("\n" + "=" * 60)
    print("流式日志 WebSocket 测试")
    print("=" * 60)
    print(f"测试 URL: {ws_url}")
    print()

    try:
        print("正在连接...")
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 连接成功！")
            print()

            # 等待接收消息
            print("等待接收消息（最多 5 秒）...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"\n📨 收到消息:")
                print("-" * 40)

                try:
                    data = json.loads(message)
                    print(json.dumps(data, indent=2, ensure_ascii=False))

                    # 检查是否是 Redis 不可用的错误
                    if data.get("type") == "error" and data.get("code") == "REDIS_UNAVAILABLE":
                        print("\n⚠️  Redis 服务不可用")
                        print("   解决: 启动 Redis 服务")
                        print("   命令: redis-server")

                except json.JSONDecodeError:
                    print(f"原始消息: {message}")

            except asyncio.TimeoutError:
                print("\n⏱️  5秒内未收到消息")

    except Exception as e:
        print(f"❌ 连接错误: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    print("\n提示: 请确保后端服务运行在 http://localhost:8000\n")

    # 测试任务状态 WebSocket
    asyncio.run(test_websocket())

    # 测试流式日志 WebSocket
    asyncio.run(test_logs_websocket())

    print("\n如果两个测试都成功，说明后端 WebSocket 端点正常")
    print("如果前端仍然连接失败，问题可能在 Vite 代理配置\n")
