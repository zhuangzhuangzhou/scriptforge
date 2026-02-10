#!/usr/bin/env python3
"""测试前端 WebSocket 连接"""
import asyncio
import websockets
import json

async def test_websocket():
    """测试 WebSocket 连接"""
    # 测试 URL（模拟前端连接）
    url = "ws://localhost:8000/api/v1/ws/breakdown/test-task-id"

    print(f"正在连接到: {url}")

    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket 连接成功")

            # 等待接收消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"收到消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except asyncio.TimeoutError:
                print("⏱️  5秒内未收到消息（可能任务不存在）")
            except Exception as e:
                print(f"❌ 接收消息失败: {e}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ 连接失败 - HTTP 状态码: {e.status_code}")
    except ConnectionRefusedError:
        print("❌ 连接被拒绝 - 后端服务可能未运行")
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
