# "lines of code":"205","lines of commented":"0"
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from db import db

WAYSEER_DOMAIN = "interdependentway.org"

TIER_ORDER = {"free": 0, "supporter": 1, "pro": 2, "team": 3, "ws-tier": 4}
TIER_LIMITS_DEFAULT: Dict[str, Dict[str, Any]] = {
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
    "ws-tier": {
        "max_instances": None,
        "max_runs_per_month": None,
        "per_model_instance_cap": None,
        "max_personas": None,
        "hosted_requests_per_month": None,
        "daily_trial_requests": None,
        "daily_chats_per_24h": None,
        "daily_batch_runs_per_24h": None,
        "daily_roleplay_runs_per_24h": None,
        "max_connected_keys": None,
        "max_batch_size": None,
        "queue_priority": "highest",
        "hide_emergent_badge": True,
    },
}
TIER_LIMITS: Dict[str, Dict[str, Any]] = copy.deepcopy(TIER_LIMITS_DEFAULT)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_month_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()


def normalize_tier(value: Optional[str]) -> str:
    if value in TIER_ORDER:
        return value
    return "free"


def is_wayseer_email(value: Optional[str]) -> bool:
    email = str(value or "").strip().lower()
    return bool(email) and email.endswith(f"@{WAYSEER_DOMAIN}")


def is_wayseer_user(user_doc: Optional[dict]) -> bool:
    user = user_doc or {}
    return is_wayseer_email(user.get("email")) or is_wayseer_email(user.get("username"))


async def get_user_doc(user_id: str) -> Optional[dict]:
    return await db.users.find_one({"$or": [{"id": user_id}, {"user_id": user_id}]}, {"_id": 0})


def derive_billing_profile(user_doc: Optional[dict]) -> dict:
    billing = (user_doc or {}).get("billing", {}) or {}
    if is_wayseer_user(user_doc):
        tier = "ws-tier"
    else:
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
        "supporter_eligible": tier in {"supporter", "pro", "team", "ws-tier"},
        "team_seats": int(billing.get("team_seats") or (3 if tier == "team" else 1)),
        "is_ws_admin": tier == "ws-tier",
    }


async def get_user_billing_profile(user_id: str) -> dict:
    return derive_billing_profile(await get_user_doc(user_id))


async def warm_billing_tier_overrides() -> None:
    rows = await db.billing_tier_overrides.find({}, {"_id": 0, "tier": 1, "limits": 1}).to_list(100)
    for row in rows:
        tier = normalize_tier(row.get("tier"))
        if tier not in TIER_LIMITS:
            continue
        limits = row.get("limits") or {}
        if isinstance(limits, dict):
            TIER_LIMITS[tier].update(limits)


async def update_tier_limits(tier: str, updates: Dict[str, Any]) -> dict:
    normalized = normalize_tier(tier)
    if normalized not in TIER_LIMITS:
        raise HTTPException(status_code=400, detail="Unsupported tier")
    safe_updates = {k: v for k, v in updates.items() if k in TIER_LIMITS[normalized]}
    if not safe_updates:
        raise HTTPException(status_code=400, detail="No valid tier fields provided")
    TIER_LIMITS[normalized].update(safe_updates)
    await db.billing_tier_overrides.update_one(
        {"tier": normalized},
        {"$set": {"tier": normalized, "limits": TIER_LIMITS[normalized], "updated_at": iso_now()}},
        upsert=True,
    )
    return {"tier": normalized, "limits": TIER_LIMITS[normalized]}


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
# "lines of code":"205","lines of commented":"0"
