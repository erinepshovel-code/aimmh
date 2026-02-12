from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class A0IngestRequest(BaseModel):
    conversation_id: str
    title: str
    messages: List[Dict[str, Any]]
    global_context: Optional[str] = None
    model_roles: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class A0RouteRequest(BaseModel):
    message: str
    models: List[str]
