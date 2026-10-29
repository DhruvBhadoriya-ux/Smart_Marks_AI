import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from app.services.ocr.base import OCRRawResult
from app.schemas.marks import QuestionScore, VerificationStatus

logger = logging.getLogger("smartmarks.validator")

STUDENT_ID_PATTERNS = [
    r"\b(20\d{2}[A-Z]{2,4}\d{3,5})\b",
    r"\b(\d{2}[A-Z]{2,4}\d{3,5})\b",
    r"\b([A-Z]{2,4}\d{4,8})\b",
]


def extract_candidate_student_id(
    ocr_results: List[OCRRawResult]
) -> Tuple[Optional[str], float, Optional[int]]:
    """
    Scan OCR tokens for student roll number / enrollment identifier.
    Returns (candidate_id, confidence, token_index).
    """
    # 1. Search for explicit labels like "ROLL", "ENROLLMENT", "STUDENT ID", "REG NO"
    for i, token in enumerate(ocr_results):
        upper_text = token.text.upper()
        if any(k in upper_text for k in ["ENROLL", "ROLL", "STUDENT", "REG NO", "SEAT"]):
            for pattern in STUDENT_ID_PATTERNS:
                match = re.search(pattern, upper_text)
                if match:
                    return match.group(1), token.confidence, i

            if i + 1 < len(ocr_results):
                next_text = ocr_results[i + 1].text.upper()
                for pattern in STUDENT_ID_PATTERNS:
                    match = re.search(pattern, next_text)
                    if match:
                        return match.group(1), ocr_results[i + 1].confidence, i + 1

    # 2. General scan across all tokens
    for i, token in enumerate(ocr_results):
        upper_text = token.text.upper()
        for pattern in STUDENT_ID_PATTERNS:
            match = re.search(pattern, upper_text)
            if match:
                return match.group(1), token.confidence, i

    return None, 0.0, None


def parse_numeric_score(text: str) -> Optional[float]:
    """Extract a numeric float score from recognized text, e.g. '4.5', '8/10', '10'."""
    # Fraction format like "4.5/5" or "8/10"
    fraction_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*\d+", text)
    if fraction_match:
        try:
            return float(fraction_match.group(1))
        except ValueError:
            pass

    # Standard numbers like "4.5", "10", "8.0"
    # Find all numeric matches and return the last one (most often the mark)
    matches = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
    if matches:
        try:
            return float(matches[-1])
        except ValueError:
            pass

    return None


def build_question_patterns(q_id: str, q_display: str) -> List[re.Pattern]:
    """Compile regex patterns specifically tailored to match this question identifier."""
    patterns = []
    
    # Check for number and optional subquestion letter, e.g. '1(a)' or '1a' or '2'
    m = re.search(r"(\d+)\s*[\(\.\-_]?\s*([a-zA-Z])?", q_display) or re.search(r"(\d+)\s*[\(\.\-_]?\s*([a-zA-Z])?", q_id)
    if m:
        num, sub = m.group(1), m.group(2)
        if sub:
            # Subquestion like Q1(a), Q1a, 1(a), 1a
            p1 = re.compile(rf"\b(?:Q|QUESTION)?\s*{num}\s*[\(\.\-_]?\s*{sub}\s*[\)]?\b", re.IGNORECASE)
            patterns.append(p1)
        else:
            # Main question like Q1, Q2, Question 2
            # Must be preceded by 'Q' or 'Question' to avoid matching random numbers
            p1 = re.compile(rf"\b(?:Q|QUESTION)\s*[\.\-_]?\s*{num}(?![a-zA-Z0-9])", re.IGNORECASE)
            p2 = re.compile(rf"(?:^|\s){num}\s*[:\.\-=](?![a-zA-Z0-9])", re.IGNORECASE)
            patterns.extend([p1, p2])

    escaped_display = re.escape(q_display.strip())
    patterns.append(re.compile(rf"\b{escaped_display}\b", re.IGNORECASE))
    escaped_id = re.escape(q_id.strip())
    patterns.append(re.compile(rf"\b{escaped_id}\b", re.IGNORECASE))

    return patterns


