from typing import List
from fastapi import APIRouter
from pymongo import DESCENDING

from app.core.database import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.exam import ExamResponse
from app.schemas.activity import AuditEventResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    db = get_db()

    total_exams = db.exams.count_documents({})
    total_students = db.students.count_documents({})
    total_records = db.marks_records.count_documents({})
    approved_records = db.marks_records.count_documents({"status": "APPROVED"})
    pending_records = total_records - approved_records

    # Recent exams
    recent_exams_cur = db.exams.find({}).sort("created_at", DESCENDING).limit(5)
    recent_exams: List[ExamResponse] = []
    for doc in recent_exams_cur:
        doc["_id"] = str(doc["_id"])
        doc["marks_count"] = db.marks_records.count_documents({"exam_id": doc.get("exam_id")})
        recent_exams.append(ExamResponse(**doc))

    # Recent activities
    recent_acts_cur = db.audit_events.find({}).sort("timestamp", DESCENDING).limit(8)
    recent_activities: List[AuditEventResponse] = []
    for doc in recent_acts_cur:
        doc["event_id"] = str(doc["_id"])
        recent_activities.append(AuditEventResponse(**doc))

    return DashboardSummaryResponse(
        total_exams=total_exams,
        total_students=total_students,
        total_records_processed=total_records,
        total_approved_records=approved_records,
        pending_verification_records=pending_records,
        recent_exams=recent_exams,
        recent_activities=recent_activities
    )
