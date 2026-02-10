#!/usr/bin/env python3
"""测试 WebSocket 连接"""
import asyncio
import websockets
import json


async def test_websocket():
    """测试 WebSocket 连接"""
    # 找一个正在运行的任务
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app.core.database import SyncSessionLocal
    from app.models.ai_task import AITask
    
    db = SyncSessionLocal()
    task = db.query(AITask).filter(
        AITask.status == "running"
    ).first()
    
    if not task:
        print("❌ 没有找到正在运行的任务")
        db.close()
        return
    
    task_id = str(task.id)
    print(f"✅ 找到任务: {task_id}")
    print(f"   状态: {task.status}")
    print(f"   进度: {task.progress}%")
    db.close()
    
    # 测试 WebSocket 连接
    uri = f"ws://localhost:8000/api/v1/ws/breakdown-logs/{task_id}"
    print(f"\n🔗 连接到: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功！")
            
            # 接收消息
            count = 0
            while count < 10:  # 只接收前10条消息
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"\n📨 收到消息 #{count + 1}:")
                    print(f"   类型: {data.get('type')}")
                    if data.get('type') == 'stream_chunk':
                        print(f"   内容: {data.get('content', '')[:50]}...")
                    elif data.get('type') == 'progress':
                        print(f"   进度: {data.get('progress')}%")
                    elif data.get('type') == 'error':
                        print(f"   错误: {data.get('content')}")
                    
                    count += 1
                    
                    # 如果任务完成，退出
                    if data.get('type') in ['task_complete', 'task_failed']:
                        print("\n✅ 任务已完成")
                        break
                
                except asyncio.TimeoutError:
                    print("\n⏱️  等待消息超时（5秒）")
                    break
            
            print(f"\n✅ 测试完成，共接收 {count} 条消息")
    
    except Exception as e:
        print(f"\n❌ WebSocket 连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_websocket())