def align_and_validate_marks(
    ocr_results: List[OCRRawResult],
    configured_questions: List[Dict[str, Any]],
    confidence_threshold: float = 0.65
) -> Dict[str, Any]:
    """
    Map OCR tokens to configured examination questions, validate bounds,
    and generate structured validation flags.
    """
    candidate_student_id, student_id_confidence, student_idx = extract_candidate_student_id(ocr_results)

    question_scores: List[QuestionScore] = []
    has_any_flags = False
    warning_messages: List[str] = []

    # Flag if student ID could not be identified
    if not candidate_student_id:
        has_any_flags = True
        warning_messages.append("Student enrollment ID could not be identified with confidence. Manual entry required.")
    elif student_id_confidence < confidence_threshold:
        warning_messages.append(f"Student ID '{candidate_student_id}' has low OCR confidence ({round(student_id_confidence * 100)}%).")

    # Keep track of consumed tokens so they are not reused
    consumed_indices: Set[int] = set()
    if student_idx is not None:
        consumed_indices.add(student_idx)

    # Exclude explicit "TOTAL" tokens from individual question matching
    total_token_indices: Set[int] = set()
    for i, token in enumerate(ocr_results):
        upper = token.text.upper()
        if "TOTAL" in upper and not any(k in upper for k in ["MAX", "OUT OF"]):
            total_token_indices.add(i)
            consumed_indices.add(i)

    # Process each configured question
    for q in configured_questions:
        q_id = q["question_id"]
        q_display = q.get("display_name", q_id)
        max_marks = float(q["max_marks"])

        patterns = build_question_patterns(q_id, q_display)

        matched_score: Optional[float] = None
        matched_confidence: float = 0.0
        flag_reason: Optional[str] = None
        is_flagged = False

        # Search available OCR tokens
        for i, token in enumerate(ocr_results):
            if i in consumed_indices:
                continue

            # Check if token matches any question pattern
            matches_pattern = any(p.search(token.text) for p in patterns)

            if matches_pattern:
                # 1. Check if score is within this same token (e.g. "Q1(a) : 4.5" or "Q2 14.0")
                # Remove the question display / id prefix and search for number
                cleaned_text = token.text
                for p in patterns:
                    cleaned_text = p.sub("", cleaned_text)

                score_in_same = parse_numeric_score(cleaned_text)
                if score_in_same is not None:
                    matched_score = score_in_same
                    matched_confidence = token.confidence
                    consumed_indices.add(i)
                    break

                # 2. Check subsequent token (e.g. token[i] is "Q1(a)" and token[i+1] is "4.5")
                if i + 1 < len(ocr_results) and (i + 1) not in consumed_indices:
                    next_token = ocr_results[i + 1]
                    next_score = parse_numeric_score(next_token.text)
                    if next_score is not None:
                        matched_score = next_score
                        matched_confidence = next_token.confidence
                        consumed_indices.add(i)
                        consumed_indices.add(i + 1)
                        break

        # Validation of matched score
        if matched_score is None:
            is_flagged = True
            flag_reason = f"Score for {q_display} was not detected automatically. Please enter manually."
            matched_score = 0.0
            matched_confidence = 0.0
        else:
            if matched_score < 0:
                is_flagged = True
                flag_reason = f"Invalid negative marks ({matched_score}) for {q_display}."
            elif matched_score > max_marks:
                is_flagged = True
                flag_reason = f"Extracted score ({matched_score}) exceeds maximum allowed ({max_marks}) for {q_display}."
            elif matched_confidence < confidence_threshold:
                is_flagged = True
                flag_reason = f"Low OCR confidence ({round(matched_confidence * 100)}%) for {q_display}. Verify against scan."

        if is_flagged:
            has_any_flags = True

        question_scores.append(QuestionScore(
            question_id=q_id,
            display_name=q_display,
            obtained_marks=matched_score,
            max_marks=max_marks,
            confidence=round(matched_confidence, 4),
            is_flagged=is_flagged,
            is_manually_edited=False,
            flag_reason=flag_reason
        ))

    # Calculate totals
    total_obtained = round(sum(qs.obtained_marks for qs in question_scores), 2)
    total_max = round(sum(float(q["max_marks"]) for q in configured_questions), 2)
    percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0

    # Cross-check scanned total
    scanned_total_found = None
    for idx in total_token_indices:
        token = ocr_results[idx]
        upper = token.text.upper()
        parsed_t = parse_numeric_score(upper.replace("TOTAL", ""))
        if parsed_t is not None:
            scanned_total_found = parsed_t
            if abs(scanned_total_found - total_obtained) > 0.01:
                has_any_flags = True
                warning_messages.append(
                    f"Scanned total ({scanned_total_found}) does not match question sum ({total_obtained})."
                )
            break

    status = VerificationStatus.NEEDS_CORRECTION if has_any_flags else VerificationStatus.PENDING_REVIEW

    return {
        "candidate_student_id": candidate_student_id or "UNKNOWN",
        "student_id_confidence": round(student_id_confidence, 4),
        "scores": question_scores,
        "total_obtained": total_obtained,
        "total_max": total_max,
        "percentage": percentage,
        "status": status,
        "has_flags": has_any_flags,
        "warning_messages": warning_messages,
        "scanned_total": scanned_total_found,
    }
