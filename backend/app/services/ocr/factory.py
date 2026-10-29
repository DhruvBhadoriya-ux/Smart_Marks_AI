import logging
from typing import Optional
from app.core.config import settings
from app.services.ocr.base import BaseOCREngine
from app.services.ocr.mock_engine import MockOCREngine
from app.services.ocr.rapid_engine import RapidOCREngine

logger = logging.getLogger("smartmarks.ocr.factory")

_engine_cache: dict = {}


def get_ocr_engine(engine_name: Optional[str] = None) -> BaseOCREngine:
    """
    Factory to retrieve or instantiate the configured OCR engine.
    Ensures OCR engines are easily swappable without changing application code.
    """
    target = (engine_name or settings.OCR_ENGINE).upper().strip()

    if target in _engine_cache:
        return _engine_cache[target]

    if target in ("RAPID_OCR", "RAPIDOCR", "RAPID_OCR_ONNX"):
        try:
            engine = RapidOCREngine()
            _engine_cache[target] = engine
            return engine
        except Exception as e:
            logger.warning(
                "Could not initialize RapidOCR engine (%s). Falling back to MockOCREngine.",
                str(e)
            )
            mock = MockOCREngine()
            _engine_cache[target] = mock
            return mock
    elif target in ("MOCK_OCR", "MOCK", "TEST"):
        mock = MockOCREngine()
        _engine_cache[target] = mock
        return mock
    else:
        logger.warning("Unrecognized OCR engine '%s'. Defaulting to RapidOCR.", target)
        try:
            engine = RapidOCREngine()
            _engine_cache[target] = engine
            return engine
        except Exception:
            mock = MockOCREngine()
            _engine_cache[target] = mock
            return mock


def reset_ocr_engine_cache() -> None:
    global _engine_cache
    _engine_cache = {}
