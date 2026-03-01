from fastapi import APIRouter, HTTPException, Depends, Request, Response as FastAPIResponse
from datetime import datetime, timezone, timedelta
import uuid
import os
import httpx
import logging

from db import db
from models.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    GoogleAuthUser,
    ServiceAccountCreateRequest,
    ServiceAccountResponse,
    ServiceAccountTokenRequest,
    ServiceAccountTokenResponse,
)
from services.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_user_id, generate_service_token, hash_service_token
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(user_data.password)
    now = datetime.now(timezone.utc)

    user = {
        "id": user_id,
        "username": user_data.username,
        "password": hashed_pw,
        "created_at": now.isoformat(),
        "api_keys": {}
    }
    await db.users.insert_one(user)

    token = create_access_token(user_id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user_id, username=user_data.username, created_at=now)
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user["id"])
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            created_at=datetime.fromisoformat(user["created_at"])
        )
    )


@router.post("/google/session")
async def process_google_session(request: Request, response: FastAPIResponse):
    """Process Google OAuth session_id from Emergent Auth"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="No session ID provided")

    auth_service_url = os.environ.get("AUTH_SERVICE_URL")
    if not auth_service_url:
        raise HTTPException(status_code=500, detail="Auth service not configured")

    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                f"{auth_service_url}/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            auth_response.raise_for_status()
            user_data = auth_response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get session data: {e}")
            raise HTTPException(status_code=401, detail="Invalid session")

    email = user_data.get("email")
    name = user_data.get("name", "")
    picture = user_data.get("picture", "")
    session_token = user_data.get("session_token")

    if not email or not session_token:
        raise HTTPException(status_code=400, detail="Incomplete user data")

    existing_user = await db.users.find_one({"email": email}, {"_id": 0})

    if existing_user:
        user_id = existing_user.get("user_id")
        if not user_id:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            await db.users.update_one({"email": email}, {"$set": {"user_id": user_id}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "api_keys": {}
        }
        await db.users.insert_one(user_doc)

    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    }
    await db.user_sessions.update_one(
        {"user_id": user_id},
        {"$set": session_doc},
        upsert=True
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )

    return GoogleAuthUser(user_id=user_id, email=email, name=name, picture=picture)


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "user_id": current_user.get("user_id") or current_user.get("id"),
        "email": current_user.get("email") or current_user.get("username"),
        "name": current_user.get("name", current_user.get("username", "")),
        "picture": current_user.get("picture")
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: FastAPIResponse,
    current_user: dict = Depends(get_current_user)
):
    """Logout user (clears session)"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
        response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}
