from datetime import datetime, timezone
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import DESCENDING

from app.core.database import get_db
from app.schemas.exam import ExamCreate, ExamResponse, ExamType

router = APIRouter(prefix="/exams", tags=["Examinations"])


@router.get("", response_model=List[ExamResponse])
def list_exams(
    exam_type: Optional[ExamType] = None,
    semester: Optional[int] = Query(None, ge=1, le=8),
    subject_code: Optional[str] = None
):
    db = get_db()
    query = {}
    if exam_type:
        query["exam_type"] = exam_type.value
    if semester:
        query["semester"] = semester
    if subject_code:
        query["subject_code"] = {"$regex": subject_code, "$options": "i"}

    cursor = db.exams.find(query).sort("created_at", DESCENDING)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # Count processed marks for this exam
        marks_count = db.marks_records.count_documents({"exam_id": doc.get("exam_id")})
        doc["marks_count"] = marks_count
        results.append(ExamResponse(**doc))
    return results


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(exam_in: ExamCreate):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Calculate total marks from question configurations
    calculated_total = round(sum(q.max_marks for q in exam_in.questions), 2)
    
    # Generate clean, human-readable unique exam ID
    clean_sub = exam_in.subject_code.upper().replace(" ", "")
    type_suffix = "MID" if exam_in.exam_type == ExamType.MID_SEMESTER else "END"
    short_hash = uuid.uuid4().hex[:5].upper()
    generated_exam_id = f"EXAM-{exam_in.academic_year[:4]}-{clean_sub}-{type_suffix}-{short_hash}"

    title = exam_in.title or f"{exam_in.subject_code} - {exam_in.exam_type.value.replace('_', ' ').title()}"

    exam_dict = {
        "exam_id": generated_exam_id,
        "title": title,
        "subject_code": exam_in.subject_code.upper().strip(),
        "subject_name": exam_in.subject_name.strip(),
        "exam_type": exam_in.exam_type.value,
        "semester": exam_in.semester,
        "academic_year": exam_in.academic_year,
        "exam_date": exam_in.exam_date,
        "total_marks": calculated_total,
        "created_by": "FAC001",
        "questions": [q.model_dump() for q in exam_in.questions],
        "created_at": now,
        "updated_at": now,
    }

    db.exams.insert_one(exam_dict)

    # Log audit event
    db.audit_events.insert_one({
        "event_type": "EXAM_CREATED",
        "entity_type": "EXAM",
        "entity_id": generated_exam_id,
        "description": f"Created exam '{title}' with {len(exam_in.questions)} questions (Total: {calculated_total} marks).",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {
            "subject_code": exam_dict["subject_code"],
            "exam_type": exam_dict["exam_type"],
            "total_marks": calculated_total
        }
    })

    exam_dict["marks_count"] = 0
    return ExamResponse(**exam_dict)


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: str):
    db = get_db()
    doc = db.exams.find_one({"exam_id": exam_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session with ID '{exam_id}' was not found."
        )
    doc["_id"] = str(doc["_id"])
    doc["marks_count"] = db.marks_records.count_documents({"exam_id": exam_id})
    return ExamResponse(**doc)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: str):
    db = get_db()
    existing = db.exams.find_one({"exam_id": exam_id})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session with ID '{exam_id}' was not found."
        )

    # Delete exam and its marks records
    db.exams.delete_one({"exam_id": exam_id})
    db.marks_records.delete_many({"exam_id": exam_id})

    now = datetime.now(timezone.utc).isoformat()
    db.audit_events.insert_one({
        "event_type": "EXAM_DELETED",
        "entity_type": "EXAM",
        "entity_id": exam_id,
        "description": f"Deleted examination '{existing.get('title', exam_id)}' and associated marks records.",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {"subject_code": existing.get("subject_code")}
    })
    return None
