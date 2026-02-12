from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import os
import httpx
import logging

from db import db
from models.agent_zero import A0IngestRequest, A0RouteRequest
from models.edcm import A0Config
from services.auth import get_current_user, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/a0", tags=["agent_zero"])


async def get_a0_connection(user_id: str) -> dict:
    """Get A0 connection details for user, falling back to env defaults"""
    config = await db.a0_config.find_one({"user_id": user_id}, {"_id": 0})
    if config:
        if config.get("mode") == "cloud":
            return {"url": config.get("cloud_url", ""), "key": config.get("api_key", "")}
        else:
            host = config.get("local_url", "http://127.0.0.1")
            port = config.get("local_port", 8787)
            return {"url": f"{host}:{port}", "key": config.get("api_key", "")}
    return {
        "url": os.environ.get("A0_URL", "http://127.0.0.1:8787"),
        "key": os.environ.get("A0_API_KEY", "")
    }


@router.get("/config")
async def get_a0_config(current_user: dict = Depends(get_current_user)):
    """Get user's A0 connection config"""
    uid = get_user_id(current_user)
    config = await db.a0_config.find_one({"user_id": uid}, {"_id": 0})
    if not config:
        return {
            "mode": "local",
            "local_url": "http://192.168.1.1",
            "local_port": 8787,
            "cloud_url": "",
            "api_key": "",
            "route_via_a0": False,
            "auto_ingest": False
        }
    config.pop("user_id", None)
    return config


@router.put("/config")
async def update_a0_config(
    config: A0Config,
    current_user: dict = Depends(get_current_user)
):
    """Save user's A0 connection config"""
    uid = get_user_id(current_user)
    doc = config.model_dump()
    doc["user_id"] = uid
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.a0_config.update_one(
        {"user_id": uid},
        {"$set": doc},
        upsert=True
    )
    return {"message": "A0 config saved"}


@router.post("/ingest")
async def ingest_to_agent_zero(
    request: A0IngestRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send conversation to Agent Zero for EDCM analysis"""
    uid = get_user_id(current_user)
    conn = await get_a0_connection(uid)

    if not conn["url"]:
        raise HTTPException(status_code=503, detail="Agent Zero not configured")

    try:
        edcm_payload = {
            "source": "multi-ai-hub",
            "conversation_id": request.conversation_id,
            "title": request.title,
            "user_id": uid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": request.messages,
            "constraints": {
                "global_context": request.global_context,
                "model_roles": request.model_roles
            },
            "metadata": request.metadata or {}
        }

        headers = {"Content-Type": "application/json"}
        if conn["key"]:
            headers["X-A0-Key"] = conn["key"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{conn['url']}/ingest/transcript",
                json=edcm_payload,
                headers=headers
            )
            response.raise_for_status()

        return {"message": "Ingested to Agent Zero", "a0_response": response.json()}

    except httpx.HTTPError as e:
        logger.error(f"Agent Zero ingestion failed: {e}")
        raise HTTPException(status_code=503, detail=f"Agent Zero unreachable: {str(e)}")


@router.post("/route")
async def route_via_agent_zero(
    request: A0RouteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Route request through Agent Zero for TIW policy + logging"""
    uid = get_user_id(current_user)
    conn = await get_a0_connection(uid)

    if not conn["url"]:
        raise HTTPException(status_code=503, detail="Agent Zero not configured")

    try:
        headers = {"Content-Type": "application/json"}
        if conn["key"]:
            headers["X-A0-Key"] = conn["key"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{conn['url']}/route",
                json={
                    "message": request.message,
                    "models": request.models,
                    "user_id": uid,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                headers=headers
            )
            response.raise_for_status()

        return response.json()

    except httpx.HTTPError as e:
        logger.error(f"Agent Zero routing failed: {e}")
        raise HTTPException(status_code=503, detail=f"Agent Zero unreachable: {str(e)}")


@router.get("/health")
async def check_agent_zero_health(current_user: dict = Depends(get_current_user)):
    """Check if Agent Zero is reachable using user's config"""
    uid = get_user_id(current_user)
    conn = await get_a0_connection(uid)

    if not conn["url"]:
        return {"status": "not_configured"}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{conn['url']}/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "a0_url": conn["url"],
                "response": response.json() if response.status_code == 200 else None
            }
    except Exception as e:
        return {
            "status": "unreachable",
            "a0_url": conn["url"],
            "error": str(e)
        }
