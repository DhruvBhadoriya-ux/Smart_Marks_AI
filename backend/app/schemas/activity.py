from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    event_id: Optional[str] = None
    event_type: str
    entity_type: str
    entity_id: str
    description: str
    user_id: str = "FAC001"
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
