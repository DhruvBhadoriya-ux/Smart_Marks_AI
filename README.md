# SmartMarks AI — Examination Marks Digitization System

SmartMarks AI is a high-accuracy, human-in-the-loop web application designed to help academic faculty digitize handwritten examination marks strips. It combines browser camera capture, OpenCV document rectification, OCR, rule-based academic validation, a side-by-side verification UI, MongoDB persistence, and automated Excel / OneDrive export.

## Tech Stack
- **Frontend:** React 18 / 19, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Backend:** Python (FastAPI, Pydantic v2, PyMongo, OpenCV, RapidOCR/PaddleOCR, openpyxl, msal).
- **Database:** MongoDB Atlas (or local MongoDB).
- **Cloud Export:** Microsoft Graph API (OneDrive) via MSAL.

---

## Getting Started

### Prerequisites
- Node.js (v18+) & npm (v9+)
- Python (v3.10 - v3.11 recommended for arm64/Apple Silicon OCR support)
- MongoDB (Local instance or MongoDB Atlas URI)

### Quick Start
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd SMART_MARKS_AI
   ```
2. Configure environment:
   ```bash
   cp .env.example .env
   ```
3. Backend Setup:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
4. Frontend Setup:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Architectural Principles
- **Faculty Approval Rule:** OCR results are proposals only. Marks are never published or exported without explicit faculty sign-off.
- **Auditability:** Every correction to OCR proposals is permanently tracked in an audit log with timestamps.
- **Zero Paid Dependencies:** Designed to run with 100% free and open-source tools for minimal prototype budget.
