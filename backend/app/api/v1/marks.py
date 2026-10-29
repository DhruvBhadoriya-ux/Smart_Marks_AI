from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.marks import (
    MarksRecordResponse,
    MarksRecordUpdate,
    VerificationStatus,
    QuestionScore,
    EditHistoryEntry
)

router = APIRouter(prefix="/marks", tags=["Marks Records & Faculty Verification"])


class ApproveRecordRequest(BaseModel):
    faculty_id: str = "FAC001"
    approval_notes: Optional[str] = None


class EditMarksFieldRequest(BaseModel):
    scores: List[QuestionScore]
    student_id: Optional[str] = None
    faculty_id: str = "FAC001"
    reason: Optional[str] = "Manual correction during faculty review"


@router.get("/{exam_id}", response_model=List[MarksRecordResponse])
def get_exam_marks_records(
    exam_id: str,
    status_filter: Optional[VerificationStatus] = None
):
    """List all marks records for an examination session with optional status filter."""
    db = get_db()
    query = {"exam_id": exam_id}
    if status_filter:
        query["status"] = status_filter.value

    cursor = db.marks_records.find(query).sort("created_at", -1)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(MarksRecordResponse(**doc))
    return results


@router.get("/record/{record_id}", response_model=MarksRecordResponse)
def get_marks_record(record_id: str):
    """Retrieve detailed marks record including original scan URL and edit audit trail."""
    db = get_db()
    doc = db.marks_records.find_one({"record_id": record_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marks record '{record_id}' was not found."
        )
    doc["_id"] = str(doc["_id"])
    return MarksRecordResponse(**doc)


@router.put("/record/{record_id}", response_model=MarksRecordResponse)
def update_marks_record(record_id: str, payload: EditMarksFieldRequest):
    """
    Update marks record fields with automatic delta computation and immutable audit history.
    Never silently overwrites values.
    """
    db = get_db()
    existing = db.marks_records.find_one({"record_id": record_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marks record '{record_id}' was not found."
        )

    now = datetime.now(timezone.utc).isoformat()
    old_scores = {s["question_id"]: s["obtained_marks"] for s in existing.get("scores", [])}
    edit_history = existing.get("edit_history", [])

    # Track modifications
    for new_s in payload.scores:
        old_val = old_scores.get(new_s.question_id)
        if old_val is not None and abs(old_val - new_s.obtained_marks) > 0.001:
            edit_history.append({
                "field": new_s.question_id,
                "old_value": old_val,
                "new_value": new_s.obtained_marks,
                "edited_by": payload.faculty_id,
                "timestamp": now,
                "reason": payload.reason
            })
            new_s.is_manually_edited = True

    # Recalculate totals
    total_obtained = round(sum(s.obtained_marks for s in payload.scores), 2)
    total_max = float(existing.get("total_max", 30.0))
    pct = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0

    student_id = payload.student_id or existing.get("student_id")
    student_doc = db.students.find_one({"student_id": student_id})
    student_name = student_doc.get("name") if student_doc else existing.get("student_name", "Unknown")

    update_fields = {
        "scores": [s.model_dump() for s in payload.scores],
        "student_id": student_id,
        "student_name": student_name,
        "total_obtained": total_obtained,
        "percentage": pct,
        "edit_history": edit_history,
        "updated_at": now
    }

    db.marks_records.update_one({"record_id": record_id}, {"$set": update_fields})

    # Log audit event
    db.audit_events.insert_one({
        "event_type": "MARKS_EDITED",
        "entity_type": "MARKS_RECORD",
        "entity_id": record_id,
        "description": f"Faculty {payload.faculty_id} edited scores for student {student_id}. New Total: {total_obtained}.",
        "user_id": payload.faculty_id,
        "timestamp": now,
        "metadata": {"edits_count": len(edit_history)}
    })

    updated_doc = db.marks_records.find_one({"record_id": record_id})
    updated_doc["_id"] = str(updated_doc["_id"])
    return MarksRecordResponse(**updated_doc)


@router.post("/record/{record_id}/approve", response_model=MarksRecordResponse)
def approve_marks_record(record_id: str, req: ApproveRecordRequest):
    """
    Explicit faculty approval endpoint.
    Transitions record to 'APPROVED' state, stamping faculty credentials and timestamp.
    """
    db = get_db()
    existing = db.marks_records.find_one({"record_id": record_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Marks record '{record_id}' was not found."
        )

    now = datetime.now(timezone.utc).isoformat()
    approval_update = {
        "status": VerificationStatus.APPROVED.value,
        "approved_by": req.faculty_id,
        "approved_at": now,
        "updated_at": now
    }

    db.marks_records.update_one({"record_id": record_id}, {"$set": approval_update})

    # Log audit event
    db.audit_events.insert_one({
        "event_type": "MARKS_APPROVED",
        "entity_type": "MARKS_RECORD",
        "entity_id": record_id,
        "description": f"Faculty {req.faculty_id} signed off on marks for {existing.get('student_id')} ({existing.get('total_obtained')}/{existing.get('total_max')} pts).",
        "user_id": req.faculty_id,
        "timestamp": now,
        "metadata": {
            "exam_id": existing.get("exam_id"),
            "student_id": existing.get("student_id"),
            "total_obtained": existing.get("total_obtained")
        }
    })

    updated_doc = db.marks_records.find_one({"record_id": record_id})
    updated_doc["_id"] = str(updated_doc["_id"])
    return MarksRecordResponse(**updated_doc)
