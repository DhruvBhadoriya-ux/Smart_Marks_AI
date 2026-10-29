# SmartMarks AI — System Architecture Specification

## 1. Executive Summary & Budget Objective
SmartMarks AI is designed to assist college faculty members in digitizing handwritten examination marks strips directly within the browser, validating question-wise marks against configured exam patterns, enabling side-by-side human-in-the-loop verification, and exporting approved records to formatted Excel workbooks and Microsoft OneDrive.

**Budget Strategy:** 
- $0 API and runtime cost for MVP.
- Open-source, local-first CV/OCR pipeline (OpenCV + RapidOCR/PaddleOCR on CPU/Apple Silicon).
- Free tier MongoDB Atlas (or local MongoDB fallback with zero configuration).
- Open-source openpyxl for Excel workbook generation.
- Free Microsoft Entra ID (Azure AD) app registration with MSAL & Microsoft Graph for OneDrive export.

---

## 2. System Architecture & Topology

```
+----------------------------------------------------------------------------------+
|                                 CLIENT TIER                                      |
|                                                                                  |
|   React + TypeScript + Vite + Tailwind CSS                                       |
|   - Browser Camera Scanner (MediaDevices API) + Image Crop/Perspective Preview   |
|   - Faculty Dashboard (Exam sessions, statistics, history)                       |
|   - Interactive Side-by-Side Verification Screen (Original scan vs extracted)   |
|   - Local XLSX Download & MSAL OneDrive Direct Integration                       |
+----------------------------------------------------------------------------------+
                                        │
                               HTTP / REST (JSON)
                                        ▼
+----------------------------------------------------------------------------------+
|                              BACKEND TIER (FastAPI)                              |
|                                                                                  |
|   - Auth & Session Manager (JWT, Role checking)                                  |
|   - Exam Session & Configuration Service (Pattern validation)                    |
|   - Computer Vision & OCR Pipeline:                                              |
|       * OpenCV: Grayscale, CLAHE, Deskew, Perspective Warp, Table Extraction     |
|       * RapidOCR / PaddleOCR: Digits, Question Labels, Enrollment ID             |
|       * Marks Validator: Pattern constraints, Subquestion bounds, Total check    |
|   - Excel Generator Service (openpyxl styled workbooks)                          |
|   - Microsoft Graph Adapter (OneDrive REST Upload)                               |
|   - Audit Logging Engine (Track all manual edits & approvals)                    |
+----------------------------------------------------------------------------------+
                                        │
                                  PyMongo Driver
                                        ▼
+----------------------------------------------------------------------------------+
|                                DATABASE TIER                                     |
|                                                                                  |
|   MongoDB Atlas / Local MongoDB                                                  |
|   Collections:                                                                   |
|   - users (Faculty profiles, credentials)                                        |
|   - subjects (Course codes, titles, departments)                                 |
|   - students (Roll numbers, names, semester, branch)                             |
|   - exams (Exam configurations, mid/end-sem, question trees)                      |
|   - marks_records (Extracted & approved marks, flags, edit audit history)        |
|   - audit_events (System audit trails)                                           |
+----------------------------------------------------------------------------------+
```

---

## 3. Data Flow & Processing Lifecycle

1. **Session Setup:**
   Faculty creates or chooses an Examination Session (e.g., `CS301 - Mid-Semester Exam, Spring 2026`).
   Faculty configures the question pattern (e.g., `Q1(a): 5, Q1(b): 5, Q2: 10, Q3: 10, Total: 30`).

2. **Acquisition & Preprocessing:**
   Faculty takes a photo using the webcam/mobile browser or uploads an image.
   OpenCV performs:
   - Resizing & color space conversion.
   - Adaptive thresholding & edge detection.
   - Contour detection to locate marks strip table borders.
   - 4-point perspective transform to rectify tilt.

3. **Inference & Structured Parsing:**
   The rectified image is passed to the OCR engine.
   Digits and labels are mapped to the configured question structure.
   Confidence scores are recorded per cell.

4. **Validation & Anomaly Detection:**
   Marks Validator flags:
   - Out of bounds (`score > max_marks`).
   - Unrecognized/missing characters.
   - Confidence < threshold (`0.65`).
   - Mismatch between sum of subquestions and reported section total.

5. **Human-in-the-Loop Review & Approval:**
   Faculty views the original scanned crop adjacent to parsed fields with high-contrast indicator badges (Valid, Warning, Unclear).
   Faculty can correct any field. Every edit is tracked in an edit log.
   Faculty clicks **"Approve Record"**.
   Approved state is committed to MongoDB. Unapproved records remain flagged as `DRAFT` or `PENDING_REVIEW`.

