# modules/utils/cache.py
"""
Provides async caching with TTL using aiocache.
Usage:
    from modules.utils.cache import cache
    
    @cache(ttl=300) # Cache for 300 seconds (5 minutes)
    async def expensive_async_function(param1, param2):
        # ... function logic ...
        return result

To use Redis as a backend (ensure redis server is running and `pip install aiocache[redis]`):
1. Set environment variables for Redis connection if needed by your Redis setup.
2. In the code where aiocache is configured (e.g., early in your application startup or here):
   from aiocache import caches, Cache
   from aiocache.serializers import PickleSerializer
   
   # Example of setting up Redis cache configuration programmatically
   # This should be done ONCE at application startup.
   # caches.set_config({
   #     'default': { # This is the alias used by @cache if no alias specified
   #         'cache': "aiocache.RedisCache",
   #         'endpoint': "localhost", # Or your Redis host
   #         'port': 6379,           # Or your Redis port
   #         # 'password': "your_redis_password", # Optional
   #         # 'db': 0, # Optional Redis DB number
   #         'serializer': {
   #             'class': "aiocache.serializers.PickleSerializer"
   #         },
   #         'plugins': [ # Optional plugins
   #             {'class': "aiocache.plugins.HitMissRatioPlugin"},
   #             {'class': "aiocache.plugins.TimingPlugin"}
   #         ],
   #         'namespace': "genesis_main_cache" # Important for key separation
   #     },
   #     # You can define other cache aliases here if needed
   #     # 'another_cache': { ... }
   # })
   # logger.info("aiocache configured to use Redis as default.")

This file provides a lambda for memory cache by default using the 'default' alias.
To switch to Redis, configure the 'default' alias for aiocache globally at application startup.
"""

from aiocache import cached, Cache
from aiocache.serializers import PickleSerializer
from typing import Callable, Any
from core.logger import logger

def cache(ttl: int) -> Callable[..., Any]:
    """
    Async caching decorator with a specified Time-To-Live (TTL) in seconds.

    This uses the 'default' cache alias managed by aiocache. By default, this
    is an in-memory cache. It can be configured to use Redis or another backend
    at application startup by using `aiocache.caches.set_config`.

    Args:
        ttl: The number of seconds the cache entry should live.

    Returns:
        A decorator that can be applied to an async function.
    """
    return cached(ttl=ttl, alias="default")

logger.info(f"Async caching (aiocache) decorator initialized. It will use the 'default' aiocache alias.")

# To clear a specific cache (if using alias and multiple caches):
# from aiocache import caches
# async def clear_my_cache():
#     await caches.get("default").clear() # Clears the 'default' alias cache

# Note: `modules/stock_analyzer/cache.py` is now removed as this global cache replaces it.
