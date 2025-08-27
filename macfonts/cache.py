import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable
from functools import wraps
from .logging_config import logger

T = TypeVar('T')

class MemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry['expires_at']:
                    logger.debug(f"Cache hit for key: {key}")
                    return entry['value']
                else:
                    logger.debug(f"Cache expired for key: {key}")
                    del self._cache[key]
            
            logger.debug(f"Cache miss for key: {key}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            logger.debug(f"Cached value for key: {key}, expires in {ttl}s")
    
    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")
    
    async def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if current_time >= entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
cache = MemoryCache()

def cached(ttl: int = 300, key_func: Optional[Callable[..., str]] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

async def start_cache_cleanup_task():
    """Start background task to cleanup expired cache entries."""
    async def cleanup_loop():
        while True:
            try:
                await cache.cleanup_expired()
                await asyncio.sleep(60)  # Cleanup every minute
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    asyncio.create_task(cleanup_loop())
    logger.info("Cache cleanup task started")