"""Cache manager for AI model responses with LRU and Redis support."""

import hashlib
import json
import logging
from functools import lru_cache
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not available. Install with: pip install redis")


class CacheManager:
    """
    Manages caching for AI model responses.

    Supports two backends:
    - memory: In-memory LRU cache (default, no dependencies)
    - redis: Redis cache (requires redis package)

    Features:
    - Automatic cache key generation from signal text
    - TTL support for cache expiration
    - Cache hit/miss metrics
    - Graceful fallback to memory if Redis unavailable
    """

    def __init__(
        self,
        backend: str = "memory",
        redis_url: Optional[str] = None,
        max_size: int = 1000,
        ttl_seconds: int = 2592000,  # 30 days
    ):
        """
        Initialize cache manager.

        Args:
            backend: "memory" or "redis"
            redis_url: Redis connection URL (required for redis backend)
            max_size: Maximum cache entries for LRU (memory backend)
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.backend = backend
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.redis_url = redis_url

        # Metrics
        self.hits = 0
        self.misses = 0

        # In-memory cache (dict for LRU cache simulation)
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

        # Redis client
        self.redis_client: Optional[aioredis.Redis] = None

        # Initialize backend
        if backend == "redis":
            if not REDIS_AVAILABLE:
                logger.warning("Redis backend requested but redis package not installed. Falling back to memory cache.")
                self.backend = "memory"
            elif not redis_url:
                logger.warning("Redis backend requested but no redis_url provided. Falling back to memory cache.")
                self.backend = "memory"

        logger.info(f"CacheManager initialized with backend={self.backend}, max_size={max_size}, ttl={ttl_seconds}s")

    def get_sync(
        self,
        signal_text: str,
        icp_context: Optional[str] = None,
        model: str = "1b"
    ) -> Optional[Dict[str, Any]]:
        """
        Synchronous retrieval from cache (Memory backend only).
        If using Redis backend, this returns None to avoid blocking async calls.
        """
        if self.backend != "memory":
            return None

        cache_key = self._generate_cache_key(signal_text, icp_context, model)
        
        try:
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if datetime.now() < entry["expires_at"]:
                    self.hits += 1
                    logger.debug(f"Cache HIT (Memory Sync): {cache_key[:16]}...")
                    return entry["value"]
                else:
                    del self._memory_cache[cache_key]
                    self.misses += 1
                    return None
            else:
                self.misses += 1
                return None
        except Exception as e:
            logger.error(f"Cache GET SYNC error: {e}")
            return None

    def set_sync(
        self,
        signal_text: str,
        value: Dict[str, Any],
        icp_context: Optional[str] = None,
        model: str = "1b",
        ttl: Optional[int] = None
    ):
        """
        Synchronous storage in cache (Memory backend only).
        """
        if self.backend != "memory":
            return

        cache_key = self._generate_cache_key(signal_text, icp_context, model)
        ttl = ttl or self.ttl_seconds

        try:
            if len(self._memory_cache) >= self.max_size:
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]

            self._memory_cache[cache_key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl)
            }
            logger.debug(f"Cache SET (Memory Sync): {cache_key[:16]}...")
        except Exception as e:
            logger.error(f"Cache SET SYNC error: {e}")

    async def connect_redis(self):
        """Connect to Redis (call during app startup)."""
        if self.backend == "redis" and REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self.redis_client.ping()
                logger.info(f"Successfully connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}. Falling back to memory cache.")
                self.backend = "memory"
                self.redis_client = None

    async def disconnect_redis(self):
        """Disconnect from Redis (call during app shutdown)."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    def _generate_cache_key(self, signal_text: str, icp_context: Optional[str] = None, model: str = "") -> str:
        """
        Generate deterministic cache key from signal text and context.

        Args:
            signal_text: The signal text to classify
            icp_context: Optional ICP context
            model: Model identifier (e.g., "1b", "4b")

        Returns:
            SHA256 hash of the inputs as cache key
        """
        # Normalize inputs
        normalized_signal = signal_text.strip().lower()
        normalized_icp = (icp_context or "").strip().lower()

        # Create deterministic key
        key_parts = [normalized_signal, normalized_icp, model]
        key_string = "|".join(key_parts)

        # Hash to fixed-length key
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()
        return f"model_cache:{cache_key}"

    async def get(
        self,
        signal_text: str,
        icp_context: Optional[str] = None,
        model: str = "1b"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response.

        Args:
            signal_text: The signal text
            icp_context: Optional ICP context
            model: Model identifier

        Returns:
            Cached response dict or None if not found/expired
        """
        cache_key = self._generate_cache_key(signal_text, icp_context, model)

        try:
            if self.backend == "redis" and self.redis_client:
                # Redis backend
                cached_value = await self.redis_client.get(cache_key)
                if cached_value:
                    self.hits += 1
                    logger.debug(f"Cache HIT (Redis): {cache_key[:16]}...")
                    return json.loads(cached_value)
                else:
                    self.misses += 1
                    logger.debug(f"Cache MISS (Redis): {cache_key[:16]}...")
                    return None
            else:
                # Memory backend
                if cache_key in self._memory_cache:
                    entry = self._memory_cache[cache_key]
                    # Check expiration
                    if datetime.now() < entry["expires_at"]:
                        self.hits += 1
                        logger.debug(f"Cache HIT (Memory): {cache_key[:16]}...")
                        return entry["value"]
                    else:
                        # Expired - remove
                        del self._memory_cache[cache_key]
                        self.misses += 1
                        logger.debug(f"Cache MISS (Memory, expired): {cache_key[:16]}...")
                        return None
                else:
                    self.misses += 1
                    logger.debug(f"Cache MISS (Memory): {cache_key[:16]}...")
                    return None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            self.misses += 1
            return None

    async def set(
        self,
        signal_text: str,
        value: Dict[str, Any],
        icp_context: Optional[str] = None,
        model: str = "1b",
        ttl: Optional[int] = None
    ):
        """
        Store response in cache.

        Args:
            signal_text: The signal text
            value: Response dict to cache
            icp_context: Optional ICP context
            model: Model identifier
            ttl: Optional TTL override (seconds)
        """
        cache_key = self._generate_cache_key(signal_text, icp_context, model)
        ttl = ttl or self.ttl_seconds

        try:
            if self.backend == "redis" and self.redis_client:
                # Redis backend
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(value)
                )
                logger.debug(f"Cache SET (Redis): {cache_key[:16]}... (TTL={ttl}s)")
            else:
                # Memory backend - implement LRU eviction
                if len(self._memory_cache) >= self.max_size:
                    # Simple FIFO eviction (can upgrade to proper LRU if needed)
                    oldest_key = next(iter(self._memory_cache))
                    del self._memory_cache[oldest_key]
                    logger.debug(f"Cache eviction (Memory): {oldest_key[:16]}...")

                self._memory_cache[cache_key] = {
                    "value": value,
                    "expires_at": datetime.now() + timedelta(seconds=ttl)
                }
                logger.debug(f"Cache SET (Memory): {cache_key[:16]}... (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"Cache SET error: {e}")

    async def invalidate(
        self,
        signal_text: str,
        icp_context: Optional[str] = None,
        model: str = "1b"
    ):
        """Invalidate (delete) a cache entry."""
        cache_key = self._generate_cache_key(signal_text, icp_context, model)

        try:
            if self.backend == "redis" and self.redis_client:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Cache INVALIDATE (Redis): {cache_key[:16]}...")
            else:
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    logger.debug(f"Cache INVALIDATE (Memory): {cache_key[:16]}...")
        except Exception as e:
            logger.error(f"Cache INVALIDATE error: {e}")

    async def clear_all(self):
        """Clear all cache entries."""
        try:
            if self.backend == "redis" and self.redis_client:
                # Only clear keys with our prefix
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor,
                        match="model_cache:*",
                        count=100
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
                logger.info("Cache CLEAR ALL (Redis)")
            else:
                self._memory_cache.clear()
                logger.info("Cache CLEAR ALL (Memory)")
        except Exception as e:
            logger.error(f"Cache CLEAR ALL error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "backend": self.backend,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._memory_cache) if self.backend == "memory" else "N/A (Redis)",
            "max_size": self.max_size if self.backend == "memory" else "N/A (Redis)",
            "ttl_seconds": self.ttl_seconds
        }


# Singleton instance (will be initialized in main.py)
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> Optional[CacheManager]:
    """Get the singleton cache manager instance."""
    return _cache_manager


def init_cache_manager(
    backend: str = "memory",
    redis_url: Optional[str] = None,
    max_size: int = 1000,
    ttl_seconds: int = 2592000
) -> CacheManager:
    """Initialize the singleton cache manager."""
    global _cache_manager
    _cache_manager = CacheManager(
        backend=backend,
        redis_url=redis_url,
        max_size=max_size,
        ttl_seconds=ttl_seconds
    )
    return _cache_manager
