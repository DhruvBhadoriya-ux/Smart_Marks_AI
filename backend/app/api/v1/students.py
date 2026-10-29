from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ASCENDING

from app.core.database import get_db
from app.schemas.student import StudentCreate, StudentResponse, StudentBatchImport

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=List[StudentResponse])
def list_students(
    search: Optional[str] = None,
    semester: Optional[int] = Query(None, ge=1, le=8),
    branch: Optional[str] = None
):
    db = get_db()
    query = {}
    if semester:
        query["semester"] = semester
    if branch:
        query["branch"] = {"$regex": branch, "$options": "i"}
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"student_id": search_regex},
            {"name": search_regex},
            {"email": search_regex}
        ]

    cursor = db.students.find(query).sort("student_id", ASCENDING)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(StudentResponse(**doc))
    return results


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_in: StudentCreate):
    db = get_db()
    clean_id = student_in.student_id.upper().strip()

    # Check for existing student ID
    existing = db.students.find_one({"student_id": clean_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student with ID '{clean_id}' already exists."
        )

    now = datetime.now(timezone.utc).isoformat()
    student_dict = {
        "student_id": clean_id,
        "name": student_in.name.strip(),
        "semester": student_in.semester,
        "branch": student_in.branch.strip(),
        "email": student_in.email.strip() if student_in.email else None,
        "created_at": now
    }

    db.students.insert_one(student_dict)

    # Log audit event
    db.audit_events.insert_one({
        "event_type": "STUDENT_REGISTERED",
        "entity_type": "STUDENT",
        "entity_id": clean_id,
        "description": f"Enrolled student {student_dict['name']} ({clean_id}) in Semester {student_dict['semester']}.",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {"branch": student_dict["branch"]}
    })

    return StudentResponse(**student_dict)


@router.post("/batch", response_model=List[StudentResponse], status_code=status.HTTP_201_CREATED)
def batch_import_students(batch: StudentBatchImport):
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    created = []

    for s in batch.students:
        clean_id = s.student_id.upper().strip()
        existing = db.students.find_one({"student_id": clean_id})
        if not existing:
            doc = {
                "student_id": clean_id,
                "name": s.name.strip(),
                "semester": s.semester,
                "branch": s.branch.strip(),
                "email": s.email.strip() if s.email else None,
                "created_at": now
            }
            db.students.insert_one(doc)
            created.append(StudentResponse(**doc))

    return created
