"""Caching system for the FastAPI application"""

import json
import hashlib
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CacheManager:
    """Unified cache manager with Redis fallback to in-memory"""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Try to connect to Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory cache")
        else:
            logger.info("Using in-memory cache (Redis not available)")
    
    def _generate_cache_key(self, prefix: str, data: Any) -> str:
        """Generate cache key from data"""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        # Create hash of the data
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                # Try Redis first
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Use memory cache
                if key in self.memory_cache:
                    cache_entry = self.memory_cache[key]
                    # Check if expired
                    if datetime.now() < cache_entry["expires"]:
                        return cache_entry["value"]
                    else:
                        # Remove expired entry
                        del self.memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            ttl = ttl or self.default_ttl
            
            if self.redis_client:
                # Use Redis
                serialized_value = json.dumps(value, default=str)
                await self.redis_client.setex(key, ttl, serialized_value)
                return True
            else:
                # Use memory cache
                self.memory_cache[key] = {
                    "value": value,
                    "expires": datetime.now() + timedelta(seconds=ttl)
                }
                
                # Clean up expired entries periodically
                await self._cleanup_memory_cache()
                return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def _cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        try:
            current_time = datetime.now()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if current_time >= entry["expires"]
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.redis_client:
                info = await self.redis_client.info()
                return {
                    "type": "redis",
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            else:
                # Clean up before getting stats
                await self._cleanup_memory_cache()
                return {
                    "type": "memory",
                    "total_keys": len(self.memory_cache),
                    "memory_usage": "unknown"
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"type": "error", "error": str(e)}


# Global cache manager instance
cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create cache manager instance"""
    global cache_manager
    
    if cache_manager is None:
        # Get Redis URL from settings
        redis_url = None
        try:
            from ..core.settings import get_settings
            settings = get_settings()
            redis_url = settings.redis_url
        except Exception as e:
            logger.warning(f"Failed to get Redis URL from settings: {e}")
        
        cache_manager = CacheManager(redis_url=redis_url)
    
    return cache_manager


# Cache decorators
def cache_result(prefix: str = "result", ttl: int = 3600):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            cache_data = {"args": args, "kwargs": kwargs}
            cache_key = cache._generate_cache_key(prefix, cache_data)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator