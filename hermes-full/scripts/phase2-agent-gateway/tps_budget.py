#!/usr/bin/env python3
"""
TPS Budget Manager — sliding 60-second window, 100 TPS limit across all agents.
Uses an in-memory counter (Redis optional). Falls back to in-memory if Redis unavailable.
"""
import time
import threading
from collections import deque


class TPSBudgetManager:
    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._lock = threading.Lock()
        self._timestamps: deque = deque()  # timestamps of each consumed token

        # Try Redis — graceful fallback to in-memory
        self._redis = None
        try:
            import redis
            r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=1)
            r.ping()
            self._redis = r
        except Exception:
            pass  # Redis unavailable, use in-memory counter

    def remaining(self) -> int:
        if self._redis:
            return self._redis_remaining()
        return self._memory_remaining()

    def consume(self, tokens: int = 1):
        if self._redis:
            self._redis_consume(tokens)
        else:
            self._memory_consume(tokens)

    # ── Redis implementation ──────────────────────────────────────────────────

    def _redis_key(self) -> str:
        bucket = int(time.time()) // self.window
        return f"hermes:tps:{bucket}"

    def _redis_remaining(self) -> int:
        key = self._redis_key()
        used = int(self._redis.get(key) or 0)
        return max(0, self.limit - used)

    def _redis_consume(self, tokens: int):
        key = self._redis_key()
        pipe = self._redis.pipeline()
        pipe.incrby(key, tokens)
        pipe.expire(key, self.window * 2)
        pipe.execute()

    # ── In-memory implementation ──────────────────────────────────────────────

    def _memory_remaining(self) -> int:
        now = time.time()
        with self._lock:
            self._evict(now)
            return max(0, self.limit - len(self._timestamps))

    def _memory_consume(self, tokens: int):
        now = time.time()
        with self._lock:
            self._evict(now)
            for _ in range(tokens):
                self._timestamps.append(now)

    def _evict(self, now: float):
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
