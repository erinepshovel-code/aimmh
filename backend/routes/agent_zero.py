from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import os
import httpx
import logging

from db import db
from models.agent_zero import A0IngestRequest, A0RouteRequest
from services.auth import get_current_user, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/a0", tags=["agent_zero"])


@router.post("/ingest")
async def ingest_to_agent_zero(
    request: A0IngestRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send conversation to Agent Zero for EDCM analysis"""
    a0_url = os.environ.get("A0_URL", "http://127.0.0.1:8787")
    a0_key = os.environ.get("A0_API_KEY", "")

    if not a0_url:
        raise HTTPException(status_code=503, detail="Agent Zero not configured")

    try:
        edcm_payload = {
            "source": "multi-ai-hub",
            "conversation_id": request.conversation_id,
            "title": request.title,
            "user_id": get_user_id(current_user),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": request.messages,
            "constraints": {
                "global_context": request.global_context,
                "model_roles": request.model_roles
            },
            "metadata": request.metadata or {}
        }

        headers = {"Content-Type": "application/json"}
        if a0_key:
            headers["X-A0-Key"] = a0_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{a0_url}/ingest/transcript",
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
    a0_url = os.environ.get("A0_URL", "http://127.0.0.1:8787")
    a0_key = os.environ.get("A0_API_KEY", "")

    if not a0_url:
        raise HTTPException(status_code=503, detail="Agent Zero not configured")

    try:
        headers = {"Content-Type": "application/json"}
        if a0_key:
            headers["X-A0-Key"] = a0_key

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{a0_url}/route",
                json={
                    "message": request.message,
                    "models": request.models,
                    "user_id": get_user_id(current_user),
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
    """Check if Agent Zero is reachable"""
    a0_url = os.environ.get("A0_URL", "http://127.0.0.1:8787")

    if not a0_url:
        return {"status": "not_configured"}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{a0_url}/health")
            return {
                "status": "connected" if response.status_code == 200 else "error",
                "a0_url": a0_url,
                "response": response.json() if response.status_code == 200 else None
            }
    except Exception as e:
        return {
            "status": "unreachable",
            "a0_url": a0_url,
            "error": str(e)
        }
