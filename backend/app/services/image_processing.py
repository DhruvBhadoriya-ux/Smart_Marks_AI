import os
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List
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


def assess_image_quality(image: np.ndarray) -> Dict[str, Any]:
    """
    Evaluate scan frame quality:
    - Laplacian variance for blur detection
    - Resolution constraints (reject / flag tiny images)
    - Mean illumination and exposure
    - Image contrast
    """
    h, w = image.shape[:2]
    flags: List[str] = []
    
    # Check minimum dimensions
    if w < 320 or h < 200:
        flags.append("IMAGE_TOO_SMALL")

    # Grayscale for statistical metrics
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # 1. Blur / Sharpness via Laplacian variance
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if laplacian_var < 20.0:
        flags.append("IMAGE_TOO_BLURRED")
    elif laplacian_var < 50.0:
        flags.append("IMAGE_BLURRED")

    # 2. Illumination / Brightness
    mean_brightness = float(np.mean(gray))
    if mean_brightness < 40.0:
        flags.append("IMAGE_TOO_DARK")
    elif mean_brightness > 245.0:
        flags.append("IMAGE_OVEREXPOSED")

    # 3. Contrast (Standard deviation of pixel intensities)
    contrast = float(np.std(gray))
    if contrast < 22.0:
        flags.append("IMAGE_LOW_CONTRAST")

    # Framing / Framing area check
    total_pixels = h * w
    if total_pixels < 60000:
        flags.append("IMAGE_FRAME_POOR")

    # Composite quality score between 0.0 and 1.0
    quality_score = 1.0
    if "IMAGE_TOO_BLURRED" in flags:
        quality_score -= 0.45
    elif "IMAGE_BLURRED" in flags:
        quality_score -= 0.20
    if "IMAGE_TOO_SMALL" in flags:
        quality_score -= 0.35
    if "IMAGE_TOO_DARK" in flags or "IMAGE_OVEREXPOSED" in flags:
        quality_score -= 0.25
    if "IMAGE_LOW_CONTRAST" in flags:
        quality_score -= 0.15

    quality_score = max(0.0, min(1.0, round(quality_score, 3)))
    is_acceptable = "IMAGE_TOO_BLURRED" not in flags and "IMAGE_TOO_SMALL" not in flags

    return {
        "is_acceptable": is_acceptable,
        "quality_score": quality_score,
        "flags": flags,
        "laplacian_var": round(laplacian_var, 2),
        "mean_brightness": round(mean_brightness, 2),
        "contrast": round(contrast, 2),
        "dimensions": [w, h],
    }


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

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

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
    
    # Try Canny edges
    edges = cv2.Canny(blurred, 40, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]

    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.15 * total_area or area > 0.98 * total_area:
            continue

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            return approx.reshape(4, 2)

    return None


def enhance_contrast_clahe(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE in LAB color space to enhance handwritten ink strokes."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def enhance_illumination_and_sharpness(image: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE contrast adjustment followed by subtle unsharp masking
    to sharpen pen strokes against uneven background paper illumination.
    """
    clahe_img = enhance_contrast_clahe(image)
    # Subtle unsharp mask: original + 0.3 * (original - gaussian)
    gaussian = cv2.GaussianBlur(clahe_img, (0, 0), 2.0)
    sharpened = cv2.addWeighted(clahe_img, 1.3, gaussian, -0.3, 0)
    return sharpened


def generate_image_variants(image: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Generate multiple processing variants for modular OCR engines:
    - enhanced: CLAHE + sharpened BGR
    - gray: Grayscale
    - adaptive_thresh: Clean binary threshold isolating ink strokes
    - otsu_thresh: Otsu global threshold
    """
    enhanced = enhance_illumination_and_sharpness(image)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 9
    )
    
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return {
        "original": image,
        "enhanced": enhanced,
        "gray": gray,
        "adaptive_thresh": adaptive_thresh,
        "otsu_thresh": otsu_thresh,
    }


