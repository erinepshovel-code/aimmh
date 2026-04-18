# "lines of code":"114","lines of commented":"0"
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from db import db

HUB_CONTEXT_CACHE_COLLECTION = "hub_context_cache"
DEFAULT_CONTEXT_CACHE_TTL_SECONDS = 1800
_MIN_TTL_SECONDS = 60
_INDEX_READY = False


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def build_context_cache_key(
    *,
    instance: dict,
    verbosity: Optional[int],
    thread_updated_at: Optional[str],
) -> str:
    payload = {
        "instance_id": instance.get("instance_id"),
        "model_id": instance.get("model_id"),
        "role_preset": instance.get("role_preset"),
        "context": instance.get("context") or {},
        "instance_prompt": instance.get("instance_prompt") or "",
        "history_window_messages": int(instance.get("history_window_messages", 12) or 0),
        "instance_updated_at": instance.get("updated_at") or "",
        "thread_updated_at": thread_updated_at or "",
        "verbosity": verbosity,
    }
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


async def _ensure_indexes() -> None:
    global _INDEX_READY
    if _INDEX_READY:
        return
    coll = db[HUB_CONTEXT_CACHE_COLLECTION]
    await coll.create_index(
        [("user_id", 1), ("instance_id", 1), ("cache_key", 1)],
        unique=True,
        name="hub_ctx_cache_unique",
    )
    await coll.create_index("expires_at", expireAfterSeconds=0, name="hub_ctx_cache_ttl")
    _INDEX_READY = True


async def get_instance_context_cache(user_id: str, instance_id: str, cache_key: str) -> Optional[dict]:
    await _ensure_indexes()
    doc = await db[HUB_CONTEXT_CACHE_COLLECTION].find_one(
        {
            "user_id": user_id,
            "instance_id": instance_id,
            "cache_key": cache_key,
            "expires_at": {"$gt": _now_utc()},
        },
        {"_id": 0, "payload": 1},
    )
    if not doc:
        return None
    payload = doc.get("payload")
    return payload if isinstance(payload, dict) else None


async def set_instance_context_cache(
    *,
    user_id: str,
    instance_id: str,
    cache_key: str,
    payload: dict,
    ttl_seconds: int = DEFAULT_CONTEXT_CACHE_TTL_SECONDS,
) -> None:
    await _ensure_indexes()
    now = _now_utc()
    safe_ttl = max(_MIN_TTL_SECONDS, int(ttl_seconds or DEFAULT_CONTEXT_CACHE_TTL_SECONDS))
    expires_at = now + timedelta(seconds=safe_ttl)
    await db[HUB_CONTEXT_CACHE_COLLECTION].update_one(
        {"user_id": user_id, "instance_id": instance_id, "cache_key": cache_key},
        {
            "$set": {
                "payload": payload,
                "updated_at": _iso(now),
                "expires_at": expires_at,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "instance_id": instance_id,
                "cache_key": cache_key,
                "created_at": _iso(now),
            },
        },
        upsert=True,
    )


async def purge_instance_context_cache(user_id: str, instance_id: str) -> None:
    await _ensure_indexes()
    await db[HUB_CONTEXT_CACHE_COLLECTION].delete_many({"user_id": user_id, "instance_id": instance_id})
# "lines of code":"114","lines of commented":"0"
