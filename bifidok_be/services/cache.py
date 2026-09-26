"""
Redis caching layer and in-memory fallback for Orange Systems platform.
Provides transparent TTL caching and background job status tracking.
"""
import copy
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class InMemoryTTLCache:
    """
    Thread-safe in-memory cache with per-key TTL expiration.
    Used as an automatic fallback when Redis is unreachable.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if expiry is not None and time.time() > expiry:
                del self._cache[key]
                return None
            return copy.deepcopy(val)

    def set(self, key: str, value: Any, ttl: Optional[int] = 86400) -> bool:
        with self._lock:
            expiry = time.time() + ttl if (ttl is not None and ttl > 0) else None
            self._cache[key] = (copy.deepcopy(value), expiry)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            now = time.time()
            # Clean expired on len count
            expired = [k for k, (_, exp) in self._cache.items() if exp is not None and now > exp]
            for k in expired:
                del self._cache[k]
            return len(self._cache)


_in_memory_cache = InMemoryTTLCache()
_redis_client: Optional[Any] = None
_redis_checked = False
_redis_init_lock = threading.Lock()


def get_redis_client():
    """
    Returns an active Redis client if available, or None if unreachable.
    Caches connection state to avoid blocking subsequent calls.
    """
    global _redis_client, _redis_checked
    with _redis_init_lock:
        if _redis_checked:
            return _redis_client

        try:
            import redis

            client = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            client.ping()
            _redis_client = client
            logger.info("Connected to Redis at %s", REDIS_URL)
        except Exception as exc:
            logger.info(
                "Redis connection failed (%s). Falling back to in-memory TTL cache.",
                exc,
            )
            _redis_client = None

        _redis_checked = True
        return _redis_client


def reset_cache_state(force_redis: Optional[bool] = None) -> None:
    """Helper for testing to reset connection check state and clear in-memory cache."""
    global _redis_client, _redis_checked
    with _redis_init_lock:
        _redis_checked = False
        _redis_client = None
        _in_memory_cache.clear()
        if force_redis is False:
            _redis_checked = True
            _redis_client = None


def get_cache(key: str) -> Optional[Any]:
    """
    Retrieves a cached value by key.
    Checks Redis first if available; falls back to in-memory TTL cache.
    Automatically deserializes JSON values where applicable.
    """
    client = get_redis_client()
    if client is not None:
        try:
            raw = client.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (ValueError, TypeError):
                return raw
        except Exception as exc:
            logger.debug("Redis get failed for %s (%s). Falling back to in-memory.", key, exc)

    return _in_memory_cache.get(key)


def set_cache(key: str, value: Any, ttl: int = 86400) -> bool:
    """
    Stores a value in the cache with the specified TTL (default 24h = 86400s).
    Serializes complex objects (dicts, lists) to JSON before storing in Redis.
    Mirrors in in-memory TTL cache as resilience guarantee.
    """
    # Prepare serializable copy for in-memory
    if isinstance(value, (dict, list, int, float, bool, str)) or value is None:
        _in_memory_cache.set(key, value, ttl=ttl)
    else:
        _in_memory_cache.set(key, str(value), ttl=ttl)

    client = get_redis_client()
    if client is not None:
        try:
            if isinstance(value, (dict, list)):
                str_val = json.dumps(value)
            elif isinstance(value, (int, float, bool, str)):
                str_val = str(value)
            elif value is None:
                str_val = "null"
            else:
                str_val = str(value)

            client.set(key, str_val, ex=ttl)
            return True
        except Exception as exc:
            logger.debug("Redis set failed for %s (%s). Kept in in-memory.", key, exc)
            return True

    return True


def delete_cache(key: str) -> bool:
    """Removes a key from both Redis and in-memory cache."""
    _in_memory_cache.delete(key)
    client = get_redis_client()
    if client is not None:
        try:
            client.delete(key)
            return True
        except Exception:
            pass
    return True


def update_job_status(
    job_id: str,
    status: str,
    progress: float,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Updates the background ingestion job status and progress in the cache.
    Progress is clamped between 0.0 and 1.0.
    """
    clamped_progress = max(0.0, min(1.0, float(progress)))
    payload = {
        "job_id": job_id,
        "status": status,
        "progress": round(clamped_progress, 3),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "meta": meta or {},
    }
    set_cache(f"job:{job_id}", payload, ttl=86400)


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the background ingestion job status and progress.
    Returns a dict with job_id, status, progress, updated_at, and meta, or None.
    """
    data = get_cache(f"job:{job_id}")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return None
    if isinstance(data, dict):
        return data
    return None
