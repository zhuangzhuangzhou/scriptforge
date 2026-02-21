from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "novel_script",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.breakdown_tasks', 'app.tasks.task_monitor']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_sender='always',
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # 任务超时配置
    task_time_limit=1800,       # 硬超时：30分钟后强制终止
    task_soft_time_limit=1500,  # 软超时：25分钟后发出超时信号

    # Worker 过期检测
    worker_disable_rate_limits=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 定时任务配置
    beat_schedule={
        'monitor-stuck-tasks': {
            'task': 'monitor_and_terminate_stuck_tasks',
            'schedule': 300.0,  # 每 5 分钟执行一次
        },
    },
)
