from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoogleAuthUser(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class ServiceAccountCreateRequest(BaseModel):
    username: str
    password: str
    label: Optional[str] = None


class ServiceAccountResponse(BaseModel):
    id: str
    username: str
    label: Optional[str] = None
    owner_user_id: str
    active: bool
    created_at: datetime


class ServiceAccountTokenRequest(BaseModel):
    username: str
    password: str
    expires_in_days: int = Field(default=90, ge=1, le=365)


class ServiceAccountTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    service_account_username: str
