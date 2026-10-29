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
