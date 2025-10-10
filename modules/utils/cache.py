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
from core.logger import logger

# The decorator function.
# It uses the 'default' cache alias which aiocache manages.
# By default, if not configured, aiocache's 'default' is SimpleMemoryCache.
# If you call `caches.set_config` as shown in the docstring example above
# before this module is imported or before the first @cache is applied,
# it will use that configuration (e.g., Redis).
cache = lambda ttl: cached(
    ttl=ttl,
    # cache=Cache.MEMORY, # Explicitly Memory if you don't want to rely on global default
    # serializer=PickleSerializer(), # Default is already PickleSerializer
    alias="default", # Uses the 'default' cache configuration from aiocache
    # namespace="genesis_cache", # Namespace is good if 'default' Redis is shared
)

logger.info(f"Async caching (aiocache) decorator initialized. It will use the 'default' aiocache alias.")

# To clear a specific cache (if using alias and multiple caches):
# from aiocache import caches
# async def clear_my_cache():
#     await caches.get("default").clear() # Clears the 'default' alias cache

# Note: `modules/stock_analyzer/cache.py` is now removed as this global cache replaces it.
