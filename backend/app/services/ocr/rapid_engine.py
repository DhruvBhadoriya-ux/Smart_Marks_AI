import logging
from typing import List
import numpy as np

from app.services.ocr.base import BaseOCREngine, OCRRawResult

logger = logging.getLogger("smartmarks.ocr.rapid")


class RapidOCREngine(BaseOCREngine):
    """
    High-performance, local offline OCR engine using RapidOCR (ONNXRuntime).
    Zero cloud cost, native ARM64 / Apple Silicon support.
    """

    def __init__(self):
        self._engine = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "RAPID_OCR_ONNX"

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
                self._initialized = True
                logger.info("RapidOCR (ONNXRuntime) initialized successfully.")
            except ImportError as e:
                logger.error("RapidOCR library is not installed: %s", str(e))
                raise RuntimeError(
                    "RapidOCR is not installed in the environment. Please run: pip install rapidocr-onnxruntime"
                ) from e
            except Exception as e:
                logger.error("Failed to initialize RapidOCR: %s", str(e))
                raise

    def extract(self, image: np.ndarray) -> List[OCRRawResult]:
        self._ensure_initialized()
        
        # RapidOCR returns: (result, elapse_list)
        if self._engine is None:
            return []

        try:
            results, _ = self._engine(image)
        except Exception as e:
            logger.error("RapidOCR extraction execution error: %s", str(e))
            return []

        if not results:
            return []

        parsed: List[OCRRawResult] = []
        for item in results:
            if len(item) >= 3:
                box, text, score = item[0], item[1], float(item[2])
                # Ensure box format is list of lists
                box_coords = [list(pt) for pt in box] if isinstance(box, (list, np.ndarray)) else []
                parsed.append(OCRRawResult(
                    text=str(text).strip(),
                    confidence=round(score, 4),
                    box=box_coords
                ))

        return parsed
