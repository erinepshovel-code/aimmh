from fastapi import APIRouter, Depends
import logging

from db import db
from models.chat import APIKeyUpdate, APIKeysResponse
from services.auth import get_current_user, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["keys"])


@router.put("/keys")
async def update_api_key(key_data: APIKeyUpdate, current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    query = {"$or": [{"id": user_id}, {"user_id": user_id}]}

    update_data = {}
    if key_data.use_universal:
        update_data[f"api_keys.{key_data.provider}"] = "UNIVERSAL"
    elif key_data.api_key:
        update_data[f"api_keys.{key_data.provider}"] = key_data.api_key
    else:
        # If universal is being turned OFF for emergent-backed providers,
        # store an explicit sentinel so default-on logic won't re-enable it.
        if key_data.provider in {"gpt", "claude", "gemini"}:
            update_data[f"api_keys.{key_data.provider}"] = "DISABLED"
        else:
            await db.users.update_one(query, {"$unset": {f"api_keys.{key_data.provider}": ""}})
            return {"message": "API key removed"}

    result = await db.users.update_one(query, {"$set": update_data})
    if result.modified_count == 0:
        logger.warning(f"No user updated for user_id: {user_id}")

    return {"message": "API key updated"}


@router.get("/keys", response_model=APIKeysResponse)
async def get_api_keys(current_user: dict = Depends(get_current_user)):
    api_keys = current_user.get("api_keys", {})

    masked_keys = {}
    for provider, key in api_keys.items():
        if key == "UNIVERSAL":
            masked_keys[provider] = "UNIVERSAL"
        elif key == "DISABLED":
            masked_keys[provider] = "DISABLED"
        elif key:
            masked_keys[provider] = f"{key[:8]}...{key[-4:]}"
        else:
            masked_keys[provider] = None

    return APIKeysResponse(**masked_keys)
