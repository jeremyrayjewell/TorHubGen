"""In-memory storage and rate limiting primitives."""

from __future__ import annotations

import threading
import time
from collections import deque


class MessageStore:
    def __init__(self, *, max_messages: int) -> None:
        self._messages: deque[dict] = deque(maxlen=max_messages)
        self._lock = threading.Lock()

    def add(self, message: dict) -> None:
        with self._lock:
            self._messages.append(message)

    def list(self) -> list[dict]:
        with self._lock:
            return list(self._messages)

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()


class TokenBucketRateLimiter:
    """In-memory, per-process token bucket limiter."""

    def __init__(self, *, capacity: float, refill_per_second: float) -> None:
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("Invalid rate limiter parameters")
        self._capacity = float(capacity)
        self._refill_per_second = float(refill_per_second)
        self._state: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, cost: float = 1.0) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last_ts = self._state.get(key, (self._capacity, now))
            elapsed = max(0.0, now - last_ts)
            tokens = min(self._capacity, tokens + elapsed * self._refill_per_second)
            if tokens < cost:
                self._state[key] = (tokens, now)
                return False
            tokens -= cost
            self._state[key] = (tokens, now)
            return True
