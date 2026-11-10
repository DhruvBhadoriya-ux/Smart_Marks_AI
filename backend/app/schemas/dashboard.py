from typing import List
from pydantic import BaseModel
from app.schemas.exam import ExamResponse
from app.schemas.activity import AuditEventResponse


class DashboardSummaryResponse(BaseModel):
    total_exams: int
    total_students: int
    total_records_processed: int
    total_approved_records: int
    pending_verification_records: int
    recent_exams: List[ExamResponse]
    recent_activities: List[AuditEventResponse]
