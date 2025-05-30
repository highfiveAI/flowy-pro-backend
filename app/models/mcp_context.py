from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class UserContext(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    last_updated: Optional[str] = None  # ISO8601 문자열 등

class ContextUpdateRequest(BaseModel):
    user_id: str
    data: Dict[str, Any] 