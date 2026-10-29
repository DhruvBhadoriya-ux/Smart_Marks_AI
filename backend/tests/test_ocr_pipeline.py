import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import db_instance, get_db
from app.services.image_processing import (
    preprocess_marks_strip,
    order_points,
    four_point_transform,
    detect_document_contour,
    load_image_from_bytes,
)
from app.services.ocr.base import OCRRawResult
from app.services.ocr.factory import get_ocr_engine
from app.services.ocr.mock_engine import MockOCREngine
from app.services.ocr.rapid_engine import RapidOCREngine
from app.services.marks_validator import align_and_validate_marks

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_db():
    db_instance.connect()
    yield


def create_synthetic_marksheet_image(include_text: bool = True) -> bytes:
    """Generate a clean synthetic marks strip image using OpenCV."""
    # White background image (400x300)
    img = np.ones((400, 300, 3), dtype=np.uint8) * 255

    # Draw border
    cv2.rectangle(img, (15, 15), (285, 385), (0, 0, 0), 2)

    if include_text:
        # Draw header
        cv2.putText(img, "ROLL: 2023CS0104", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        # Draw marks table rows
        cv2.putText(img, "Q1(a) : 4.5", (25, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(img, "Q1(b) : 3.0", (25, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(img, "Q2 : 8.0", (25, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(img, "Q3 : 9.5", (25, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(img, "TOTAL : 25.0", (25, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


def test_cv_preprocessing_pipeline():
    image_bytes = create_synthetic_marksheet_image()
    res = preprocess_marks_strip(image_bytes, output_dir="temp_scans")
    assert "processed_shape" in res
    assert "saved_image_path" in res
    assert "image_array" in res
    assert isinstance(res["image_array"], np.ndarray)
    assert res["processed_shape"][0] > 0
    assert res["processed_shape"][1] > 0


def test_four_point_transform_ordering():
    # Randomly ordered quadrilateral points
    pts = np.array([[200, 200], [0, 0], [200, 0], [0, 200]], dtype="float32")
    ordered = order_points(pts)
    # [top-left, top-right, bottom-right, bottom-left]
    assert np.allclose(ordered[0], [0, 0])
    assert np.allclose(ordered[1], [200, 0])
    assert np.allclose(ordered[2], [200, 200])
    assert np.allclose(ordered[3], [0, 200])


def test_swappable_ocr_factory():
    # Test Mock Engine
    mock_engine = get_ocr_engine("MOCK_OCR")
    assert isinstance(mock_engine, MockOCREngine)
    assert mock_engine.name == "MOCK_OCR_ENGINE"

    # Test Rapid Engine
    rapid_engine = get_ocr_engine("RAPID_OCR")
    assert isinstance(rapid_engine, RapidOCREngine)
    assert rapid_engine.name == "RAPID_OCR_ONNX"


def test_marks_validator_bounds_and_flags():
    configured_questions = [
        {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0},
        {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0},
        {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0},
        {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0},
    ]

    # Provide OCR tokens where:
    # Q1(a) = 4.5 (valid)
    # Q1(b) = 3.0 (valid)
    # Q2 = 14.0 (INVALID: exceeds max_marks 10.0)
    # Q3 = 8.0 with low confidence 0.40 (FLAGGED: low confidence)
    tokens = [
        OCRRawResult(text="STUDENT ROLL: 2023CS0104", confidence=0.98),
        OCRRawResult(text="Q1(a) 4.5", confidence=0.95),
        OCRRawResult(text="Q1(b) 3.0", confidence=0.92),
        OCRRawResult(text="Q2 14.0", confidence=0.94),
        OCRRawResult(text="Q3 8.0", confidence=0.40),
        OCRRawResult(text="TOTAL: 29.5", confidence=0.96),
    ]

    val_res = align_and_validate_marks(
        ocr_results=tokens,
        configured_questions=configured_questions,
        confidence_threshold=0.65
    )

    assert val_res["candidate_student_id"] == "2023CS0104"
    assert val_res["has_flags"] is True
    assert val_res["status"].value == "NEEDS_CORRECTION"

    # Check question-level flags
    scores_by_id = {s.question_id: s for s in val_res["scores"]}
    assert scores_by_id["Q1a"].is_flagged is False
    assert scores_by_id["Q1a"].obtained_marks == 4.5

    assert scores_by_id["Q1b"].is_flagged is False
    assert scores_by_id["Q1b"].obtained_marks == 3.0

    # Q2 should be flagged for exceeding max marks
    assert scores_by_id["Q2"].is_flagged is True
    assert "exceeds maximum allowed" in scores_by_id["Q2"].flag_reason

    # Q3 should be flagged for low confidence
    assert scores_by_id["Q3"].is_flagged is True
    assert "Low OCR confidence" in scores_by_id["Q3"].flag_reason


def test_ocr_process_endpoint_e2e():
    image_bytes = create_synthetic_marksheet_image()
    files = {"file": ("test_scan.jpg", image_bytes, "image/jpeg")}
    data = {
        "exam_id": "EXAM-2026-CS301-MID",
        "engine": "MOCK_OCR"
    }

    response = client.post("/api/v1/ocr/process", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()

    assert "record_id" in res_data
    assert res_data["exam_id"] == "EXAM-2026-CS301-MID"
    assert res_data["student_id"] == "2023CS0104"
    assert "scores" in res_data
    assert len(res_data["scores"]) == 4
    assert res_data["total_obtained"] == 25.0
    assert res_data["total_max"] == 30.0
    assert "scan_image_url" in res_data

    # Verify that the scan image can be fetched via HTTP
    img_res = client.get(res_data["scan_image_url"])
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/jpeg"

    # Verify that draft was stored in MongoDB
    db = get_db()
    saved = db.marks_records.find_one({"record_id": res_data["record_id"]})
    assert saved is not None
    assert saved["status"] in ("PENDING_REVIEW", "NEEDS_CORRECTION")
    assert saved["total_obtained"] == 25.0


def test_rapid_ocr_inference_on_synthetic_image():
    """Verify live RapidOCR inference with ONNXRuntime on synthetic text image."""
    engine = RapidOCREngine()
    assert engine.name == "RAPID_OCR_ONNX"

    # Create image with high-contrast text
    img = np.ones((100, 350, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Q1 5.0 Q2 10.0", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    results = engine.extract(img)
    assert isinstance(results, list)
    # Verify that tokens are returned with text and confidence
    for item in results:
        assert isinstance(item, OCRRawResult)
        assert item.confidence >= 0.0
        assert len(item.text) > 0
