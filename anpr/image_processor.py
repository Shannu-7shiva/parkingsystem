import cv2
import numpy as np
from typing import Tuple, Dict, Any, List, Optional


class ImageProcessor:
    """
    Advanced Computer Vision & Preprocessing Pipeline for Indian License Plate ANPR.
    Implements padding expansion, 4-point quadrilateral perspective correction,
    deskewing, aspect-ratio preserving scaling, CLAHE contrast enhancement,
    bilateral filtering, adaptive thresholding, and multi-variant generation.
    """

    @staticmethod
    def crop_with_padding(
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        pad_x_pct: float = 0.08,
        pad_y_pct: float = 0.12
    ) -> np.ndarray:
        """
        Crops a detected plate region with adaptive safety padding to avoid clipping
        critical outer characters (such as state code letters 'T', 'A', 'D' or ending digits).
        """
        if frame is None or frame.size == 0:
            return np.array([], dtype=np.uint8)

        fh, fw = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)

        pad_x = int(bw * pad_x_pct)
        pad_y = int(bh * pad_y_pct)

        crop_x1 = max(0, x1 - pad_x)
        crop_y1 = max(0, y1 - pad_y)
        crop_x2 = min(fw, x2 + pad_x)
        crop_y2 = min(fh, y2 + pad_y)

        crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
        return crop.copy() if crop.size > 0 else frame[y1:y2, x1:x2].copy()

    @staticmethod
    def resize_keep_aspect(image: np.ndarray, target_height: int = 90) -> np.ndarray:
        """Resizes the plate image to a standard height while preserving exact aspect ratio."""
        if image is None or image.size == 0:
            return image
        h, w = image.shape[:2]
        if h == 0 or w == 0:
            return image
        scale = float(target_height) / float(h)
        target_width = max(1, int(round(w * scale)))
        interp = cv2.INTER_CUBIC if scale > 1.0 else cv2.INTER_AREA
        return cv2.resize(image, (target_width, target_height), interpolation=interp)

    @classmethod
    def correct_perspective_and_deskew(cls, image: np.ndarray) -> np.ndarray:
        """
        Detects plate boundary quadrilateral and applies 4-point perspective warp.
        If quadrilateral is not well-formed, falls back to Hough-line / minimum area deskewing.
        """
        if image is None or image.size == 0:
            return image

        h, w = image.shape[:2]
        if h < 20 or w < 40:
            return image

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

        # Step 1: Attempt 4-point quadrilateral perspective correction
        try:
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 40, 160)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Find largest contour by area
                largest_cnt = max(contours, key=cv2.contourArea)
                peri = cv2.arcLength(largest_cnt, True)
                approx = cv2.approxPolyDP(largest_cnt, 0.035 * peri, True)

                # Check if approximately a 4-point quadrilateral covering >= 40% of the image
                area = cv2.contourArea(largest_cnt)
                if len(approx) == 4 and (area > 0.35 * (w * h)):
                    pts = approx.reshape(4, 2).astype("float32")
                    # Order points: top-left, top-right, bottom-right, bottom-left
                    s = pts.sum(axis=1)
                    diff = np.diff(pts, axis=1)
                    ordered = np.zeros((4, 2), dtype="float32")
                    ordered[0] = pts[np.argmin(s)]        # Top-left
                    ordered[2] = pts[np.argmax(s)]        # Bottom-right
                    ordered[1] = pts[np.argmin(diff)]     # Top-right
                    ordered[3] = pts[np.argmax(diff)]     # Bottom-left

                    tl, tr, br, bl = ordered
                    width_top = np.linalg.norm(tr - tl)
                    width_bot = np.linalg.norm(br - bl)
                    max_w = max(int(width_top), int(width_bot))

                    height_right = np.linalg.norm(tr - br)
                    height_left = np.linalg.norm(tl - bl)
                    max_h = max(int(height_right), int(height_left))

                    # Standard plate aspect ratio verification
                    if max_h > 0 and 1.8 <= (max_w / float(max_h)) <= 6.5:
                        dst = np.array([
                            [0, 0],
                            [max_w - 1, 0],
                            [max_w - 1, max_h - 1],
                            [0, max_h - 1]
                        ], dtype="float32")
                        M = cv2.getPerspectiveTransform(ordered, dst)
                        warped = cv2.warpPerspective(image, M, (max_w, max_h), flags=cv2.INTER_CUBIC)
                        return warped
        except Exception:
            pass

        # Step 2: Fallback to Hough-line / Minimum Area Rect deskewing
        return cls._deskew_hough_lines(image, gray)

    @staticmethod
    def _deskew_hough_lines(image: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """Straightens subtle horizontal angle tilts using Hough transform."""
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            min_line = max(15, gray.shape[1] // 4)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=min_line, maxLineGap=12)

            if lines is not None and len(lines) > 0:
                angles = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(x2 - x1) > 10:
                        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                        if abs(angle) < 35.0:  # Ignore vertical edges
                            angles.append(angle)

                if angles:
                    median_angle = float(np.median(angles))
                    if abs(median_angle) > 1.2:
                        h, w = image.shape[:2]
                        center = (w // 2, h // 2)
                        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        rotated = cv2.warpAffine(
                            image, M, (w, h),
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE
                        )
                        return rotated
        except Exception:
            pass
        return image

    @classmethod
    def generate_preprocessing_variants(cls, plate_bgr: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Generates 5 specialized computer vision preprocessing variations for OCR evaluation:
        1. CLAHE Contrast Enhanced Grayscale (optimal for gradient text)
        2. Bilateral Denoised Grayscale (edge-preserving character smoothing)
        3. Adaptive Gaussian Thresholded Binary (optimal for shadows and lighting variation)
        4. Otsu Dual-Polarity Binary (optimal for crisp uniform lighting)
        5. Morphological Black-Hat Enhanced (isolates embossed characters on HSRP plates)
        """
        if plate_bgr is None or plate_bgr.size == 0:
            return {}

        # 1. Perspective deskew & aspect-ratio resize
        deskewed = cls.correct_perspective_and_deskew(plate_bgr)
        resized = cls.resize_keep_aspect(deskewed, target_height=90)

        # 2. Grayscale conversion
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized.copy()

        # 3. Bilateral filter (d=9, sigmaColor=75, sigmaSpace=75) preserves character edges while removing road grit
        bilateral = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

        # 4. Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        clahe_img = clahe.apply(bilateral)

        # 5. Adaptive Gaussian Thresholding (handles shadows across the plate)
        adaptive_thresh = cv2.adaptiveThreshold(
            clahe_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 8
        )
        # Ensure characters are dark on white background (standard for OCR)
        if np.mean(adaptive_thresh) < 127:
            adaptive_thresh = cv2.bitwise_not(adaptive_thresh)

        # 6. Otsu Global Binarization with Polarity Correction
        _, otsu_thresh = cv2.threshold(clahe_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(otsu_thresh) < 127:
            otsu_thresh = cv2.bitwise_not(otsu_thresh)

        # 7. Morphological Black-Hat (Extracts dark characters on light background)
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rect_kernel)
        blackhat_enhanced = cv2.add(gray, blackhat)
        blackhat_enhanced = clahe.apply(blackhat_enhanced)

        # 8. Unsharp Masking Sharpening Filter
        gaussian_blur = cv2.GaussianBlur(clahe_img, (0, 0), 2.0)
        sharpened = cv2.addWeighted(clahe_img, 1.5, gaussian_blur, -0.5, 0)

        return {
            "clahe": clahe_img,
            "adaptive_thresh": adaptive_thresh,
            "otsu": otsu_thresh,
            "blackhat": blackhat_enhanced,
            "sharpened": sharpened,
            "raw_deskewed": deskewed
        }

    @staticmethod
    def calculate_sharpness(image: np.ndarray) -> float:
        """Measures focus quality using Laplacian variance."""
        if image is None or image.size == 0:
            return 0.0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
