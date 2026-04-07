from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from db import db

TIER_ORDER = {"free": 0, "supporter": 1, "pro": 2, "team": 3}
TIER_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "max_instances": 5,
        "max_runs_per_month": 100,
        "per_model_instance_cap": 2,
        "max_personas": 3,
        "hosted_requests_per_month": 100,
        "daily_trial_requests": 120,
        "daily_chats_per_24h": 25,
        "daily_batch_runs_per_24h": 5,
        "daily_roleplay_runs_per_24h": 2,
        "max_connected_keys": 1,
        "max_batch_size": 20,
        "queue_priority": "low",
        "hide_emergent_badge": False,
    },
    "supporter": {
        "max_instances": 25,
        "max_runs_per_month": 600,
        "per_model_instance_cap": None,
        "max_personas": None,
        "hosted_requests_per_month": 1000,
        "daily_trial_requests": None,
        "max_connected_keys": 5,
        "max_batch_size": 60,
        "queue_priority": "medium",
        "hide_emergent_badge": True,
    },
    "pro": {
        "max_instances": 100,
        "max_runs_per_month": None,
        "per_model_instance_cap": None,
        "max_personas": None,
        "hosted_requests_per_month": 5000,
        "daily_trial_requests": None,
        "max_connected_keys": 25,
        "max_batch_size": 200,
        "queue_priority": "high",
        "hide_emergent_badge": True,
    },
    "team": {
        "max_instances": 300,
        "max_runs_per_month": None,
        "per_model_instance_cap": None,
        "max_personas": None,
        "hosted_requests_per_month": 20000,
        "daily_trial_requests": None,
        "max_connected_keys": 100,
        "max_batch_size": 500,
        "queue_priority": "high",
        "hide_emergent_badge": True,
    },
}


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_month_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()


def normalize_tier(value: Optional[str]) -> str:
    if value in TIER_ORDER:
        return value
    return "free"


async def get_user_doc(user_id: str) -> Optional[dict]:
    return await db.users.find_one({"$or": [{"id": user_id}, {"user_id": user_id}]}, {"_id": 0})


def derive_billing_profile(user_doc: Optional[dict]) -> dict:
    billing = (user_doc or {}).get("billing", {}) or {}
    tier = normalize_tier(billing.get("subscription_tier"))
    limits = TIER_LIMITS[tier]
    return {
        "subscription_tier": tier,
        "max_instances": limits["max_instances"],
        "max_runs_per_month": limits["max_runs_per_month"],
        "per_model_instance_cap": limits["per_model_instance_cap"],
        "max_personas": limits["max_personas"],
        "hosted_requests_per_month": limits["hosted_requests_per_month"],
        "daily_chats_per_24h": limits.get("daily_chats_per_24h"),
        "daily_batch_runs_per_24h": limits.get("daily_batch_runs_per_24h"),
        "daily_roleplay_runs_per_24h": limits.get("daily_roleplay_runs_per_24h"),
        "max_connected_keys": limits["max_connected_keys"],
        "max_batch_size": limits["max_batch_size"],
        "queue_priority": limits["queue_priority"],
        "hide_emergent_badge": limits["hide_emergent_badge"],
        "supporter_eligible": tier in {"supporter", "pro", "team"},
        "team_seats": int(billing.get("team_seats") or (3 if tier == "team" else 1)),
    }


async def get_user_billing_profile(user_id: str) -> dict:
    return derive_billing_profile(await get_user_doc(user_id))


def merge_tier(current_tier: str, requested_tier: str) -> str:
    current = normalize_tier(current_tier)
    requested = normalize_tier(requested_tier)
    return requested if TIER_ORDER[requested] >= TIER_ORDER[current] else current


def _utc_day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for.strip():
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _quota_subject_key(current_user: dict, request: Request) -> str:
    if current_user.get("auth_type") == "guest":
        return f"guest-ip:{_request_ip(request)}"
    user_id = current_user.get("user_id") or current_user.get("id") or "unknown"
    return f"user:{user_id}"


async def consume_non_paying_daily_quota(
    *,
    current_user: dict,
    billing_profile: dict,
    request: Request,
    action: str,
    limit: Optional[int],
    error_message: str,
) -> Optional[dict]:
    if limit is None:
        return None
    if billing_profile.get("subscription_tier") != "free":
        return None

    safe_limit = int(limit)
    now_iso = iso_now()
    subject_key = _quota_subject_key(current_user, request)
    day_key = _utc_day_key()
    identity_query = {
        "subject_key": subject_key,
        "day_key": day_key,
        "action": action,
    }

    existing = await db.hub_quota_usage.find_one(identity_query, {"_id": 0, "count": 1})
    if existing and int(existing.get("count") or 0) >= safe_limit:
        raise HTTPException(status_code=403, detail=error_message)

    update = {
        "$inc": {"count": 1},
        "$set": {"updated_at": now_iso},
        "$setOnInsert": {"created_at": now_iso},
    }
    await db.hub_quota_usage.update_one(
        identity_query,
        update,
        upsert=True,
    )
    updated = await db.hub_quota_usage.find_one(identity_query, {"_id": 0, "count": 1})
    return {
        "subject_key": subject_key,
        "day_key": day_key,
        "action": action,
        "used": int((updated or {}).get("count") or 0),
        "limit": safe_limit,
    }
