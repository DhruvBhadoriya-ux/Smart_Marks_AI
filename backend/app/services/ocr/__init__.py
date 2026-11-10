"""OCR Service Package"""
from app.services.ocr.base import BaseOCREngine, OCRRawResult

OCRToken = OCRRawResult
from app.services.ocr.factory import get_ocr_engine

__all__ = ["BaseOCREngine", "OCRRawResult", "OCRToken", "get_ocr_engine"]

