from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.marks import (
    MarksRecordResponse,
    VerificationStatus,
    QuestionScore
)

router = APIRouter(prefix="/marks", tags=["Marks Records & Faculty Verification"])


class ApproveRecordRequest(BaseModel):
    faculty_id: str = "FAC001"
    approval_notes: Optional[str] = None


class EditMarksFieldRequest(BaseModel):
    scores: List[QuestionScore]
    student_id: Optional[str] = None
    status: Optional[VerificationStatus] = None
    faculty_id: str = "FAC001"
    reason: Optional[str] = "Manual correction during faculty review"
    notes: Optional[str] = None


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
        val_changed = False
        if old_val is None and new_s.obtained_marks is not None:
            val_changed = True
        elif old_val is not None and new_s.obtained_marks is None:
            val_changed = True
        elif old_val is not None and new_s.obtained_marks is not None:
            val_changed = abs(float(old_val) - float(new_s.obtained_marks)) > 0.001

        if val_changed:
            edit_history.append({
                "field": new_s.question_id,
                "old_value": old_val,
                "new_value": new_s.obtained_marks,
                "edited_by": payload.faculty_id,
                "timestamp": now,
                "reason": payload.reason or payload.notes
            })
            new_s.is_manually_edited = True

    # Recalculate totals only if all scores are valid numbers
    all_scored = all(s.obtained_marks is not None for s in payload.scores)
    total_obtained = round(sum(float(s.obtained_marks) for s in payload.scores if s.obtained_marks is not None), 2) if all_scored else None
    total_max = float(existing.get("total_max", 30.0))
    pct = round((total_obtained / total_max * 100), 2) if (total_obtained is not None and total_max > 0) else None

    student_id = (payload.student_id or existing.get("student_id", "")).strip().upper()
    student_doc = db.students.find_one({"student_id": student_id})
    student_name = student_doc.get("name") if student_doc else existing.get("student_name", "Unknown")

    # Resolve record status: payload.status or infer from score completeness
    if payload.status:
        record_status = payload.status.value
    else:
        record_status = VerificationStatus.PENDING_REVIEW.value if all_scored else VerificationStatus.NEEDS_CORRECTION.value

    update_fields = {
        "scores": [s.model_dump() for s in payload.scores],
        "student_id": student_id,
        "student_name": student_name,
        "total_obtained": total_obtained,
        "percentage": pct,
        "status": record_status,
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

    # Validate that student ID is assigned and not UNKNOWN
    student_id = existing.get("student_id")
    if not student_id or student_id == "UNKNOWN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve marks record with UNKNOWN or missing Student ID. Please assign a valid student roll number first."
        )

    # Validate that all question scores have valid numeric marks
    for s in existing.get("scores", []):
        if s.get("obtained_marks") is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve marks record with unverified scores. Question '{s.get('display_name', s.get('question_id'))}' has no marks assigned."
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
