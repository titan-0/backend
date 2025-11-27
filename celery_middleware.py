"""
Celery Consumer: RabbitMQ -> Celery Tasks -> Redis -> MySQL Pipeline
Receives messages from RabbitMQ and dispatches them to Celery tasks
"""

import msgpack
import json
import signal
import sys
from datetime import datetime
from typing import Dict, Any

from config import APP_CONFIG, RABBITMQ_CONFIG
from rabbitmq_client import RabbitMQClient
from tasks import process_order_update

# Global shutdown flag
shutdown_requested = False
rabbitmq_client = None


# ------------------------ MESSAGE HANDLERS ------------------------
def handle_order_update(data: Dict[str, Any]) -> None:
    """
    Handle order update events from RabbitMQ by dispatching to Celery task
    """
    order_id = data.get("order_id")
    if not order_id:
        print("⚠️ Missing order_id in message")
        return
    
    print(f"📤 Dispatching order {order_id} to Celery task")
    
    # Send to Celery task asynchronously
    result = process_order_update.apply_async(
        args=[data],
        queue='celery_tasks',  # Send to Celery worker queue
        retry=True,
        retry_policy={
            'max_retries': 3,
            'interval_start': 0,
            'interval_step': 0.2,
            'interval_max': 0.2,
        }
    )
    
    print(f"✅ Task dispatched with ID: {result.id}")


# ------------------------ CALLBACK FUNCTION ------------------------
def callback(ch, method, properties, body):
    """Main callback function for processing RabbitMQ messages"""
    try:
        # Try to unpack msgpack
        try:
            data = msgpack.unpackb(body, raw=False)
        except:
            # Fallback to JSON
            try:
                data = json.loads(body)
            except:
                print("❌ Error unpacking message (not msgpack or JSON)")
                ch.basic_ack(method.delivery_tag)
                return
        
        # Skip if data is not a dict (ignore Celery internal messages)
        if not isinstance(data, dict):
            print(f"ℹ️ Ignoring non-dict message type: {type(data).__name__}")
            ch.basic_ack(method.delivery_tag)
            return
        
        print(f"\n📩 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received message: {data}")
        
        # Route based on message class/type
        message_class = data.get("class") or data.get("type") or data.get("event_type")
        
        if message_class in APP_CONFIG['message_class']:
            handle_order_update(data)
        else:
            print(f"ℹ️ Ignoring message with class: {message_class}")
        
        ch.basic_ack(method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        ch.basic_ack(method.delivery_tag)


# ------------------------ SIGNAL HANDLERS ------------------------
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested, rabbitmq_client
    print(f"\n⚠️ Received signal {signum}. Initiating graceful shutdown...")
    shutdown_requested = True
    
    # Stop consuming
    if rabbitmq_client and rabbitmq_client.channel:
        try:
            rabbitmq_client.channel.stop_consuming()
        except:
            pass


# ------------------------ MAIN ENTRY POINT ------------------------
def main():
    """Main entry point for the Celery consumer"""
    global rabbitmq_client
    
    # Only register signal handlers if running as main thread
    try:
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Kill signal
        print("⚡ Signal handlers registered")
    except ValueError:
        # Running in a thread, signals won't work - that's ok
        print("ℹ️ Running in background thread (signals handled by main process)")
    
    # Initialize RabbitMQ client
    rabbitmq_client = RabbitMQClient()
    
    # Print connection summary
    print(f"🔗 RabbitMQ: {RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}")
    print("📤 Messages will be dispatched to Celery workers")
    
    try:
        # Start consuming messages
        rabbitmq_client.start_consuming(callback)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up connections
        print("🧹 Cleaning up resources...")
        if rabbitmq_client:
            rabbitmq_client.close()
        print("✅ Connections closed. Goodbye!")


if __name__ == "__main__":
    main()
