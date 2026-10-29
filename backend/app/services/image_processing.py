import os
import uuid
import logging
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("smartmarks.cv")


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode raw bytes into an OpenCV BGR image matrix."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes. Unsupported or corrupted image file.")
    return img


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order quadrilateral points clockwise:
    [top-left, top-right, bottom-right, bottom-left]
    """
    rect = np.zeros((4, 2), dtype="float32")

    # Top-left has smallest sum (x + y), bottom-right has largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Top-right has smallest diff (y - x), bottom-left has largest diff
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Perform a perspective warp to rectify document angle and tilt."""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Width of the new image
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    # Height of the new image
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    transform_matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))
    return warped


def detect_document_contour(image: np.ndarray) -> Optional[np.ndarray]:
    """
    Detect the 4-point bounding contour of a marks strip/page in an image.
    Returns 4-point polygon if found with sufficient area, else None.
    """
    h, w = image.shape[:2]
    total_area = h * w

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Adaptive edge detection
    edges = cv2.Canny(blurred, 40, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    for c in contours:
        area = cv2.contourArea(c)
        # Bounding contour must be at least 15% of total frame
        if area < 0.15 * total_area:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            return approx.reshape(4, 2)

    return None


def enhance_contrast_clahe(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE in LAB color space to enhance handwritten ink strokes."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def preprocess_marks_strip(
    image_bytes: bytes,
    output_dir: str = "temp_scans",
    force_crop: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, Any]:
    """
    Full Computer Vision Preprocessing Pipeline:
    1. Decode raw bytes
    2. Document boundary contour detection
    3. Perspective rectification (warp)
    4. CLAHE contrast enhancement
    5. Save processed image for audit and side-by-side verification
    """
    image = load_image_from_bytes(image_bytes)
    orig_h, orig_w = image.shape[:2]

    # Check if manual crop coords provided [ymin, xmin, ymax, xmax]
    perspective_corrected = False
    if force_crop is not None:
        y1, x1, y2, x2 = force_crop
        warped = image[max(0, y1):min(orig_h, y2), max(0, x1):min(orig_w, x2)]
    else:
        doc_contour = detect_document_contour(image)
        if doc_contour is not None:
            try:
                warped = four_point_transform(image, doc_contour)
                perspective_corrected = True
            except Exception as e:
                logger.warning("Perspective transform failed: %s. Using original crop.", str(e))
                warped = image
        else:
            warped = image

    # Apply contrast enhancement
    enhanced = enhance_contrast_clahe(warped)

    # Save to disk for faculty verification view
    os.makedirs(output_dir, exist_ok=True)
    scan_id = f"scan_{uuid.uuid4().hex[:10]}.jpg"
    save_path = os.path.join(output_dir, scan_id)
    cv2.imwrite(save_path, enhanced)

    return {
        "original_shape": [orig_h, orig_w],
        "processed_shape": [enhanced.shape[0], enhanced.shape[1]],
        "perspective_corrected": perspective_corrected,
        "saved_image_path": save_path,
        "filename": scan_id,
        "image_array": enhanced
    }