6. **Export:**
   - **Local Excel:** Formatted `.xlsx` file generated with headers, student metadata, question marks, and color-coded status.
   - **OneDrive Export:** Faculty signs in with Microsoft credentials; backend/frontend transmits the verified workbook to faculty OneDrive via Microsoft Graph API.

---

## 4. MongoDB Document Schemas

### 4.1. `exams`
```json
{
  "_id": "ObjectId",
  "exam_id": "EXAM-2026-CS301-MID",
  "faculty_id": "FAC001",
  "subject_code": "CS301",
  "subject_name": "Data Structures and Algorithms",
  "exam_type": "MID_SEMESTER", // MID_SEMESTER | END_SEMESTER
  "semester": 3,
  "academic_year": "2025-2026",
  "exam_date": "2026-11-15",
  "total_marks": 30.0,
  "questions": [
    {
      "question_id": "Q1a",
      "display_name": "Q1(a)",
      "max_marks": 5.0,
      "parent_question": "Q1"
    },
    {
      "question_id": "Q1b",
      "display_name": "Q1(b)",
      "max_marks": 5.0,
      "parent_question": "Q1"
    },
    {
      "question_id": "Q2",
      "display_name": "Q2",
      "max_marks": 10.0,
      "parent_question": null
    },
    {
      "question_id": "Q3",
      "display_name": "Q3",
      "max_marks": 10.0,
      "parent_question": null
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.2. `marks_records`
```json
{
  "_id": "ObjectId",
  "record_id": "REC-CS301-MID-2026-001",
  "exam_id": "EXAM-2026-CS301-MID",
  "student_id": "2023CS0104",
  "student_name": "Aarav Sharma",
  "status": "APPROVED", // PENDING_REVIEW | NEEDS_CORRECTION | APPROVED
  "scan_image_path": "uploads/scans/scan_rec_001.jpg",
  "scores": [
    {
      "question_id": "Q1a",
      "obtained_marks": 4.5,
      "max_marks": 5.0,
      "confidence": 0.94,
      "is_flagged": false,
      "is_manually_edited": false
    },
    {
      "question_id": "Q1b",
      "obtained_marks": 3.0,
      "max_marks": 5.0,
      "confidence": 0.88,
      "is_flagged": false,
      "is_manually_edited": false
    },
    {
      "question_id": "Q2",
      "obtained_marks": 8.0,
      "max_marks": 10.0,
      "confidence": 0.91,
      "is_flagged": false,
      "is_manually_edited": false
    },
    {
      "question_id": "Q3",
      "obtained_marks": 9.5,
      "max_marks": 10.0,
      "confidence": 0.62,
      "is_flagged": true,
      "is_manually_edited": true,
      "original_ocr_val": "9.0"
    }
  ],
  "total_obtained": 25.0,
  "total_max": 30.0,
  "approved_by": "FAC001",
  "approved_at": "ISODate",
  "edit_history": [
    {
      "field": "Q3",
      "old_value": 9.0,
      "new_value": 9.5,
      "edited_by": "FAC001",
      "timestamp": "ISODate",
      "reason": "Faculty verified handwriting stroke on scan"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

---

## 5. Security & Privacy Guarantees
1. **Human Sign-off Policy:** No marks record is eligible for final export unless `status == "APPROVED"` by authenticated faculty.
2. **Immutable Audit Trail:** All manual corrections append to an `edit_history` list containing user ID, timestamp, and field delta.
3. **No Credential Exposure:** Database strings, secret keys, and Azure OAuth client secrets are strictly backend environment variables.
4. **Duplicate Prevention:** Unique composite index on `(exam_id, student_id)` prevents accidental multiple submissions of the same student marksheet.

---

## 6. Implementation Phasing
- **Phase 1:** Environment setup, architecture, and project skeleton.
- **Phase 2:** FastAPI backend + React Vite frontend with live health check.
- **Phase 3:** MongoDB integration, exam configuration, and manual marks entry.
- **Phase 4:** Browser camera capture, OpenCV preprocessing, and OCR pipeline.
- **Phase 5:** Side-by-side extraction verification, correction, and approval workflow.
- **Phase 6:** Excel report generation with formatting & statistical summaries.
- **Phase 7:** MSAL authentication & OneDrive export via Microsoft Graph.
- **Phase 8:** Unit/integration tests, synthetic sample data, end-to-end demo validation.
