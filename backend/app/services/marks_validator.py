import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set

from app.services.ocr.base import OCRRawResult, BaseOCREngine
from app.schemas.marks import QuestionScore, VerificationStatus

logger = logging.getLogger("smartmarks.validator")

STUDENT_ID_PATTERNS = [
    r"(2[0-9O]{3}[A-Z]{2,4}[0-9OISZB]{3,6})",
    r"([0-9O]{2}[A-Z]{2,4}[0-9OISZB]{3,6})",
    r"([A-Z]{2,4}[0-9OISZB]{4,8})",
    r"(2[0-9O]{7,10})",
]


def clean_student_id_token(text: str) -> str:
    """Clean raw OCR text for student enrollment ID by stripping label prefixes and punctuation."""
    cleaned = re.sub(
        r"(?:ROLL|ENROLL(?:MENT)?|STUDENT|REG(?:ISTRATION)?|SEAT|ID|NO|NUMBER|#|:|\.)+",
        " ",
        text,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"[\s\-\/\:\.\_\(\)]+", "", cleaned).upper()
    return cleaned


def generate_student_id_variants(token: str) -> List[str]:
    """
    Generate normalized student ID variants based on common OCR character confusions:
    - 'O', 'Q', 'D' <-> '0'
    - 'I', 'l', '|' <-> '1'
    - 'Z' <-> '2'
    - 'S' <-> '5'
    - 'B' <-> '8'
    """
    variants = [token]

    # Year prefix 2O... -> 20...
    year_fixed = re.sub(r"^2[OQD](\d{2})", r"20\1", token)
    if year_fixed not in variants:
        variants.append(year_fixed)

    for base in [token, year_fixed]:
        # Typical university pattern: 4-digit year + 2-4 letter branch + 3-6 digit roll no
        m = re.match(r"^(2[0-9O]{3})([A-Z]{2,4}?)([0-9OISZB]{3,6})$", base)
        if m:
            year, branch, suffix = m.group(1), m.group(2), m.group(3)
            norm_year = "20" + year[2:].replace("O", "0")
            char_map = str.maketrans("OQDlIZSB", "00011258")
            norm_suffix = suffix.translate(char_map)
            candidate = norm_year + branch + norm_suffix
            if candidate not in variants:
                variants.append(candidate)

        # Pattern without year prefix, e.g. CS0104 or 23CS0104
        m2 = re.match(r"^([0-9O]{2})([A-Z]{2,4}?)([0-9OISZB]{3,6})$", base)
        if m2:
            yr, branch, suffix = m2.group(1), m2.group(2), m2.group(3)
            char_map = str.maketrans("OQDlIZSB", "00011258")
            norm_yr = yr.translate(char_map)
            norm_suffix = suffix.translate(char_map)
            candidate2 = norm_yr + branch + norm_suffix
            if candidate2 not in variants:
                variants.append(candidate2)

    return variants


