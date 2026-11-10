from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"
    APPROVED = "APPROVED"


class QuestionScore(BaseModel):
    question_id: str
    display_name: str
    obtained_marks: Optional[float] = Field(default=None, ge=0)
    max_marks: float = Field(..., gt=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_flagged: bool = False
    is_unrecognized: bool = False
    is_manually_edited: bool = False
    flag_reason: Optional[str] = None
    cell_box: Optional[List[int]] = None  # [x, y, w, h] bounding box in scan image


class EditHistoryEntry(BaseModel):
    field: str
    old_value: Any
    new_value: Any
    edited_by: str = "FAC001"
    timestamp: str
    reason: Optional[str] = None


class MarksRecordCreate(BaseModel):
    exam_id: str
    student_id: str
    scores: List[QuestionScore]
    scan_image_path: Optional[str] = None
    status: VerificationStatus = VerificationStatus.PENDING_REVIEW


class MarksRecordUpdate(BaseModel):
    scores: List[QuestionScore]
    status: Optional[VerificationStatus] = VerificationStatus.PENDING_REVIEW
    student_id: Optional[str] = None
    faculty_id: str = "FAC001"
    reason: Optional[str] = None
    notes: Optional[str] = None


class MarksRecordResponse(BaseModel):
    record_id: str
    exam_id: str
    student_id: str
    student_name: Optional[str] = "Unknown"
    scores: List[QuestionScore]
    total_obtained: Optional[float] = None
    total_max: float
    percentage: Optional[float] = None
    status: VerificationStatus
    scan_image_path: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    edit_history: List[EditHistoryEntry] = []
    created_at: str
    updated_at: str

