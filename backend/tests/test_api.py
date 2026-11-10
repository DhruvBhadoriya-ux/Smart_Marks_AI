import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import db_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    # Make sure DB is connected before tests run
    db_instance.connect()
    yield


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert data["database"]["status"] == "ok"


def test_dashboard_summary():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_exams" in data
    assert "total_students" in data
    assert "recent_exams" in data
    assert "recent_activities" in data
    assert data["total_exams"] >= 1
    assert data["total_students"] >= 1


def test_list_and_create_exam():
    # 1. List existing exams
    res = client.get("/api/v1/exams")
    assert res.status_code == 200
    exams = res.json()
    initial_count = len(exams)

    # 2. Create a new exam with subquestions Q1(a), Q1(b), Q2
    new_exam_payload = {
        "title": "Operating Systems Mid-Semester",
        "subject_code": "CS402",
        "subject_name": "Operating Systems",
        "exam_type": "MID_SEMESTER",
        "semester": 4,
        "academic_year": "2025-2026",
        "exam_date": "2026-11-20",
        "questions": [
            {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0, "parent_question": "Q1"},
            {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0, "parent_question": "Q1"},
            {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0, "parent_question": None},
            {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0, "parent_question": None}
        ]
    }
    create_res = client.post("/api/v1/exams", json=new_exam_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["total_marks"] == 30.0
    assert created["subject_code"] == "CS402"
    assert "exam_id" in created

    # 3. Fetch newly created exam by exam_id
    detail_res = client.get(f"/api/v1/exams/{created['exam_id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["exam_id"] == created["exam_id"]

    # 4. Verify count increased
    list_res = client.get("/api/v1/exams")
    assert len(list_res.json()) == initial_count + 1


def test_duplicate_question_id_validation():
    # Questions with duplicate IDs must be rejected by Pydantic validator
    invalid_payload = {
        "title": "Invalid Exam",
        "subject_code": "CS999",
        "subject_name": "Test Subject",
        "exam_type": "MID_SEMESTER",
        "semester": 1,
        "academic_year": "2025-2026",
        "exam_date": "2026-11-20",
        "questions": [
            {"question_id": "Q1", "display_name": "Q1", "max_marks": 10.0},
            {"question_id": "Q1", "display_name": "Q1 Duplicate", "max_marks": 10.0}
        ]
    }
    res = client.post("/api/v1/exams", json=invalid_payload)
    assert res.status_code == 422


def test_list_and_create_student():
    res = client.get("/api/v1/students")
    assert res.status_code == 200
    students = res.json()
    assert len(students) >= 1

    # Create new student
    student_payload = {
        "student_id": "2023CS0999",
        "name": "Kavya Singhania",
        "semester": 3,
        "branch": "Computer Science",
        "email": "kavya.s@college.edu"
    }
    create_res = client.post("/api/v1/students", json=student_payload)
    assert create_res.status_code == 201
    assert create_res.json()["student_id"] == "2023CS0999"

    # Search for this student
    search_res = client.get("/api/v1/students?search=Kavya")
    assert search_res.status_code == 200
    matches = search_res.json()
    assert len(matches) == 1
    assert matches[0]["name"] == "Kavya Singhania"


def test_recent_activity_logs():
    res = client.get("/api/v1/activity")
    assert res.status_code == 200
    activities = res.json()
    assert isinstance(activities, list)
    assert len(activities) > 0
    # Audit log structure verification
    assert "event_type" in activities[0]
    assert "timestamp" in activities[0]


def test_update_marks_record_and_approval():
    from app.core.database import get_db
    db = get_db()
    
    # Insert draft record with an unread score (None)
    record_id = "REC-TEST-UPD-001"
    draft_record = {
        "record_id": record_id,
        "exam_id": "EXAM-2026-CS301-MID",
        "student_id": "UNKNOWN",
        "student_name": "Unknown Student",
        "scores": [
            {"question_id": "Q1a", "display_name": "Q1(a)", "obtained_marks": None, "max_marks": 5.0, "confidence": 0.0, "is_flagged": True, "is_unrecognized": True, "is_manually_edited": False},
            {"question_id": "Q1b", "display_name": "Q1(b)", "obtained_marks": 4.0, "max_marks": 5.0, "confidence": 0.95, "is_flagged": False, "is_unrecognized": False, "is_manually_edited": False},
            {"question_id": "Q2", "display_name": "Q2", "obtained_marks": 8.0, "max_marks": 10.0, "confidence": 0.92, "is_flagged": False, "is_unrecognized": False, "is_manually_edited": False},
            {"question_id": "Q3", "display_name": "Q3", "obtained_marks": 9.0, "max_marks": 10.0, "confidence": 0.94, "is_flagged": False, "is_unrecognized": False, "is_manually_edited": False},
        ],
        "total_obtained": None,
        "total_max": 30.0,
        "percentage": None,
        "status": "NEEDS_CORRECTION",
        "edit_history": [],
        "created_at": "2026-10-29T12:00:00Z",
        "updated_at": "2026-10-29T12:00:00Z",
    }
    db.marks_records.update_one({"record_id": record_id}, {"$set": draft_record}, upsert=True)

    # 1. Update: Faculty provides student ID 2023CS0104 and fills in missing Q1(a) score: 4.5
    updated_scores = [
        {"question_id": "Q1a", "display_name": "Q1(a)", "obtained_marks": 4.5, "max_marks": 5.0, "confidence": 1.0, "is_flagged": False, "is_manually_edited": True},
        {"question_id": "Q1b", "display_name": "Q1(b)", "obtained_marks": 4.0, "max_marks": 5.0, "confidence": 0.95, "is_flagged": False, "is_manually_edited": False},
        {"question_id": "Q2", "display_name": "Q2", "obtained_marks": 8.0, "max_marks": 10.0, "confidence": 0.92, "is_flagged": False, "is_manually_edited": False},
        {"question_id": "Q3", "display_name": "Q3", "obtained_marks": 9.0, "max_marks": 10.0, "confidence": 0.94, "is_flagged": False, "is_manually_edited": False},
    ]
    update_payload = {
        "scores": updated_scores,
        "student_id": "2023CS0104",
        "faculty_id": "FAC001",
        "reason": "Faculty entered missing Q1(a) score and assigned student"
    }

    put_res = client.put(f"/api/v1/marks/record/{record_id}", json=update_payload)
    assert put_res.status_code == 200
    res_data = put_res.json()
    assert res_data["student_id"] == "2023CS0104"
    assert res_data["total_obtained"] == 25.5
    assert res_data["percentage"] == 85.0
    assert len(res_data["edit_history"]) >= 1

    # 2. Approve record
    appr_res = client.post(f"/api/v1/marks/record/{record_id}/approve", json={"faculty_id": "FAC001", "approval_notes": "All verified"})
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"
    assert appr_res.json()["approved_by"] == "FAC001"


def test_approve_rejected_if_incomplete_or_unknown_student():
    from app.core.database import get_db
    db = get_db()

    # Draft with UNKNOWN student
    rec_unknown = "REC-TEST-UNKNOWN-001"
    db.marks_records.update_one(
        {"record_id": rec_unknown},
        {"$set": {
            "record_id": rec_unknown,
            "exam_id": "EXAM-2026-CS301-MID",
            "student_id": "UNKNOWN",
            "scores": [{"question_id": "Q1a", "display_name": "Q1(a)", "obtained_marks": 5.0, "max_marks": 5.0}],
            "total_obtained": 5.0,
            "total_max": 5.0,
            "status": "NEEDS_CORRECTION",
            "created_at": "2026-10-29T12:00:00Z",
            "updated_at": "2026-10-29T12:00:00Z"
        }},
        upsert=True
    )

    res1 = client.post(f"/api/v1/marks/record/{rec_unknown}/approve", json={"faculty_id": "FAC001"})
    assert res1.status_code == 400
    assert "UNKNOWN" in res1.json()["detail"]

    # Draft with missing question mark
    rec_incomplete = "REC-TEST-INCOMPLETE-001"
    db.marks_records.update_one(
        {"record_id": rec_incomplete},
        {"$set": {
            "record_id": rec_incomplete,
            "exam_id": "EXAM-2026-CS301-MID",
            "student_id": "2023CS0105",
            "scores": [{"question_id": "Q1a", "display_name": "Q1(a)", "obtained_marks": None, "max_marks": 5.0}],
            "total_obtained": None,
            "total_max": 5.0,
            "status": "NEEDS_CORRECTION",
            "created_at": "2026-10-29T12:00:00Z",
            "updated_at": "2026-10-29T12:00:00Z"
        }},
        upsert=True
    )

    res2 = client.post(f"/api/v1/marks/record/{rec_incomplete}/approve", json={"faculty_id": "FAC001"})
    assert res2.status_code == 400
    assert "no marks assigned" in res2.json()["detail"]


def test_multiple_unknown_marks_records_coexistence():
    from app.core.database import get_db
    db = get_db()

    # Verify multiple records with UNKNOWN student for the same exam do not trigger DuplicateKeyError
    rec_a = {"record_id": "REC-UNK-A", "exam_id": "EXAM-2026-CS301-MID", "student_id": "UNKNOWN", "status": "NEEDS_CORRECTION"}
    rec_b = {"record_id": "REC-UNK-B", "exam_id": "EXAM-2026-CS301-MID", "student_id": "UNKNOWN", "status": "NEEDS_CORRECTION"}

    db.marks_records.insert_one(rec_a)
    db.marks_records.insert_one(rec_b)

    found_a = db.marks_records.find_one({"record_id": "REC-UNK-A"})
    found_b = db.marks_records.find_one({"record_id": "REC-UNK-B"})
    assert found_a is not None
    assert found_b is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



