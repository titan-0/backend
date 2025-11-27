"""
RabbitMQ client connection and consumer setup
"""
import pika
import uuid
from config import RABBITMQ_CONFIG, CELERY_CONFIG


class RabbitMQClient:
    """RabbitMQ connection manager"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()
    
    def connect(self):
        """Establish RabbitMQ connection and setup queue"""
        print(f"🔌 Connecting to RabbitMQ at {RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}...")
        
        credentials = pika.PlainCredentials(
            RABBITMQ_CONFIG['user'],
            RABBITMQ_CONFIG['password']
        )
        
        connection_name = f"celery_middleware_{str(uuid.uuid1())[:8]}"
        client_properties = {'connection_name': connection_name}
        
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_CONFIG['host'],
            port=RABBITMQ_CONFIG['port'],
            virtual_host=RABBITMQ_CONFIG['vhost'],
            credentials=credentials,
            connection_attempts=3,
            client_properties=client_properties,
            heartbeat=CELERY_CONFIG['heartbeat'],
            blocked_connection_timeout=CELERY_CONFIG['blocked_connection_timeout']
        )
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        # Declare exchanges and queue
        self.channel.exchange_declare(
            exchange=CELERY_CONFIG['exchange_direct'],
            exchange_type='direct',
            durable=True
        )
        self.channel.exchange_declare(
            exchange=CELERY_CONFIG['exchange_cpp'],
            exchange_type='direct',
            durable=False
        )
        self.channel.queue_declare(
            queue=CELERY_CONFIG['queue_name'],
            durable=True
        )
        self.channel.queue_bind(
            exchange=CELERY_CONFIG['exchange_direct'],
            queue=CELERY_CONFIG['queue_name'],
            routing_key=CELERY_CONFIG['routing_key']
        )
        self.channel.queue_bind(
            exchange=CELERY_CONFIG['exchange_cpp'],
            queue=CELERY_CONFIG['queue_name'],
            routing_key=CELERY_CONFIG['routing_key']
        )
        
        print("✅ RabbitMQ connection established")
    
    def start_consuming(self, callback):
        """Start consuming messages from the queue"""
        self.channel.basic_qos(prefetch_count=CELERY_CONFIG['prefetch_count'])
        self.channel.basic_consume(
            queue=CELERY_CONFIG['queue_name'],
            on_message_callback=callback
        )
        
        print("\n" + "="*60)
        print("🚀 Celery Middleware Started")
        print(f"📡 Listening on queue: {CELERY_CONFIG['queue_name']}")
        print(f"🔗 RabbitMQ: {RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}")
        print("="*60)
        print("\nPress CTRL+C to stop...\n")
        
        self.channel.start_consuming()
    
    def close(self):
        """Close RabbitMQ connection"""
        if self.connection:
            self.connection.close()
