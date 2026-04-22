"""Rate limiter for Bantu-OS Network API."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional


class RateLimiter:
    """
    Sliding-window rate limiter per API key.

    Default: 60 requests/minute per key.
    Stores request timestamps in memory (resets on restart — use Redis for production).
    """

    _DEFAULT_LIMIT = 60  # requests per window
    _WINDOW_SECS = 60.0

    def __init__(self) -> None:
        # key -> sorted list of request timestamps
        self._buckets: Dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: Optional[int] = None) -> bool:
        """Return True if the key is within its rate limit."""
        limit = limit or self._DEFAULT_LIMIT
        now = time.time()
        cutoff = now - self._WINDOW_SECS

        async with self._lock:
            bucket = self._buckets[key]

            # Remove old timestamps outside the window
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)

            if len(bucket) >= limit:
                return False

            bucket.append(now)
            return True

    async def reset(self, key: str) -> None:
        """Clear rate limit for a key (e.g. after upgrade)."""
        async with self._lock:
            self._buckets.pop(key, None)

    async def get_usage(self, key: str) -> Dict[str, float]:
        """Return current usage stats for monitoring."""
        now = time.time()
        cutoff = now - self._WINDOW_SECS

        async with self._lock:
            bucket = self._buckets.get(key, [])
            active = [ts for ts in bucket if ts >= cutoff]

        return {
            "requests_in_window": len(active),
            "window_seconds": self._WINDOW_SECS,
            "limit": self._DEFAULT_LIMIT,
        }
