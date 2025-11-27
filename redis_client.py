"""
Redis client connection and operations
"""
import redis
from typing import Dict, Any, Optional
from config import REDIS_CONFIG


class RedisClient:
    """Redis connection manager"""
    
    def __init__(self):
        self.client = None
        self.connect()
    
    def connect(self):
        """Establish Redis connection"""
        print(f"🔌 Connecting to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}...")
        self.client = redis.Redis(
            host=REDIS_CONFIG['host'],
            port=REDIS_CONFIG['port'],
            db=REDIS_CONFIG['db'],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )
        
        try:
            self.client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    def fetch_data(self, redis_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete data from Redis for a given key.
        Handles both Hash and List data types.
        """
        try:
            key_type = self.client.type(redis_key)
            
            if key_type == "hash":
                return self.client.hgetall(redis_key)
            elif key_type == "list":
                raw_data = self.client.lrange(redis_key, 0, -1)
                if raw_data and len(raw_data) % 2 == 0:
                    return {raw_data[i]: raw_data[i + 1] for i in range(0, len(raw_data), 2)}
            elif key_type == "string":
                import json
                data = self.client.get(redis_key)
                try:
                    return json.loads(data)
                except:
                    return {"value": data}
            else:
                print(f"⚠️ Unsupported Redis key type: {key_type}")
                return None
                
        except Exception as e:
            print(f"❌ Redis fetch failed for {redis_key}: {e}")
            return None
    
    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
