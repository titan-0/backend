"""
Celery application configuration
"""
from celery import Celery
from config import RABBITMQ_CONFIG

# Create Celery app
celery_app = Celery(
    'order_processor',
    broker=f"amqp://{RABBITMQ_CONFIG['user']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}/{RABBITMQ_CONFIG['vhost']}",
    backend=None,  # Disable result backend to avoid echo messages
    include=['tasks']  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json', 'msgpack'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Queue configuration
celery_app.conf.task_routes = {
    'tasks.process_order_update': {'queue': 'celery_tasks'},
}
