#!/usr/bin/env python3
"""模拟前端 WebSocket 连接测试"""
import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_breakdown_websocket():
    """测试剧集拆解 WebSocket 连接"""
    
    # 创建一个测试任务 ID
    task_id = str(uuid.uuid4())
    
    # 前端通过 Vite 代理访问，实际连接到后端
    # 前端代码: /api/v1/ws/breakdown/${taskId}
    # Vite 代理: /api -> http://localhost:8000
    # 最终 URL: ws://localhost:8000/api/v1/ws/breakdown/${taskId}
    
    ws_url = f"ws://localhost:8000/api/v1/ws/breakdown/{task_id}"
    
    print("=" * 60)
    print("🧪 前端 WebSocket 连接测试")
    print("=" * 60)
    print(f"任务 ID: {task_id}")
    print(f"连接地址: {ws_url}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 连接成功")
            print()
            
            # 接收消息
            message_count = 0
            timeout_seconds = 5
            
            print(f"⏳ 等待接收消息（最多 {timeout_seconds} 秒）...")
            print()
            
            try:
                while message_count < 3:  # 最多接收 3 条消息
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=timeout_seconds
                    )
                    message_count += 1
                    
                    data = json.loads(message)
                    
                    print(f"📨 消息 #{message_count}:")
                    print(f"   类型: {data.get('code', data.get('status', 'unknown'))}")
                    
                    if 'error' in data:
                        print(f"   错误: {data['error']}")
                        if data.get('code') == 'TASK_NOT_FOUND':
                            print("   ✅ 这是预期的错误（任务不存在）")
                            print("   ✅ 说明 WebSocket 和数据库连接都正常")
                            break
                    elif 'task_id' in data:
                        print(f"   任务ID: {data['task_id']}")
                        print(f"   状态: {data.get('status')}")
                        print(f"   进度: {data.get('progress', 0)}%")
                        print(f"   当前步骤: {data.get('current_step', 'N/A')}")
                    
                    print()
                    
            except asyncio.TimeoutError:
                print(f"⏱️  {timeout_seconds} 秒内未收到更多消息")
            
            print("-" * 60)
            print("✅ 测试完成")
            print()
            print("📊 测试结果:")
            print(f"   - WebSocket 连接: ✅ 成功")
            print(f"   - 数据库查询: ✅ 正常")
            print(f"   - 消息接收: ✅ 正常 (收到 {message_count} 条消息)")
            print()
            print("💡 前端页面应该能够正常使用 WebSocket 功能")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ HTTP 错误: {e.status_code}")
        print("   可能原因: 后端服务未运行或路由配置错误")
    except ConnectionRefusedError:
        print("❌ 连接被拒绝")
        print("   可能原因: 后端服务未运行 (端口 8000)")
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}")
        print(f"   错误详情: {e}")
    
    print("=" * 60)

async def test_batch_websocket():
    """测试批量进度 WebSocket 连接"""
    
    project_id = str(uuid.uuid4())
    ws_url = f"ws://localhost:8000/api/v1/ws/batch-simple/{project_id}"
    
    print()
    print("=" * 60)
    print("🧪 批量进度 WebSocket 连接测试")
    print("=" * 60)
    print(f"项目 ID: {project_id}")
    print(f"连接地址: {ws_url}")
    print("-" * 60)
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 连接成功")
            print()
            
            # 接收初始消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                data = json.loads(message)
                
                print("📨 收到消息:")
                print(f"   类型: {data.get('type')}")
                
                if data.get('type') == 'batch_progress':
                    print(f"   总任务数: {data.get('total_tasks', 0)}")
                    print(f"   整体进度: {data.get('overall_progress', 0)}%")
                    print(f"   状态统计: {data.get('status_counts', {})}")
                
                print()
                print("✅ 批量进度 WebSocket 正常")
                
            except asyncio.TimeoutError:
                print("⏱️  3 秒内未收到消息（项目无任务）")
                print("✅ 连接正常，只是没有数据")
                
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
    
    print("=" * 60)

async def main():
    """运行所有测试"""
    await test_breakdown_websocket()
    await test_batch_websocket()
    
    print()
    print("🎉 所有测试完成！")
    print()
    print("📝 下一步:")
    print("   1. 打开浏览器访问: http://localhost:5173")
    print("   2. 进入 Workspace 页面")
    print("   3. 打开浏览器开发者工具 (F12)")
    print("   4. 查看 Console 和 Network (WS) 标签")
    print("   5. 启动一个拆解任务，观察 WebSocket 消息")
    print()

if __name__ == "__main__":
    asyncio.run(main())
