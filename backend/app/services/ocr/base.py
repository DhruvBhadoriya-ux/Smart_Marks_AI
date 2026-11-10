from abc import ABC, abstractmethod
from typing import List
import numpy as np
from pydantic import BaseModel, Field


class OCRRawResult(BaseModel):
    text: str = Field(..., description="Recognized string token")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR recognition confidence score")
    box: List[List[float]] = Field(
        default_factory=list,
        description="Bounding quadrilateral coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
    )


class BaseOCREngine(ABC):
    """Abstract interface for all swappable OCR engines (RapidOCR, PaddleOCR, Mock, Tesseract)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the human-readable identifier of the engine."""

    @abstractmethod
    def extract(self, image: np.ndarray) -> List[OCRRawResult]:
        """
        Accept an image as a numpy array (BGR or Grayscale) and return list of recognized OCRRawResults.
        """
