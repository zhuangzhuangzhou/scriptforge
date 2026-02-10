#!/usr/bin/env python3
"""测试 WebSocket 连接（使用真实 UUID）"""
import asyncio
import websockets
import json
import uuid

async def test_websocket():
    # 使用真实的 UUID 格式
    test_uuid = str(uuid.uuid4())
    url = f"ws://localhost:8000/api/v1/ws/breakdown/{test_uuid}"

    print(f"正在连接到: {url}")
    print(f"测试 UUID: {test_uuid}")

    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket 连接成功")

            # 等待接收消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                data = json.loads(message)
                print(f"收到消息: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # 检查是否是预期的"任务不存在"错误
                if data.get('code') == 'TASK_NOT_FOUND':
                    print("\n✅ WebSocket 功能正常！")
                    print("   (收到预期的'任务不存在'错误，说明数据库查询成功)")
                    
            except asyncio.TimeoutError:
                print("⏱️  3秒内未收到消息")
                
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