def extract_candidate_student_id(
    ocr_results: List[OCRRawResult],
    header_ocr_results: Optional[List[OCRRawResult]] = None,
    registered_students: Optional[List[str]] = None,
) -> Tuple[Optional[str], float, Optional[int], bool]:
    """
    Scan OCR tokens for student roll number / enrollment identifier.
    Uses separate header crop OCR tokens when available, normalizes spaces and
    OCR character confusions, and validates against registered students.

    Returns: (candidate_id, confidence, token_index, was_normalized)
    """
    reg_set = set(s.upper() for s in (registered_students or []))

    # Priority 1: Check header tokens first if available, then full image tokens
    token_sources = []
    if header_ocr_results:
        token_sources.append(("header", header_ocr_results))
    token_sources.append(("full", ocr_results))

    # Pass 1: Direct substring check against known registered students in all tokens
    if reg_set:
        for source_name, tokens in token_sources:
            for i, token in enumerate(tokens):
                spaceless = re.sub(r"[\s\-\/\:\.\_\(\)]+", "", token.text.upper())
                for reg_id in reg_set:
                    if reg_id in spaceless:
                        return reg_id, max(token.confidence, 0.98), (i if source_name == "full" else None), False

    # Pass 2: Embedded regex pattern search with OCR confusion normalization
    for source_name, tokens in token_sources:
        for i, token in enumerate(tokens):
            upper_text = token.text.upper()
            spaceless = re.sub(r"[\s\-\/\:\.\_\(\)]+", "", upper_text)
            cleaned = re.sub(r"^(?:ROLL|ENROLL(?:MENT)?|STUDENT|REG(?:ISTRATION)?|SEAT|ID|NO|NUMBER|#)+", "", spaceless, flags=re.IGNORECASE)

            # Search in current token
            for target_str in ([cleaned, spaceless] if cleaned != spaceless else [spaceless]):
                for pattern in STUDENT_ID_PATTERNS:
                    m = re.search(pattern, target_str)
                    if m:
                        raw_candidate = m.group(1)
                        variants = generate_student_id_variants(raw_candidate)
                        # Check if any normalized variant matches a registered student
                        for v in variants:
                            if v in reg_set:
                                return v, max(token.confidence, 0.95), (i if source_name == "full" else None), (v != raw_candidate)
                        # If registered set was provided but none matched, still check if standalone valid
                        best_v = variants[-1] if len(variants) > 1 else variants[0]
                        return best_v, token.confidence, (i if source_name == "full" else None), (best_v != raw_candidate)

            # Check if this token is a label and next token has candidate
            if any(k in upper_text for k in ["ENROLL", "ROLL", "STUDENT", "REG NO", "SEAT", "ID"]):
                if i + 1 < len(tokens):
                    next_spaceless = re.sub(r"[\s\-\/\:\.\_\(\)]+", "", tokens[i + 1].text.upper())
                    next_cleaned = re.sub(r"^(?:ROLL|ENROLL(?:MENT)?|STUDENT|REG(?:ISTRATION)?|SEAT|ID|NO|NUMBER|#)+", "", next_spaceless, flags=re.IGNORECASE)
                    for target_next in ([next_cleaned, next_spaceless] if next_cleaned != next_spaceless else [next_spaceless]):
                        for pattern in STUDENT_ID_PATTERNS:
                            m = re.search(pattern, target_next)
                            if m:
                                raw_candidate = m.group(1)
                                variants = generate_student_id_variants(raw_candidate)
                                for v in variants:
                                    if v in reg_set:
                                        return v, max(tokens[i + 1].confidence, 0.95), (i + 1 if source_name == "full" else None), (v != raw_candidate)
                                best_v = variants[-1] if len(variants) > 1 else variants[0]
                                return best_v, tokens[i + 1].confidence, (i + 1 if source_name == "full" else None), (best_v != raw_candidate)

    return None, 0.0, None, False


def parse_numeric_score(text: str) -> Optional[float]:
    """Extract a numeric float score from recognized text, e.g. '4.5', '8/10', '0.5', '10'."""
    # Fraction format like "4.5/5" or "8/10"
    fraction_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*\d+", text)
    if fraction_match:
        try:
            return float(fraction_match.group(1))
        except ValueError:
            pass

    # Standard numbers like "4.5", "0.5", "10", "8.0"
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
            p1 = re.compile(rf"\b(?:Q|QUESTION)\s*[\.\-_]?\s*{num}(?![a-zA-Z0-9])", re.IGNORECASE)
            p2 = re.compile(rf"(?:^|\s){num}\s*[:\.\-=](?![a-zA-Z0-9])", re.IGNORECASE)
            patterns.extend([p1, p2])

    escaped_display = re.escape(q_display.strip())
    patterns.append(re.compile(rf"\b{escaped_display}\b", re.IGNORECASE))
    escaped_id = re.escape(q_id.strip())
    patterns.append(re.compile(rf"\b{escaped_id}\b", re.IGNORECASE))

    return patterns


def get_token_center(box: List[List[float]]) -> Tuple[float, float]:
    """Compute center (x, y) coordinates of an OCR bounding quadrilateral."""
    if not box or len(box) == 0:
        return 0.0, 0.0
    xs = [pt[0] for pt in box if len(pt) >= 2]
    ys = [pt[1] for pt in box if len(pt) >= 2]
    if not xs or not ys:
        return 0.0, 0.0
    return float(sum(xs) / len(xs)), float(sum(ys) / len(ys))


