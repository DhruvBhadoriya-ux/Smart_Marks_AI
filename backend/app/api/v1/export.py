from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.excel_generator import generate_exam_excel_workbook
from app.services.ms_graph import ms_graph_service

router = APIRouter(prefix="/export", tags=["Excel & Cloud Export"])


class OneDriveUploadRequest(BaseModel):
    exam_id: str
    access_token: str
    only_approved: bool = True
    folder_name: str = "SmartMarks_AI"


@router.get("/preview/{exam_id}")
def get_export_preview(exam_id: str):
    """Provide statistics and readiness check before exporting examination records."""
    db = get_db()
    exam = db.exams.find_one({"exam_id": exam_id})
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session '{exam_id}' was not found."
        )

    total_records = db.marks_records.count_documents({"exam_id": exam_id})
    approved_records = db.marks_records.count_documents({"exam_id": exam_id, "status": "APPROVED"})
    pending_records = total_records - approved_records

    clean_sub = exam.get("subject_code", "EXAM").replace(" ", "_")
    exam_type = exam.get("exam_type", "MID").replace("MID_SEMESTER", "MidSem").replace("END_SEMESTER", "EndSem")
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suggested_filename = f"SmartMarks_{clean_sub}_{exam_type}_{date_str}.xlsx"

    return {
        "exam_id": exam_id,
        "subject_code": exam.get("subject_code"),
        "subject_name": exam.get("subject_name"),
        "exam_type": exam.get("exam_type"),
        "total_records": total_records,
        "approved_records": approved_records,
        "pending_records": pending_records,
        "questions_count": len(exam.get("questions", [])),
        "total_marks": exam.get("total_marks"),
        "suggested_filename": suggested_filename,
        "microsoft_integration_configured": ms_graph_service.is_configured
    }


@router.get("/excel/{exam_id}")
def download_excel_workbook(
    exam_id: str,
    only_approved: bool = Query(True, description="Filter for faculty-approved records only")
):
    """
    Download a formatted Excel (.xlsx) workbook directly from verified MongoDB records.
    Always available locally with zero external dependencies.
    """
    db = get_db()
    exam = db.exams.find_one({"exam_id": exam_id})
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session '{exam_id}' was not found."
        )

    # Fetch marks records
    query = {"exam_id": exam_id}
    if only_approved:
        query["status"] = "APPROVED"

    records = list(db.marks_records.find(query))
    if not records and only_approved:
        # Check if unapproved records exist
        total_existing = db.marks_records.count_documents({"exam_id": exam_id})
        if total_existing > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No approved marks records found for '{exam.get('subject_code')}'. {total_existing} unapproved draft records exist. Faculty review & approval is required before final export."
            )

    # Generate Excel workbook
    buffer, filename = generate_exam_excel_workbook(exam, records, only_approved=only_approved)

    # Log export audit event
    now = datetime.now(timezone.utc).isoformat()
    db.audit_events.insert_one({
        "event_type": "EXCEL_EXPORTED",
        "entity_type": "EXAM",
        "entity_id": exam_id,
        "description": f"Generated Excel workbook '{filename}' with {len(records)} records.",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {
            "only_approved": only_approved,
            "record_count": len(records),
            "filename": filename
        }
    })

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/onedrive/auth-url")
def get_onedrive_auth_url(state: Optional[str] = None):
    """Generate Microsoft Identity authorization URL for OneDrive sync."""
    return ms_graph_service.get_auth_url(state=state)


@router.post("/onedrive/token")
async def exchange_onedrive_token(
    code: str = Query(..., description="Authorization code returned by Microsoft redirect")
):
    """Exchange Microsoft authorization code for access token."""
    try:
        return await ms_graph_service.acquire_token_by_code(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/onedrive/upload")
async def upload_to_onedrive(req: OneDriveUploadRequest):
    """
    Generate the verified examination workbook and upload it directly
    into the faculty's Microsoft OneDrive account via Microsoft Graph API.
    """
    db = get_db()
    exam = db.exams.find_one({"exam_id": req.exam_id})
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination session '{req.exam_id}' was not found."
        )

    # Query records
    query = {"exam_id": req.exam_id}
    if req.only_approved:
        query["status"] = "APPROVED"

    records = list(db.marks_records.find(query))

    # Generate workbook bytes
    buffer, filename = generate_exam_excel_workbook(exam, records, only_approved=req.only_approved)
    content_bytes = buffer.getvalue()

    # Upload to OneDrive via Microsoft Graph
    try:
        result = await ms_graph_service.upload_workbook_to_onedrive(
            access_token=req.access_token,
            filename=filename,
            content_bytes=content_bytes,
            folder_name=req.folder_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to upload workbook to OneDrive: {str(e)}"
        )

    # Log audit event
    now = datetime.now(timezone.utc).isoformat()
    db.audit_events.insert_one({
        "event_type": "ONEDRIVE_UPLOADED",
        "entity_type": "EXAM",
        "entity_id": req.exam_id,
        "description": f"Uploaded Excel workbook '{filename}' to OneDrive folder '{req.folder_name}'.",
        "user_id": "FAC001",
        "timestamp": now,
        "metadata": {
            "onedrive_url": result.get("web_url"),
            "size_bytes": result.get("size_bytes"),
            "record_count": len(records)
        }
    })

    return {
        "success": True,
        "message": f"Workbook '{filename}' successfully saved to your OneDrive ({req.folder_name}).",
        "onedrive_result": result
    }