def detect_table_and_cells(image: np.ndarray) -> Dict[str, Any]:
    """
    Detect table grid lines and segment individual cells using OpenCV morphology:
    - Horizontal line kernel
    - Vertical line kernel
    - Table grid mask
    - Cell contour segmentation into rows & columns
    - Header crop (student info) vs Marks Table crop
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Inverted adaptive threshold: lines & ink are white (255), background is black (0)
    inv_gray = cv2.bitwise_not(gray)
    thresh = cv2.adaptiveThreshold(
        inv_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2
    )

    # 1. Morphological kernels proportional to image dimensions
    h_kernel_len = max(15, int(w / 25))
    v_kernel_len = max(15, int(h / 25))
    
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))

    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel, iterations=2)
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel, iterations=2)

    table_grid = cv2.add(horizontal, vertical)

    # 2. Find table outer boundary
    contours, _ = cv2.findContours(table_grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    table_box: Optional[Tuple[int, int, int, int]] = None
    if contours:
        # Find largest contour by area
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for c in contours:
            tx, ty, tw, th = cv2.boundingRect(c)
            # Table must occupy at least 35% width and 15% height
            if tw > w * 0.35 and th > h * 0.15:
                table_box = (tx, ty, tw, th)
                break

    # 3. Separate header zone (student roll number/ID) from table
    header_crop: np.ndarray
    if table_box is not None and table_box[1] > 35:
        # Region above the table
        header_crop = image[0:table_box[1], 0:w]
    else:
        # Top 32% of marks strip
        header_crop = image[0:int(h * 0.32), 0:w]

    # 4. Extract individual cells if table grid exists
    cell_rows: List[List[Dict[str, Any]]] = []
    table_found = False

    if table_box is not None:
        tx, ty, tw, th = table_box
        table_crop = image[ty:ty+th, tx:tx+tw]
        
        # Dilate grid slightly to disconnect cell contents from borders
        dilated_grid = cv2.dilate(table_grid, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
        cell_mask = cv2.bitwise_not(dilated_grid)

        cell_contours, _ = cv2.findContours(cell_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        extracted_cells: List[Tuple[int, int, int, int]] = []
        
        for c in cell_contours:
            cx, cy, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            # Filter noise and outer table
            if (area > 500 and cw > 25 and ch > 15 
                    and cw < tw * 0.85 and ch < th * 0.85
                    and cx >= tx - 5 and cy >= ty - 5
                    and (cx + cw) <= (tx + tw + 10) and (cy + ch) <= (ty + th + 10)):
                extracted_cells.append((cx, cy, cw, ch))

        if len(extracted_cells) >= 4:
            table_found = True
            # Sort cells vertically by y
            extracted_cells.sort(key=lambda b: (b[1], b[0]))
            
            # Cluster cells into rows based on y coordinate overlap
            raw_rows: List[List[Tuple[int, int, int, int]]] = []
            for box in extracted_cells:
                bx, by, bw, bh = box
                matched_row = None
                for row in raw_rows:
                    avg_y = sum(b[1] for b in row) / len(row)
                    avg_h = sum(b[3] for b in row) / len(row)
                    if abs(by - avg_y) < avg_h * 0.45:
                        matched_row = row
                        break
                if matched_row is not None:
                    matched_row.append(box)
                else:
                    raw_rows.append([box])

            # Sort each row horizontally by x
            for r in raw_rows:
                r.sort(key=lambda b: b[0])

            # Convert to structured cell dictionaries with crop
            for row in raw_rows:
                row_items = []
                for cx, cy, cw, ch in row:
                    # Clip coordinates safely to image bounds
                    y1, y2 = max(0, cy), min(h, cy + ch)
                    x1, x2 = max(0, cx), min(w, cx + cw)
                    if y2 > y1 and x2 > x1:
                        cell_img = image[y1:y2, x1:x2]
                        row_items.append({
                            "box": [cx, cy, cw, ch],
                            "crop": cell_img
                        })
                if row_items:
                    cell_rows.append(row_items)
    else:
        table_crop = image[int(h * 0.28):h, 0:w]

    return {
        "table_found": table_found,
        "table_box": list(table_box) if table_box else None,
        "header_crop": header_crop,
        "table_crop": table_crop,
        "cell_rows": cell_rows,
    }


def preprocess_marks_strip(
    image_bytes: bytes,
    output_dir: str = "temp_scans",
    force_crop: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, Any]:
    """
    Comprehensive Computer Vision Preprocessing Pipeline:
    1. Decode raw bytes
    2. Assess scan quality (blur, small size, framing, illumination)
    3. Document boundary contour detection & 4-point perspective warp
    4. Contrast enhancement (CLAHE + unsharp masking)
    5. Table grid & cell boundary detection (OpenCV morphology)
    6. Multi-variant generation (enhanced, gray, adaptive-threshold)
    7. Save processed image for audit and side-by-side faculty verification
    """
    image = load_image_from_bytes(image_bytes)
    orig_h, orig_w = image.shape[:2]

    # 1. Quality Assessment
    quality = assess_image_quality(image)

    # 2. Perspective Rectification
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

    # 3. Enhance contrast, illumination and sharpness
    enhanced = enhance_illumination_and_sharpness(warped)

    # 4. Generate multi-variants
    variants = generate_image_variants(warped)

    # 5. Table & Cell Morphology Detection
    table_data = detect_table_and_cells(enhanced)

    # 6. Save rectified image for faculty side-by-side verification
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
        "image_array": enhanced,
        "variants": variants,
        "table_data": table_data,
        "quality": quality,
    }
