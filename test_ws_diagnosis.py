#!/usr/bin/env python3
"""
WebSocket 连接诊断脚本
用于测试剧集拆解的 WebSocket 连接是否正常
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_websocket_connection():
    """测试 WebSocket 连接"""

    # 测试配置
    host = "localhost"
    port = 8000
    task_id = "test-task-id"  # 需要替换为实际的 task_id

    ws_url = f"ws://{host}:{port}/api/v1/ws/breakdown/{task_id}"

    print("=" * 60)
    print("WebSocket 连接诊断")
    print("=" * 60)
    print(f"测试 URL: {ws_url}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        print("正在连接 WebSocket...")
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 连接成功！")
            print()

            # 接收消息
            print("等待接收消息...")
            message_count = 0

            while message_count < 5:  # 最多接收 5 条消息
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_count += 1

                    print(f"\n📨 收到消息 #{message_count}:")
                    print("-" * 40)

                    try:
                        data = json.loads(message)
                        print(json.dumps(data, indent=2, ensure_ascii=False))

                        # 检查是否是任务完成消息
                        if data.get("status") == "done":
                            print("\n✅ 任务已完成，断开连接")
                            break

                    except json.JSONDecodeError:
                        print(f"原始消息: {message}")

                except asyncio.TimeoutError:
                    print("\n⏱️  等待超时（5秒内未收到消息）")
                    break

            print("\n" + "=" * 60)
            print("测试完成")
            print("=" * 60)

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ 连接失败: HTTP {e.status_code}")
        print(f"   可能原因: 任务不存在或后端未启动")

    except ConnectionRefusedError:
        print(f"❌ 连接被拒绝")
        print(f"   可能原因: 后端服务未启动或端口错误")

    except Exception as e:
        print(f"❌ 连接错误: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")

if __name__ == "__main__":
    print("\n提示: 请先启动后端服务，并确保有一个正在运行的拆解任务")
    print("如果没有任务，可以先通过前端或 API 启动一个拆解任务\n")

    asyncio.run(test_websocket_connection())
