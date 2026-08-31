"""Shared FastAPI dependencies: Redis, session store, common lookups."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_redis: Any = None


def get_redis():
    """Get or create a Redis client singleton.

    Returns ``None`` when Redis is unavailable so callers can degrade
    gracefully (chat history simply won't persist across restarts).
    """
    global _redis
    if _redis is not None:
        return _redis

    url = os.getenv("REDIS_URL", "")
    if not url:
        log.info("REDIS_URL not set, chat history will be in-memory only")
        return None

    try:
        import redis as _redis_mod

        _redis = _redis_mod.from_url(url, decode_responses=True)
        _redis.ping()
        log.info("Connected to Redis at %s", url)
        return _redis
    except Exception as exc:
        log.warning("Redis unavailable (%s), falling back to no persistence", exc)
        _redis = None
        return None


# ---------------------------------------------------------------------------
# Chat history (per-session, backed by Redis when available)
# ---------------------------------------------------------------------------

_in_memory_history: dict[str, list[dict]] = {}


def save_chat_message(session_id: str, role: str, content: str, **extra: Any) -> None:
    """Append a message to the session's chat history."""
    message = {"role": role, "content": content, **extra}
    r = get_redis()
    key = f"chat:{session_id}"
    if r:
        try:
            r.rpush(key, json.dumps(message))
            r.expire(key, 3600 * 24)  # 24h TTL
            return
        except Exception:
            pass
    _in_memory_history.setdefault(key, []).append(message)


def get_chat_history(session_id: str, limit: int = 50) -> list[dict]:
    """Return the last *limit* messages for a session."""
    r = get_redis()
    key = f"chat:{session_id}"
    if r:
        try:
            raw = r.lrange(key, -limit, -1)
            return [json.loads(m) for m in raw]
        except Exception:
            pass
    return _in_memory_history.get(key, [])[-limit:]


def clear_chat_history(session_id: str) -> None:
    """Delete all chat history for a session."""
    r = get_redis()
    key = f"chat:{session_id}"
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _in_memory_history.pop(key, None)
