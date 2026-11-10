import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import get_db
from app.services.image_processing import preprocess_marks_strip
from app.services.ocr.factory import get_ocr_engine
from app.services.marks_validator import align_and_validate_marks

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

    # 2. Validate file type and read image bytes
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg", "image/bmp", "application/octet-stream"]
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file format '{file.content_type}'. Please upload a JPG, PNG, or WebP image."
        )

    try:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise ValueError("Uploaded image file is empty.")
        if len(image_bytes) > 15 * 1024 * 1024:
            raise ValueError("Uploaded image exceeds the 15MB maximum size limit.")
    except HTTPException:
        raise
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

    # Extract header tokens from dedicated crop if available
    table_data = cv_result.get("table_data", {})
    header_crop = table_data.get("header_crop")
    header_tokens = []
    if header_crop is not None and header_crop.size > 0:
        try:
            header_tokens = ocr_engine.extract(header_crop)
        except Exception:
            header_tokens = []

    # Retrieve registered students for this session / college directory
    registered_docs = list(db.students.find({}, {"student_id": 1, "name": 1, "_id": 0}))
    registered_ids = [d["student_id"] for d in registered_docs]

    # 5. Multi-Strategy Pattern Alignment & Bounds Validation
    validated = align_and_validate_marks(
        ocr_results=raw_tokens,
        configured_questions=exam.get("questions", []),
        header_ocr_results=header_tokens,
        table_data=table_data,
        ocr_engine=ocr_engine,
        registered_students=registered_ids,
        confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD
    )

    # Integrate image quality assessment flags
    quality = cv_result.get("quality", {})
    if quality.get("flags"):
        for q_flag in quality["flags"]:
            if q_flag == "IMAGE_TOO_BLURRED":
                validated["has_flags"] = True
                validated["warning_messages"].insert(0, "Image is heavily blurred. Accuracy is degraded; retake recommended.")
            elif q_flag == "IMAGE_BLURRED":
                validated["has_flags"] = True
                validated["warning_messages"].insert(0, "Image has mild blur / soft focus. Please verify extracted marks against scan.")
            elif q_flag == "IMAGE_TOO_SMALL":
                validated["has_flags"] = True
                validated["warning_messages"].insert(0, "Image resolution is low. Position camera closer to marks strip.")
            elif q_flag == "IMAGE_TOO_DARK":
                validated["warning_messages"].append("Low ambient lighting detected. Ensure even document illumination.")

    # Use student override if provided, else extracted candidate
    override = student_id_override.strip().upper() if student_id_override and student_id_override.strip() else None
    effective_student_id = override or validated.get("candidate_student_id") or "UNKNOWN"

    # Look up student name from directory if exists
    student_name = "Unknown Student"
    student_doc = db.students.find_one({"student_id": effective_student_id})
    if student_doc:
        student_name = student_doc.get("name", student_name)

    # 6. Generate Record ID and persist draft in MongoDB
    record_id = f"REC-{exam.get('subject_code', 'SUB')}-{uuid.uuid4().hex[:6].upper()}"

    # If student is already scanned for this exam, reuse their record_id and original created_at
    existing_record = db.marks_records.find_one({"exam_id": exam_id, "student_id": effective_student_id}) if effective_student_id != "UNKNOWN" else None
    if existing_record:
        record_id = existing_record.get("record_id", record_id)

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
        "edit_history": existing_record.get("edit_history", []) if existing_record else [],
        "created_at": existing_record.get("created_at", now) if existing_record else now,
        "updated_at": now,
    }

    # Upsert to prevent duplicate import conflicts (or insert if student ID is UNKNOWN)
    if existing_record:
        db.marks_records.update_one(
            {"_id": existing_record["_id"]},
            {"$set": record_doc}
        )
    elif effective_student_id != "UNKNOWN":
        db.marks_records.update_one(
            {"exam_id": exam_id, "student_id": effective_student_id},
            {"$set": record_doc},
            upsert=True
        )
    else:
        db.marks_records.insert_one(record_doc)

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
        "table_detected": table_data.get("table_found", False),
        "quality_assessment": quality,
        "registered_students": registered_docs,
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
