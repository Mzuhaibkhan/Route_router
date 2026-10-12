"""
Cache utilities with cache stampede lock for concurrent request deduplication.
Ensures only one thread computes expensive external ORS or weather queries on a cache miss.
"""
import threading
from typing import Any, Callable

from django.core.cache import cache

_locks_mutex = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}


def _get_lock_for_key(key: str) -> threading.Lock:
    """Retrieve or create a thread lock specific to a cache key."""
    with _locks_mutex:
        if key not in _key_locks:
            _key_locks[key] = threading.Lock()
        return _key_locks[key]


def get_or_compute(key: str, fn: Callable[[], Any], timeout: int = 1800) -> Any:
    """
    Retrieves value from Django cache, or safely computes and stores it under a per-key lock.
    Uses double-checked locking to protect against cache stampedes.
    """
    val = cache.get(key)
    if val is not None:
        return val

    lock = _get_lock_for_key(key)
    with lock:
        # Re-check cache inside lock
        val = cache.get(key)
        if val is not None:
            return val

        val = fn()
        cache.set(key, val, timeout)
        return val


def make_route_cache_key(
    origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
) -> str:
    """Create normalized cache key for routing queries."""
    return f"route:{origin_lat:.4f}:{origin_lng:.4f}->{dest_lat:.4f}:{dest_lng:.4f}"


def make_weather_cache_key(lat: float, lng: float, start_ts: int) -> str:
    """Create normalized cache key for hourly weather queries."""
    hour_bucket = (start_ts // 3600) * 3600
    return f"weather:{lat:.2f}:{lng:.2f}:{hour_bucket}"
