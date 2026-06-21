import time
import json
from functools import wraps
import logging

# Create a logger for the module
logger = logging.getLogger(__name__)

class CacheService:
    """Simple in-memory cache service with expiration"""
    
    def __init__(self, app=None):
        self._cache = {}
        self.app = app
        
    def get(self, key):
        """
        Get a value from the cache
        
        Parameters:
        - key: The cache key
        
        Returns:
        - value: The cached value, or None if not found or expired
        """
        if key in self._cache:
            expiry_time, value = self._cache[key]
            if expiry_time > time.time():
                return value
            else:
                # Remove expired item
                del self._cache[key]
        return None
        
    def set(self, key, value, ttl=300):
        """
        Set a value in the cache with expiration
        
        Parameters:
        - key: The cache key
        - value: The value to cache
        - ttl: Time to live in seconds (default: 5 minutes)
        """
        self._cache[key] = (time.time() + ttl, value)
        
    def delete(self, key):
        """
        Delete a value from the cache
        
        Parameters:
        - key: The cache key
        """
        if key in self._cache:
            del self._cache[key]
            
    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        
    def clean_expired(self):
        """Remove all expired cache entries"""
        now = time.time()
        expired_keys = [key for key, (expiry_time, _) in self._cache.items() if expiry_time <= now]
        for key in expired_keys:
            del self._cache[key]
            if self.app:
                self.app.logger.debug(f"Removed expired cache key: {key}")
            else:
                logger.debug(f"Removed expired cache key: {key}")

# Create a global cache instance
cache = CacheService()

def cached(ttl=300, key_prefix=''):
    """
    Decorator that caches function results
    
    Parameters:
    - ttl: Time to live in seconds (default: 5 minutes)
    - key_prefix: Prefix for the cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name, args, and kwargs
            key_parts = [key_prefix, func.__name__]
            for arg in args:
                if isinstance(arg, (int, float, str, bool, type(None))):
                    key_parts.append(str(arg))
                else:
                    key_parts.append(str(hash(str(arg))))
                    
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (int, float, str, bool, type(None))):
                    key_parts.append(f"{k}={v}")
                else:
                    key_parts.append(f"{k}={hash(str(v))}")
                    
            cache_key = ':'.join(key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
                
            # Call function and cache result
            result = func(*args, **kwargs)
            try:
                # Only cache if result is JSON-serializable
                json.dumps(result)
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached: {cache_key} (TTL: {ttl}s)")
            except (TypeError, OverflowError):
                logger.debug(f"Could not cache {cache_key}: result not serializable")
                
            return result
        return wrapper
    return decorator 