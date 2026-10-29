import io
import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import db_instance, get_db
from app.services.excel_generator import generate_exam_excel_workbook
from app.services.ms_graph import ms_graph_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    db_instance.connect()
    db = get_db()

    # Insert verified/approved sample record
    sample_approved_record = {
        "record_id": "REC-CS301-TEST-APP1",
        "exam_id": "EXAM-2026-CS301-MID",
        "student_id": "2023CS0101",
        "student_name": "Aarav Sharma",
        "scores": [
            {"question_id": "Q1a", "display_name": "Q1(a)", "obtained_marks": 4.5, "max_marks": 5.0, "confidence": 0.95, "is_flagged": False, "is_manually_edited": False},
            {"question_id": "Q1b", "display_name": "Q1(b)", "obtained_marks": 4.0, "max_marks": 5.0, "confidence": 0.92, "is_flagged": False, "is_manually_edited": False},
            {"question_id": "Q2", "display_name": "Q2", "obtained_marks": 8.5, "max_marks": 10.0, "confidence": 0.94, "is_flagged": False, "is_manually_edited": False},
            {"question_id": "Q3", "display_name": "Q3", "obtained_marks": 9.0, "max_marks": 10.0, "confidence": 0.91, "is_flagged": False, "is_manually_edited": False},
        ],
        "total_obtained": 26.0,
        "total_max": 30.0,
        "percentage": 86.67,
        "status": "APPROVED",
        "scan_image_path": "temp_scans/test.jpg",
        "approved_by": "FAC001",
        "approved_at": "2026-11-16T10:00:00Z",
        "edit_history": [],
        "created_at": "2026-11-16T09:00:00Z",
        "updated_at": "2026-11-16T10:00:00Z"
    }

    db.marks_records.update_one(
        {"record_id": sample_approved_record["record_id"]},
        {"$set": sample_approved_record},
        upsert=True
    )
    yield


def test_openpyxl_workbook_generation():
    exam = {
        "exam_id": "EXAM-2026-CS301-MID",
        "subject_code": "CS301",
        "subject_name": "Data Structures and Algorithms",
        "exam_type": "MID_SEMESTER",
        "semester": 3,
        "academic_year": "2025-2026",
        "exam_date": "2026-11-15",
        "total_marks": 30.0,
        "questions": [
            {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0},
            {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0},
            {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0},
            {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0},
        ]
    }

    records = [
        {
            "student_id": "2023CS0101",
            "student_name": "Aarav Sharma",
            "status": "APPROVED",
            "scores": [
                {"question_id": "Q1a", "obtained_marks": 5.0},
                {"question_id": "Q1b", "obtained_marks": 4.5},
                {"question_id": "Q2", "obtained_marks": 9.0},
                {"question_id": "Q3", "obtained_marks": 8.5},
            ],
            "total_obtained": 27.0,
            "total_max": 30.0,
            "percentage": 90.0,
            "approved_by": "FAC001",
            "approved_at": "2026-11-16T10:00:00Z"
        }
    ]

    buffer, filename = generate_exam_excel_workbook(exam, records, only_approved=True)
    assert filename.startswith("SmartMarks_CS301_MidSem_")
    assert filename.endswith(".xlsx")

    # Load back with openpyxl to verify cell structure
    wb = openpyxl.load_workbook(buffer)
    ws = wb.active
    assert ws.title == "CS301_Marks"

    # Verify Title Banner
    assert "SMARTMARKS AI" in str(ws["A1"].value)

    # Verify Header row (row 7)
    header_values = [ws.cell(row=7, column=col).value for col in range(1, 12)]
    assert "S.No" in header_values
    assert "Student ID / Roll No" in header_values
    assert "Student Name" in header_values
    assert "Total Obtained" in header_values
    assert "Max Marks" in header_values

    # Verify Student data row (row 8)
    assert ws["B8"].value == "2023CS0101"
    assert ws["C8"].value == "Aarav Sharma"
    assert ws["D8"].value == 5.0  # Q1a
    assert ws["E8"].value == 4.5  # Q1b
    assert ws["H8"].value == 27.0  # Total Obtained


def test_export_preview_endpoint():
    res = client.get("/api/v1/export/preview/EXAM-2026-CS301-MID")
    assert res.status_code == 200
    data = res.json()

    assert data["exam_id"] == "EXAM-2026-CS301-MID"
    assert data["subject_code"] == "CS301"
    assert data["approved_records"] >= 1
    assert "suggested_filename" in data
    assert "microsoft_integration_configured" in data


def test_download_excel_endpoint_local():
    res = client.get("/api/v1/export/excel/EXAM-2026-CS301-MID?only_approved=true")
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    # Verify binary contains valid XLSX/ZIP magic bytes ('PK\x03\x04')
    content = res.content
    assert len(content) > 1000
    assert content[:4] == b"PK\x03\x04"


def test_onedrive_auth_url_and_fallback():
    res = client.get("/api/v1/export/onedrive/auth-url")
    assert res.status_code == 200
    data = res.json()
    assert "configured" in data
    # If not configured, should return fallback message
    if not data["configured"]:
        assert "not configured" in data.get("message", "").lower()
