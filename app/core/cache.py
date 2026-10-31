"""Cache interface with an in-process TTL default (R12 result caching).

Only non-user-specific or short-lived data lives here (LLM classification of identical text,
flight searches by route+date). Per-user check-up results are cached in the `checkups` table
so they hold across stateless workers. A Redis implementation can be plugged in later.
"""
from __future__ import annotations

import time
from typing import Any, Protocol


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: float) -> None: ...
    def delete(self, key: str) -> None: ...
    def prune(self) -> int: ...
    def clear(self) -> None: ...


class InMemoryTTLCache:
    def __init__(self, max_items: int = 10_000) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._max_items = max_items

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        if len(self._data) >= self._max_items:
            self.prune()
            if len(self._data) >= self._max_items:
                self._data.pop(next(iter(self._data)))
        self._data[key] = (time.monotonic() + ttl_seconds, value)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def prune(self) -> int:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._data.items() if exp < now]
        for k in expired:
            self._data.pop(k, None)
        return len(expired)

    def clear(self) -> None:
        self._data.clear()


cache: Cache = InMemoryTTLCache()
