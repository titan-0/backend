"""
Celery tasks for processing orders
"""
from celery import Task
from celery_app import celery_app
from redis_client import RedisClient
from mysql_client import MySQLClient
from config import APP_CONFIG
from typing import Dict, Any


# Initialize clients (reused across tasks)
redis_client = RedisClient()
mysql_client = MySQLClient()


@celery_app.task(name='tasks.process_order_update', bind=True, max_retries=3)
def process_order_update(self, order_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Celery task to process order updates.
    Fetches data from Redis and stores in MySQL.
    
    Args:
        order_data: Dictionary containing order information with 'order_id'
        
    Returns:
        Dictionary with status and message
    """
    try:
        order_id = order_data.get("order_id")
        if not order_id:
            print(f"❌ Task {self.request.id}: Missing order_id in data: {order_data}")
            return {"status": "error", "message": "Missing order_id"}
        
        # Fetch complete order data from Redis
        redis_key = APP_CONFIG['redis_key_pattern'].format(order_id=order_id)
        print(f"🔍 Task {self.request.id}: Fetching order data from Redis: {redis_key}")
        
        order_dict = redis_client.fetch_data(redis_key)
        
        if not order_dict:
            print(f"⚠️ Task {self.request.id}: No data found in Redis for key: {redis_key}")
            return {"status": "error", "message": f"No data found in Redis for order {order_id}"}
        
        print(f"📦 Task {self.request.id}: Retrieved {len(order_dict)} fields from Redis for order {order_id}")
        print(f"📋 Task {self.request.id}: Data fields: {list(order_dict.keys())}")
        
        # Insert into MySQL directly without sanitization
        table_name = APP_CONFIG['target_table']
        print(f"💾 Task {self.request.id}: Attempting to insert into table '{table_name}'")
        
        if mysql_client.insert_or_update(table_name, order_dict):
            print(f"✅ Task {self.request.id}: Order {order_id} inserted/updated successfully in MySQL")
            return {
                "status": "success",
                "message": f"Order {order_id} processed successfully",
                "order_id": order_id,
                "fields_count": len(order_dict)
            }
        else:
            print(f"❌ Task {self.request.id}: Failed to insert order {order_id} into MySQL")
            raise Exception(f"Failed to insert order {order_id} into MySQL")
            
    except Exception as e:
        print(f"❌ Task {self.request.id}: Error processing order: {e}")
        import traceback
        traceback.print_exc()
        # Retry the task
        raise self.retry(exc=e, countdown=5)  # Retry after 5 seconds


@celery_app.task(name='tasks.health_check')
def health_check() -> Dict[str, str]:
    """Simple health check task"""
    return {"status": "ok", "message": "Celery worker is running"}
