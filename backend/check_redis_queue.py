#!/usr/bin/env python3
"""检查 Redis 队列状态"""
import redis

# 连接到 Redis
r = redis.Redis(host='127.0.0.1', port=6380, db=0, decode_responses=True)

# 检查队列长度
queue_length = r.llen('celery')
print(f"📊 Celery 队列中的任务数: {queue_length}")

if queue_length > 0:
    print("\n📋 队列中的任务:")
    # 查看前 5 个任务
    tasks = r.lrange('celery', 0, 4)
    for i, task in enumerate(tasks, 1):
        print(f"\n任务 {i}:")
        print(task[:200] + "..." if len(task) > 200 else task)
else:
    print("\n✅ 队列为空")

# 检查是否有 worker 连接
print(f"\n🔌 活跃的 worker 数: {len(r.smembers('_kombu.binding.celery'))}")
