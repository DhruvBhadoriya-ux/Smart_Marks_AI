from typing import List, Optional
import numpy as np
from app.services.ocr.base import BaseOCREngine, OCRRawResult


class MockOCREngine(BaseOCREngine):
    """
    Deterministic mock engine for fast unit tests, synthetic evaluations,
    and fallback validation without neural network weights.
    """

    def __init__(self, predefined_results: Optional[List[OCRRawResult]] = None):
        self._predefined = predefined_results

    @property
    def name(self) -> str:
        return "MOCK_OCR_ENGINE"

    def set_predefined_results(self, results: List[OCRRawResult]) -> None:
        self._predefined = results

    def extract(self, image: np.ndarray) -> List[OCRRawResult]:
        if self._predefined is not None:
            return self._predefined

        # Default realistic student marks strip recognition
        return [
            OCRRawResult(text="STUDENT ENROLLMENT: 2023CS0104", confidence=0.96, box=[[10, 10], [280, 10], [280, 35], [10, 35]]),
            OCRRawResult(text="Q1(a)", confidence=0.92, box=[[15, 60], [60, 60], [60, 85], [15, 85]]),
            OCRRawResult(text="4.5", confidence=0.91, box=[[90, 60], [130, 60], [130, 85], [90, 85]]),
            OCRRawResult(text="Q1(b)", confidence=0.89, box=[[15, 95], [60, 95], [60, 120], [15, 120]]),
            OCRRawResult(text="3.0", confidence=0.88, box=[[90, 95], [130, 95], [130, 120], [90, 120]]),
            OCRRawResult(text="Q2", confidence=0.94, box=[[15, 130], [50, 130], [50, 155], [15, 155]]),
            OCRRawResult(text="8.0", confidence=0.93, box=[[90, 130], [130, 130], [130, 155], [90, 155]]),
            OCRRawResult(text="Q3", confidence=0.55, box=[[15, 165], [50, 165], [50, 190], [15, 190]]),
            OCRRawResult(text="9.5", confidence=0.58, box=[[90, 165], [130, 165], [130, 190], [90, 190]]),
            OCRRawResult(text="TOTAL: 25.0", confidence=0.95, box=[[15, 205], [140, 205], [140, 230], [15, 230]]),
        ]
