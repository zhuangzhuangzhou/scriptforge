#!/usr/bin/env python3
"""检查 Redis 中的任务"""
import redis
import json

# 连接到 Redis
r = redis.Redis(host='127.0.0.1', port=6380, db=0, decode_responses=True)

# 检查队列
queue_length = r.llen('celery')
print(f"📊 Celery 队列长度: {queue_length}")

if queue_length > 0:
    print(f"\n📋 队列中的任务:")
    tasks = r.lrange('celery', 0, -1)  # 获取所有任务
    
    target_celery_id = "ec1dd5f5-b9ea-4e1c-929d-61a6ca77ae50"
    found = False
    
    for i, task_str in enumerate(tasks, 1):
        try:
            task_data = json.loads(task_str)
            task_id = task_data.get('headers', {}).get('id', 'unknown')
            
            if task_id == target_celery_id:
                print(f"\n✅ 找到目标任务 (位置 {i}):")
                print(f"   Celery Task ID: {task_id}")
                print(f"   任务名称: {task_data.get('headers', {}).get('task', 'unknown')}")
                print(f"   参数: {task_data.get('headers', {}).get('argsrepr', 'unknown')}")
                found = True
            
            if i <= 5:  # 只显示前5个
                print(f"\n任务 {i}:")
                print(f"   Celery Task ID: {task_id}")
                print(f"   任务名称: {task_data.get('headers', {}).get('task', 'unknown')}")
        except:
            print(f"\n任务 {i}: (无法解析)")
    
    if not found:
        print(f"\n❌ 目标任务不在队列中")
        print(f"   这意味着任务已经被处理过，但状态没有正确更新")
else:
    print(f"\n✅ 队列为空")
    print(f"   目标任务不在队列中，可能已经被处理过")

# 检查 Celery 结果
print(f"\n🔍 检查任务结果:")
result_key = f"celery-task-meta-ec1dd5f5-b9ea-4e1c-929d-61a6ca77ae50"
result = r.get(result_key)
if result:
    print(f"   找到结果: {result[:200]}")
else:
    print(f"   ❌ 没有找到结果")
