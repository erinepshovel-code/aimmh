from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class A0IngestRequest(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    global_context: Optional[str] = None
    model_roles: Optional[Dict[str, str]] = None
    context_mode: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class A0RouteRequest(BaseModel):
    message: str
    models: List[str]
