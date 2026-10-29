import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import get_db
from app.services.image_processing import preprocess_marks_strip
from app.services.ocr.factory import get_ocr_engine
from app.services.marks_validator import align_and_validate_marks
from app.schemas.marks import MarksRecordResponse, VerificationStatus, QuestionScore

router = APIRouter(prefix="/ocr", tags=["Computer Vision & OCR"])


@router.post("/process")
async def process_marks_strip(
    file: UploadFile = File(..., description="Marksheet image file (JPG, PNG, WebP)"),
    exam_id: str = Form(..., description="Target examination identifier"),
    engine: Optional[str] = Form(None, description="Optional OCR engine override (RAPID_OCR, MOCK_OCR)"),
    student_id_override: Optional[str] = Form(None, description="Optional manual student roll number override")
):
    """
    Complete Examination Marks Digitization Pipeline:
    1. Retrieve and validate exam configuration
    2. OpenCV Preprocessing: document boundary detection, perspective warp, CLAHE enhancement
    3. OCR Token Extraction via selected engine
    4. Academic Pattern Alignment & Validation (bounds, totals, subquestions)
    5. Draft Record Persistence in MongoDB with audit logging
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Verify exam exists
    exam = db.exams.find_one({"exam_id": exam_id})
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session '{exam_id}' does not exist."
        )

    # 2. Read image bytes
    try:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise ValueError("Uploaded file is empty.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading uploaded image file: {str(e)}"
        )

    # 3. OpenCV Preprocessing & Rectification
    try:
        cv_result = preprocess_marks_strip(
            image_bytes=image_bytes,
            output_dir=settings.UPLOAD_DIR
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OpenCV image preprocessing failed: {str(e)}"
        )

    # 4. OCR Extraction
    ocr_engine = get_ocr_engine(engine)
    raw_tokens = ocr_engine.extract(cv_result["image_array"])

    # 5. Pattern Alignment & Bounds Validation
    validated = align_and_validate_marks(
        ocr_results=raw_tokens,
        configured_questions=exam.get("questions", []),
        confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD
    )

    # Use student override if provided, else extracted candidate
    effective_student_id = (student_id_override or validated["candidate_student_id"]).strip().upper()

    # Look up student name from directory if exists
    student_name = "Unknown Student"
    student_doc = db.students.find_one({"student_id": effective_student_id})
    if student_doc:
        student_name = student_doc.get("name", student_name)

    # 6. Generate Record ID and persist draft in MongoDB
    record_id = f"REC-{exam.get('subject_code', 'SUB')}-{uuid.uuid4().hex[:6].upper()}"

    record_doc = {
        "record_id": record_id,
        "exam_id": exam_id,
        "student_id": effective_student_id,
        "student_name": student_name,
        "scores": [s.model_dump() for s in validated["scores"]],
        "total_obtained": validated["total_obtained"],
        "total_max": validated["total_max"],
        "percentage": validated["percentage"],
        "status": validated["status"].value,
        "scan_image_path": cv_result["saved_image_path"],
        "scan_filename": cv_result["filename"],
        "approved_by": None,
        "approved_at": None,
        "edit_history": [],
        "created_at": now,
        "updated_at": now,
    }

    # Upsert to prevent duplicate import conflicts
    db.marks_records.update_one(
        {"exam_id": exam_id, "student_id": effective_student_id},
        {"$set": record_doc},
        upsert=True
    )

    # Log audit event
    db.audit_events.insert_one({
        "event_type": "MARKS_SCANNED",
        "entity_type": "MARKS_RECORD",
        "entity_id": record_id,
        "description": f"Processed marksheet for student {effective_student_id} ({exam.get('subject_code')}). Status: {validated['status'].value}.",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {
            "exam_id": exam_id,
            "ocr_engine": ocr_engine.name,
            "has_flags": validated["has_flags"],
            "total_obtained": validated["total_obtained"]
        }
    })

    return {
        "record_id": record_id,
        "exam_id": exam_id,
        "student_id": effective_student_id,
        "student_name": student_name,
        "scores": validated["scores"],
        "total_obtained": validated["total_obtained"],
        "total_max": validated["total_max"],
        "percentage": validated["percentage"],
        "status": validated["status"],
        "scan_image_path": cv_result["saved_image_path"],
        "scan_filename": cv_result["filename"],
        "scan_image_url": f"/api/v1/ocr/scans/{cv_result['filename']}",
        "ocr_engine": ocr_engine.name,
        "perspective_corrected": cv_result["perspective_corrected"],
        "has_flags": validated["has_flags"],
        "warning_messages": validated["warning_messages"],
        "raw_tokens_count": len(raw_tokens),
        "created_at": now
    }


@router.get("/scans/{filename}")
def get_scan_image(filename: str):
    """Retrieve scanned marks strip image for side-by-side faculty review."""
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scanned image file '{filename}' was not found."
        )
    return FileResponse(filepath, media_type="image/jpeg")
