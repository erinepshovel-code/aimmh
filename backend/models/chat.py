from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone


class APIKeyUpdate(BaseModel):
    provider: Literal["gpt", "claude", "gemini", "grok", "deepseek", "perplexity"]
    api_key: Optional[str] = None
    use_universal: bool = False


class APIKeysResponse(BaseModel):
    gpt: Optional[str] = None
    claude: Optional[str] = None
    gemini: Optional[str] = None
    grok: Optional[str] = None
    deepseek: Optional[str] = None
    perplexity: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    models: List[str]
    conversation_id: Optional[str] = None


class MessageFeedback(BaseModel):
    message_id: str
    feedback: Literal["up", "down"]


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class CatchupRequest(BaseModel):
    conversation_id: str
    new_models: List[str]
    message_ids: Optional[List[str]] = None


class SynthesisRequest(BaseModel):
    selected_messages: List[str]
    target_models: List[str]
    synthesis_prompt: str
