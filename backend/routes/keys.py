# "lines of code":"68","lines of commented":"5"
"""User API key management — secure storage, never expose full keys."""

import os
from fastapi import APIRouter, Depends, HTTPException

from db import db
from models.v1 import KeyStatusResponse, SetKeyRequest
from services.auth import get_current_user, get_user_id
from services.billing_tiers import get_user_billing_profile
from services.llm import DEFAULT_REGISTRY, validate_universal_key

router = APIRouter(prefix="/api/v1/keys", tags=["keys"])


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:6] + "..." + key[-4:]


@router.get("")
async def list_key_status(current_user: dict = Depends(get_current_user)):
    """List key status for all developers (never returns full keys)."""
    user_keys = current_user.get("api_keys", {})
    results = []

    for dev_id in DEFAULT_REGISTRY:
        key = user_keys.get(dev_id, "")
        auth_type = DEFAULT_REGISTRY[dev_id].get("auth_type", "emergent")

        if auth_type == "emergent":
            if key and key not in ("UNIVERSAL", ""):
                results.append(KeyStatusResponse(developer_id=dev_id, status="configured", masked_key=_mask_key(key)))
            else:
                universal = os.environ.get("EMERGENT_LLM_KEY", "")
                results.append(KeyStatusResponse(developer_id=dev_id, status="universal" if universal else "missing"))
        else:
            if key:
                results.append(KeyStatusResponse(developer_id=dev_id, status="configured", masked_key=_mask_key(key)))
            else:
                results.append(KeyStatusResponse(developer_id=dev_id, status="missing"))

    return results


@router.post("")
async def set_key(
    request: SetKeyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Set an API key for a developer. Stored in user document."""
    uid = get_user_id(current_user)
    if str(uid).startswith("guest:"):
        raise HTTPException(status_code=403, detail="Sign in required to manage API keys")

    billing_profile = await get_user_billing_profile(uid)
    max_connected_keys = billing_profile.get("max_connected_keys")
    existing_keys = (current_user.get("api_keys") or {}).copy()
    already_configured = bool(existing_keys.get(request.developer_id))
    configured_count = len([key for key in existing_keys.values() if key])
    if max_connected_keys is not None and not already_configured and configured_count >= int(max_connected_keys):
        raise HTTPException(
            status_code=403,
            detail=f"Your {billing_profile['subscription_tier']} tier allows up to {max_connected_keys} connected keys.",
        )

    await db.users.update_one(
        {"$or": [{"id": uid}, {"user_id": uid}]},
        {"$set": {f"api_keys.{request.developer_id}": request.api_key}},
    )
    return {"message": f"Key set for {request.developer_id}", "status": "configured"}


@router.delete("/{developer_id}")
async def remove_key(
    developer_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a user's API key for a developer (reverts to universal if applicable)."""
    uid = get_user_id(current_user)
    await db.users.update_one(
        {"$or": [{"id": uid}, {"user_id": uid}]},
        {"$unset": {f"api_keys.{developer_id}": ""}},
    )
    return {"message": f"Key removed for {developer_id}"}


@router.get("/universal/status")
async def universal_key_status():
    """Check if the universal key is valid."""
    return await validate_universal_key()
# "lines of code":"68","lines of commented":"5"
