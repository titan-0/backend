"""
Configuration settings for Celery Middleware
All connection parameters for RabbitMQ, Redis, and MySQL
"""
import os

# ------------------------ REDIS CONFIGURATION ------------------------
REDIS_CONFIG = {
    'host': os.getenv("REDIS_HOST", "127.0.0.1"),
    'port': int(os.getenv("REDIS_PORT", "6379")),
    'db': int(os.getenv("REDIS_DB", "0")),
}

# ------------------------ MYSQL CONFIGURATION ------------------------
MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "127.0.0.1"),
    'port': int(os.getenv("MYSQL_PORT", "3306")),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", "Deccan115"),
    'database': os.getenv("MYSQL_DATABASE", "tradingdatabase"),
}

# ------------------------ RABBITMQ CONFIGURATION ------------------------
RABBITMQ_CONFIG = {
    'host': os.getenv("RABBITMQ_HOST", "127.0.0.1"),
    'port': int(os.getenv("RABBITMQ_PORT", "5672")),
    'user': os.getenv("RABBITMQ_USER", "guest"),
    'password': os.getenv("RABBITMQ_PASSWORD", "guest"),
    'vhost': os.getenv("RABBITMQ_VHOST", "/"),
}

# ------------------------ CELERY CONFIGURATION ------------------------
CELERY_CONFIG = {
    'queue_name': 'incoming_orders',  # Consumer listens to this
    'task_queue_name': 'celery_tasks',  # Celery worker listens to this
    'exchange_direct': 'amq.direct',
    'exchange_cpp': 'cpp_oms_service',
    'routing_key': 'celery_task',
    'prefetch_count': 1,
    'heartbeat': 600,
    'blocked_connection_timeout': 300,
}

# ------------------------ APPLICATION SETTINGS ------------------------
APP_CONFIG = {
    'redis_key_pattern': 'KANHOJI_INTERNALORDER:{order_id}',
    'target_table': 'internalorder',
    'message_class': ['CeleryEvent_order_update', 'order_update'],
}