def align_and_validate_marks(
    ocr_results: List[OCRRawResult],
    configured_questions: List[Dict[str, Any]],
    header_ocr_results: Optional[List[OCRRawResult]] = None,
    table_data: Optional[Dict[str, Any]] = None,
    ocr_engine: Optional[BaseOCREngine] = None,
    registered_students: Optional[List[str]] = None,
    confidence_threshold: float = 0.65
) -> Dict[str, Any]:
    """
    Map OCR tokens to configured examination questions, validate bounds,
    and generate structured validation flags.

    Multi-strategy Extraction:
    - Strategy A: OpenCV morphological table cell grid association (Header row vs Marks row)
    - Strategy B: 2D spatial column alignment on tokens (Header label with number directly beneath it)
    - Strategy C: Inline / sequential token pattern matching

    Safety guarantee:
    - Unreadable marks remain None / null with is_unrecognized=True (never defaulted to 0.0).
    - Totals are only calculated when all required marks are present and valid numbers.
    """
    candidate_student_id, student_id_confidence, student_idx, was_normalized = extract_candidate_student_id(
        ocr_results=ocr_results,
        header_ocr_results=header_ocr_results,
        registered_students=registered_students
    )

    question_scores: List[QuestionScore] = []
    has_any_flags = False
    warning_messages: List[str] = []

    # Flag if student ID could not be identified
    if not candidate_student_id:
        has_any_flags = True
        warning_messages.append("Student enrollment ID could not be identified with confidence. Please select from registered students or enter manually.")
    else:
        if student_id_confidence < confidence_threshold:
            has_any_flags = True
            warning_messages.append(f"Student ID '{candidate_student_id}' has low OCR confidence ({round(student_id_confidence * 100)}%).")
        if was_normalized:
            warning_messages.append(f"Student ID was normalized from OCR text as '{candidate_student_id}'. Please confirm.")

    # Keep track of consumed tokens
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

    # -------------------------------------------------------------
    # STRATEGY A: OpenCV Table Cell Grid Association
    # If table_data has segmented cell rows (Row 0 = Headers, Row 1 = Marks)
    # -------------------------------------------------------------
    matched_by_cell: Dict[str, Dict[str, Any]] = {}
    scanned_total_found = None

    if table_data and table_data.get("table_found") and ocr_engine is not None:
        cell_rows = table_data.get("cell_rows", [])
        if len(cell_rows) >= 2:
            header_row = cell_rows[0]
            marks_row = cell_rows[1]

            # Recognize text in each header cell
            header_cell_texts = []
            for col_idx, cell in enumerate(header_row):
                cell_crop = cell["crop"]
                if cell_crop is not None and cell_crop.size > 0:
                    c_tokens = ocr_engine.extract(cell_crop)
                    cell_text = " ".join(t.text for t in c_tokens).strip()
                    header_cell_texts.append((col_idx, cell_text, cell["box"]))

            # Match header cells against configured questions
            for q in configured_questions:
                q_id = q["question_id"]
                q_disp = q.get("display_name", q_id)
                patterns = build_question_patterns(q_id, q_disp)

                for col_idx, h_text, h_box in header_cell_texts:
                    if any(p.search(h_text) for p in patterns):
                        # Corresponding marks cell in marks_row
                        if col_idx < len(marks_row):
                            m_cell = marks_row[col_idx]
                            m_tokens = ocr_engine.extract(m_cell["crop"])
                            if m_tokens:
                                best_token = max(m_tokens, key=lambda t: t.confidence)
                                score_val = parse_numeric_score(best_token.text)
                                if score_val is not None:
                                    matched_by_cell[q_id] = {
                                        "score": score_val,
                                        "confidence": best_token.confidence,
                                        "cell_box": m_cell["box"]
                                    }
                        break

            # Also check for TOTAL column in header row
            for col_idx, h_text, h_box in header_cell_texts:
                if "TOTAL" in h_text.upper() and col_idx < len(marks_row):
                    tot_tokens = ocr_engine.extract(marks_row[col_idx]["crop"])
                    if tot_tokens:
                        tot_score = parse_numeric_score(tot_tokens[0].text)
                        if tot_score is not None:
                            scanned_total_found = tot_score

    # Pre-compute token spatial centers for Strategy B
    token_centers = [get_token_center(t.box) for t in ocr_results]

    # Process each configured question
    for q in configured_questions:
        q_id = q["question_id"]
        q_display = q.get("display_name", q_id)
        max_marks = float(q["max_marks"])

        matched_score: Optional[float] = None
        matched_confidence: float = 0.0
        flag_reason: Optional[str] = None
        is_flagged = False
        is_unrecognized = False
        cell_box: Optional[List[int]] = None

        # 1. Check Strategy A (OpenCV Morphological Table Cell)
        if q_id in matched_by_cell:
            cell_data = matched_by_cell[q_id]
            matched_score = cell_data["score"]
            matched_confidence = cell_data["confidence"]
            cell_box = cell_data["cell_box"]

        # 2. Strategy B: 2D Spatial Column Alignment
        if matched_score is None:
            patterns = build_question_patterns(q_id, q_display)
            # Find question label token
            q_token_idx = None
            for i, token in enumerate(ocr_results):
                if i in consumed_indices:
                    continue
                if any(p.search(token.text) for p in patterns):
                    q_token_idx = i
                    break

            if q_token_idx is not None:
                qx, qy = token_centers[q_token_idx]
                # Look for numeric tokens positioned vertically below this question header
                cand_numbers = []
                for j, token in enumerate(ocr_results):
                    if j in consumed_indices or j == q_token_idx:
                        continue
                    num_val = parse_numeric_score(token.text)
                    if num_val is not None:
                        nx, ny = token_centers[j]
                        # Must be below question header in y, and aligned within column x-tolerance
                        if ny > qy and abs(nx - qx) < 70:
                            dist = abs(nx - qx) + 0.3 * (ny - qy)
                            cand_numbers.append((dist, j, num_val, token))

                if cand_numbers:
                    cand_numbers.sort(key=lambda item: item[0])
                    best_dist, best_idx, best_score, best_tok = cand_numbers[0]
                    matched_score = best_score
                    matched_confidence = best_tok.confidence
                    if best_tok.box and len(best_tok.box) >= 4:
                        xs = [pt[0] for pt in best_tok.box]
                        ys = [pt[1] for pt in best_tok.box]
                        cell_box = [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))]
                    consumed_indices.add(q_token_idx)
                    consumed_indices.add(best_idx)

        # 3. Strategy C: Inline Pattern & Sequential Next Token
        if matched_score is None:
            patterns = build_question_patterns(q_id, q_display)
            for i, token in enumerate(ocr_results):
                if i in consumed_indices:
                    continue
                matches_pattern = any(p.search(token.text) for p in patterns)
                if matches_pattern:
                    # Same token score
                    cleaned_text = token.text
                    for p in patterns:
                        cleaned_text = p.sub("", cleaned_text)
                    score_in_same = parse_numeric_score(cleaned_text)
                    if score_in_same is not None:
                        matched_score = score_in_same
                        matched_confidence = token.confidence
                        consumed_indices.add(i)
                        break

                    # Immediate sequential token
                    if i + 1 < len(ocr_results) and (i + 1) not in consumed_indices:
                        next_token = ocr_results[i + 1]
                        next_score = parse_numeric_score(next_token.text)
                        if next_score is not None:
                            matched_score = next_score
                            matched_confidence = next_token.confidence
                            consumed_indices.add(i)
                            consumed_indices.add(i + 1)
                            break

        # 4. Strict Validation (Requirement 7: Do not convert failed OCR to 0.0)
        if matched_score is None:
            is_flagged = True
            is_unrecognized = True
            flag_reason = f"Score for {q_display} was unreadable or missing. Please verify."
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
            is_unrecognized=is_unrecognized,
            is_manually_edited=False,
            flag_reason=flag_reason,
            cell_box=cell_box
        ))

    # Calculate totals ONLY if all question marks are present and valid numbers
    all_scored = all(qs.obtained_marks is not None for qs in question_scores)
    total_max = round(sum(float(q["max_marks"]) for q in configured_questions), 2)

    if all_scored:
        total_obtained = round(sum(float(qs.obtained_marks) for qs in question_scores if qs.obtained_marks is not None), 2)
        percentage = round((total_obtained / total_max * 100), 2) if total_max > 0 else 0.0
    else:
        total_obtained = None
        percentage = None
        has_any_flags = True
        warning_messages.append("One or more question marks are missing or unreadable. Totals can only be calculated once all scores are verified.")

    # Cross-check scanned total from tokens if not found via cell grid
    if scanned_total_found is None:
        for idx in total_token_indices:
            token = ocr_results[idx]
            upper = token.text.upper()
            parsed_t = parse_numeric_score(upper.replace("TOTAL", ""))
            if parsed_t is not None:
                scanned_total_found = parsed_t
                break

    if scanned_total_found is not None and total_obtained is not None:
        if abs(scanned_total_found - total_obtained) > 0.01:
            has_any_flags = True
            warning_messages.append(
                f"Scanned total ({scanned_total_found}) does not match question sum ({total_obtained})."
            )

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
