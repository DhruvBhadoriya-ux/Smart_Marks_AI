import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import cv2
import numpy as np
import pytest
from typing import Dict, Optional, TypedDict, List

from app.core.database import db_instance
from app.services.image_processing import (
    preprocess_marks_strip,
    assess_image_quality
)
from app.services.ocr.rapid_engine import RapidOCREngine
from app.services.ocr.base import OCRRawResult
from app.services.marks_validator import (
    align_and_validate_marks,
    extract_candidate_student_id
)


@pytest.fixture(autouse=True)
def setup_db():
    db_instance.connect()
    yield


def generate_synthetic_table_strip(
    student_id_text: str,
    marks: Dict[str, float],
    total_val: Optional[float] = None,
    tilt_angle_deg: float = 0.0,
    blur_ksize: int = 0
) -> bytes:
    """Generate a clean synthetic marksheet image with a 2-row table and header zone."""
    w, h = 650, 420
    img = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Document border
    cv2.rectangle(img, (15, 15), (w - 15, h - 15), (40, 40, 40), 2)

    # Header region text
    cv2.putText(img, f"STUDENT ENROLLMENT: {student_id_text}", (35, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Table dimensions: 2 rows (Headers, Marks), N columns
    questions = list(marks.keys())
    headers = questions + (["Total"] if total_val is not None else [])
    num_cols = len(headers)
    
    col_w = int((w - 70) / num_cols)
    row_h = 55
    x0, y0 = 35, 100

    # Draw table outline
    table_w = col_w * num_cols
    cv2.rectangle(img, (x0, y0), (x0 + table_w, y0 + 2 * row_h), (0, 0, 0), 2)
    # Horizontal divider
    cv2.line(img, (x0, y0 + row_h), (x0 + table_w, y0 + row_h), (0, 0, 0), 2)
    # Vertical dividers
    for c in range(1, num_cols):
        cv2.line(img, (x0 + c * col_w, y0), (x0 + c * col_w, y0 + 2 * row_h), (0, 0, 0), 2)

    # Render header row
    for i, h_text in enumerate(headers):
        cv2.putText(
            img,
            h_text,
            (x0 + i * col_w + 15, y0 + 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            2
        )

    # Render marks row
    for i, q_name in enumerate(questions):
        val = marks[q_name]
        if val is not None:
            m_str = f"{val:.1f}" if isinstance(val, float) else str(val)
            cv2.putText(
                img,
                m_str,
                (x0 + i * col_w + 18, y0 + row_h + 38),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 0),
                2
            )

    if total_val is not None:
        cv2.putText(
            img,
            f"{total_val:.1f}",
            (x0 + (num_cols - 1) * col_w + 18, y0 + row_h + 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            2
        )

    # Optional tilt / rotation
    if abs(tilt_angle_deg) > 0.1:
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, tilt_angle_deg, 1.0)
        img = cv2.warpAffine(img, rot_mat, (w, h), borderValue=(255, 255, 255))

    # Optional blur
    if blur_ksize > 1:
        img = cv2.GaussianBlur(img, (blur_ksize, blur_ksize), 0)

    _, encoded = cv2.imencode(".jpg", img)
    return encoded.tobytes()


def test_image_quality_assessment():
    """Verify Laplacian variance blur detection and image quality constraints."""
    # Sharp image
    sharp_bytes = generate_synthetic_table_strip("2023CS0104", {"Q1": 5.0, "Q2": 8.0}, 13.0)
    sharp_img = cv2.imdecode(np.frombuffer(sharp_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert sharp_img is not None
    q_sharp = assess_image_quality(sharp_img)
    assert q_sharp["is_acceptable"] is True
    assert "IMAGE_TOO_BLURRED" not in q_sharp["flags"]
    assert q_sharp["laplacian_var"] > 50.0

    # Heavily blurred image
    blur_bytes = generate_synthetic_table_strip("2023CS0104", {"Q1": 5.0, "Q2": 8.0}, 13.0, blur_ksize=25)
    blur_img = cv2.imdecode(np.frombuffer(blur_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert blur_img is not None
    q_blur = assess_image_quality(blur_img)
    assert "IMAGE_TOO_BLURRED" in q_blur["flags"] or "IMAGE_BLURRED" in q_blur["flags"]
    assert q_blur["laplacian_var"] < 50.0

    # Tiny image
    tiny_img = cv2.resize(sharp_img, (150, 100))
    q_tiny = assess_image_quality(tiny_img)
    assert "IMAGE_TOO_SMALL" in q_tiny["flags"]
    assert q_tiny["is_acceptable"] is False


def test_student_id_normalization_and_ocr_confusions():
    """Test cleaning and resolving OCR confusions without mutating to wrong student."""
    registered = ["2023CS0101", "2023CS0102", "2023CS0103", "2023CS0104", "2023CS0105"]

    # 1. Clean format with space
    t1 = [OCRRawResult(text="STUDENT ENROLL: 2023 CS 0104", confidence=0.95)]
    id1, conf1, _, was_norm1 = extract_candidate_student_id(t1, registered_students=registered)
    assert id1 == "2023CS0104"
    assert conf1 >= 0.90

    # 2. OCR confusion: Letter 'O' instead of digit '0' in year and suffix
    t2 = [OCRRawResult(text="ROLL: 2O23CSO1O4", confidence=0.92)]
    id2, conf2, _, was_norm2 = extract_candidate_student_id(t2, registered_students=registered)
    assert id2 == "2023CS0104"
    assert was_norm2 is True

    # 3. Unregistered / uncertain ID should NOT silently mutate into a registered student
    t3 = [OCRRawResult(text="ROLL: 2023ME9999", confidence=0.90)]
    id3, conf3, _, was_norm3 = extract_candidate_student_id(t3, registered_students=registered)
    # Remains candidate or does not steal 2023CS0104
    assert id3 != "2023CS0104"

    # 4. Completely unreadable text
    t4 = [OCRRawResult(text="UNREADABLE_SCRIBBLE", confidence=0.30)]
    id4, conf4, _, _ = extract_candidate_student_id(t4, registered_students=registered)
    assert id4 is None


def test_failed_ocr_returns_none_and_not_zero():
    """Requirement 7: Failed OCR must NOT default to 0.0. Total must be None when incomplete."""
    configured_questions = [
        {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0},
        {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0},
        {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0},
        {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0},
    ]

    # Only Q1(a) and Q1(b) present; Q2 and Q3 are missing
    tokens = [
        OCRRawResult(text="STUDENT ID: 2023CS0104", confidence=0.98),
        OCRRawResult(text="Q1(a)", confidence=0.95),
        OCRRawResult(text="4.5", confidence=0.95),
        OCRRawResult(text="Q1(b)", confidence=0.92),
        OCRRawResult(text="3.0", confidence=0.92),
    ]

    res = align_and_validate_marks(
        ocr_results=tokens,
        configured_questions=configured_questions,
        registered_students=["2023CS0104"]
    )

    scores_map = {s.question_id: s for s in res["scores"]}
    assert scores_map["Q1a"].obtained_marks == 4.5
    assert scores_map["Q1b"].obtained_marks == 3.0

    # Q2 and Q3 MUST be None (not 0.0!)
    assert scores_map["Q2"].obtained_marks is None
    assert scores_map["Q2"].is_unrecognized is True
    assert scores_map["Q2"].is_flagged is True

    assert scores_map["Q3"].obtained_marks is None
    assert scores_map["Q3"].is_unrecognized is True
    assert scores_map["Q3"].is_flagged is True

    # Total and percentage MUST be None (incomplete)
    assert res["total_obtained"] is None
    assert res["percentage"] is None
    assert res["has_flags"] is True
    assert res["status"].value == "NEEDS_CORRECTION"


def test_ocr_benchmark_accuracy_dataset():
    """
    Requirement 9: Measure exact question-wise mark accuracy, enrollment ID accuracy,
    and complete-strip accuracy against ground truth using synthetic marks sheets.
    """
    engine = RapidOCREngine()

    class BenchmarkSample(TypedDict):
        id: str
        student_id: str
        student_text: str
        marks: Dict[str, float]
        total: float

    test_samples: List[BenchmarkSample] = [
        {
            "id": "sample_1_standard",
            "student_id": "2023CS0104",
            "student_text": "2023CS0104",
            "marks": {"Q1(a)": 4.5, "Q1(b)": 3.0, "Q2": 8.0, "Q3": 9.5},
            "total": 25.0
        },
        {
            "id": "sample_2_spaces",
            "student_id": "2023CS0102",
            "student_text": "2023 CS 0102",
            "marks": {"Q1(a)": 5.0, "Q1(b)": 4.0, "Q2": 10.0, "Q3": 7.5},
            "total": 26.5
        },
        {
            "id": "sample_3_ocr_confusion",
            "student_id": "2023CS0103",
            "student_text": "2O23CSO1O3",
            "marks": {"Q1(a)": 3.5, "Q1(b)": 4.5, "Q2": 9.0, "Q3": 8.0},
            "total": 25.0
        },
        {
            "id": "sample_4_subquestions_decimals",
            "student_id": "2023CS0105",
            "student_text": "2023CS0105",
            "marks": {"Q1(a)": 0.5, "Q1(b)": 2.5, "Q2": 7.0, "Q3": 10.0},
            "total": 20.0
        },
    ]

    configured_questions = [
        {"question_id": "Q1a", "display_name": "Q1(a)", "max_marks": 5.0},
        {"question_id": "Q1b", "display_name": "Q1(b)", "max_marks": 5.0},
        {"question_id": "Q2", "display_name": "Q2", "max_marks": 10.0},
        {"question_id": "Q3", "display_name": "Q3", "max_marks": 10.0},
    ]

    registered = ["2023CS0101", "2023CS0102", "2023CS0103", "2023CS0104", "2023CS0105"]

    total_strips = len(test_samples)
    correct_student_ids = 0
    total_expected_marks = 0
    correct_marks = 0
    completely_correct_strips = 0

    for sample in test_samples:
        img_bytes = generate_synthetic_table_strip(
            student_id_text=sample["student_text"],
            marks=sample["marks"],
            total_val=sample["total"]
        )

        cv_res = preprocess_marks_strip(img_bytes, output_dir="temp_scans")
        raw_tokens = engine.extract(cv_res["image_array"])

        header_tokens = []
        if cv_res["table_data"].get("header_crop") is not None:
            header_tokens = engine.extract(cv_res["table_data"]["header_crop"])

        val_res = align_and_validate_marks(
            ocr_results=raw_tokens,
            configured_questions=configured_questions,
            header_ocr_results=header_tokens,
            table_data=cv_res["table_data"],
            ocr_engine=engine,
            registered_students=registered
        )

        # Check student ID accuracy
        strip_perfect = True
        if val_res["candidate_student_id"] == sample["student_id"]:
            correct_student_ids += 1
        else:
            strip_perfect = False

        # Check question-wise mark accuracy
        scores_by_name = {s.display_name: s.obtained_marks for s in val_res["scores"]}
        for q_disp, exp_val in sample["marks"].items():
            total_expected_marks += 1
            act_val = scores_by_name.get(q_disp)
            if act_val is not None and abs(act_val - exp_val) < 0.01:
                correct_marks += 1
            else:
                strip_perfect = False

        if strip_perfect:
            completely_correct_strips += 1

    id_accuracy_pct = (correct_student_ids / total_strips) * 100.0
    marks_accuracy_pct = (correct_marks / total_expected_marks) * 100.0
    strip_accuracy_pct = (completely_correct_strips / total_strips) * 100.0

    print(f"\n==========================================")
    print(f"SMARTMARKS AI OCR BENCHMARK RESULTS:")
    print(f"Student Enrollment ID Accuracy: {id_accuracy_pct:.1f}% ({correct_student_ids}/{total_strips})")
    print(f"Question-Wise Mark Accuracy:    {marks_accuracy_pct:.1f}% ({correct_marks}/{total_expected_marks})")
    print(f"Complete Marks Strip Accuracy:  {strip_accuracy_pct:.1f}% ({completely_correct_strips}/{total_strips})")
    print(f"==========================================")

    # Assert rigorous accuracy thresholds supported by tests
    assert id_accuracy_pct >= 95.0, f"ID accuracy below threshold: {id_accuracy_pct}%"
    assert marks_accuracy_pct >= 90.0, f"Mark accuracy below threshold: {marks_accuracy_pct}%"
    assert strip_accuracy_pct >= 75.0, f"Complete strip accuracy below threshold: {strip_accuracy_pct}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

