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
