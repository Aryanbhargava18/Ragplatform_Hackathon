import os
import redis
import json
import time

# Redis connection details
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

# Redis client instance
_redis_client = None

def get_redis_client():
    """
    Get a Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test the connection
            _redis_client.ping()
            print("Redis connection established successfully")
        except redis.ConnectionError as e:
            print(f"Redis connection error: {str(e)}")
            # Return a mock Redis client that doesn't do anything
            _redis_client = MockRedisClient()
        except Exception as e:
            print(f"Error initializing Redis client: {str(e)}")
            # Return a mock Redis client that doesn't do anything
            _redis_client = MockRedisClient()
    
    return _redis_client

def get_cached_result(key, default=None):
    """
    Get a cached result from Redis
    """
    client = get_redis_client()
    
    try:
        result = client.get(key)
        return result if result is not None else default
    except Exception as e:
        print(f"Error getting cached result: {str(e)}")
        return default

def cache_result(key, value, ttl=300):
    """
    Cache a result in Redis with TTL
    """
    client = get_redis_client()
    
    try:
        client.set(key, value, ex=ttl)
        return True
    except Exception as e:
        print(f"Error caching result: {str(e)}")
        return False

class MockRedisClient:
    """
    Mock Redis client for when Redis is not available
    """
    def __init__(self):
        self.cache = {}
        self.expiry = {}
    
    def ping(self):
        return True
    
    def get(self, key):
        # Check if key exists and has not expired
        if key in self.cache and (key not in self.expiry or self.expiry[key] > time.time()):
            return self.cache[key]
        return None
    
    def set(self, key, value, ex=None):
        self.cache[key] = value
        if ex is not None:
            self.expiry[key] = time.time() + ex
        return True
    
    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
        if key in self.expiry:
            del self.expiry[key]
        return True
