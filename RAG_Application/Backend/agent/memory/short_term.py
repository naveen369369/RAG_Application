from __future__ import annotations

import os
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_SESSIONS = 1000
MAX_TURNS_PER_SESSION = 50


@dataclass
class _SessionMessage:
    role: str
    content: str


class SessionStore:
    """
    Thread-safe in-memory conversation store keyed by session_id.
    Falls back to Redis when REDIS_URL env var is set.
    Short-term memory: cleared when the process restarts.
    """

    def __init__(self) -> None:
        self._store: Dict[str, deque] = {}
        self._lock = Lock()
        self._redis = self._try_redis()

    def _try_redis(self):
        url = os.getenv("REDIS_URL", "")
        if not url:
            return None
        try:
            import redis
            r = redis.from_url(url)
            r.ping()
            logger.info("SessionStore: using Redis at %s", url)
            return r
        except Exception as exc:
            logger.warning("SessionStore: Redis unavailable (%s), using in-memory", exc)
            return None

    # ── Public API ──────────────────────────────────────────────────────────

    def append(self, session_id: str, role: str, content: str) -> None:
        if not session_id:
            return
        if self._redis:
            self._redis_append(session_id, role, content)
            return
        with self._lock:
            if session_id not in self._store:
                if len(self._store) >= MAX_SESSIONS:
                    oldest = next(iter(self._store))
                    del self._store[oldest]
                self._store[session_id] = deque(maxlen=MAX_TURNS_PER_SESSION)
            self._store[session_id].append(_SessionMessage(role=role, content=content))

    def get(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        if not session_id:
            return []
        if self._redis:
            return self._redis_get(session_id, limit)
        with self._lock:
            msgs = list(self._store.get(session_id, []))[-limit:]
            return [{"role": m.role, "content": m.content} for m in msgs]

    def clear(self, session_id: str) -> None:
        if self._redis:
            self._redis.delete(f"session:{session_id}")
            return
        with self._lock:
            self._store.pop(session_id, None)

    # ── Redis helpers ────────────────────────────────────────────────────────

    def _redis_append(self, session_id: str, role: str, content: str) -> None:
        key = f"session:{session_id}"
        self._redis.rpush(key, json.dumps({"role": role, "content": content}))
        self._redis.ltrim(key, -MAX_TURNS_PER_SESSION, -1)
        self._redis.expire(key, 86400)

    def _redis_get(self, session_id: str, limit: int) -> List[Dict[str, str]]:
        key = f"session:{session_id}"
        raw = self._redis.lrange(key, -limit, -1)
        return [json.loads(r) for r in raw]
