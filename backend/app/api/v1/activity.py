from typing import List, Optional
from fastapi import APIRouter, Query
from pymongo import DESCENDING

from app.core.database import get_db
from app.schemas.activity import AuditEventResponse

router = APIRouter(prefix="/activity", tags=["Activity & Audit"])


@router.get("", response_model=List[AuditEventResponse])
def get_recent_activities(
    limit: int = Query(default=20, ge=1, le=100),
    entity_type: Optional[str] = None
):
    db = get_db()
    query = {}
    if entity_type:
        query["entity_type"] = entity_type.upper()

    cursor = db.audit_events.find(query).sort("timestamp", DESCENDING).limit(limit)
    activities = []
    for doc in cursor:
        doc["event_id"] = str(doc["_id"])
        activities.append(AuditEventResponse(**doc))
    return activities
