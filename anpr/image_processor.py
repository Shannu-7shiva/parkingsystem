import cv2
import numpy as np
from typing import Tuple, Optional


class ImageProcessor:
    """Preprocesses cropped license plate images for high-accuracy OCR text extraction."""

    @staticmethod
    def preprocess_for_ocr(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Takes raw cropped license plate BGR image and applies:
        1. Resizing to standard optimal OCR height (approx 120-150px)
        2. Grayscale conversion
        3. Bilateral filter for edge-preserving noise reduction
        4. CLAHE contrast enhancement
        5. Otsu thresholding / Adaptive thresholding

        Returns:
            (enhanced_gray, thresholded_binary)
        """
        if image is None or image.size == 0:
            raise ValueError("Invalid empty image passed to preprocess_for_ocr")

        # 1. Resize if image is too small or too large
        h, w = image.shape[:2]
        target_height = 120
        aspect_ratio = w / float(h)
        target_width = int(target_height * aspect_ratio)

        resized = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

        # 2. Grayscale
        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized.copy()

        # 3. Bilateral filter: smooths textures while preserving sharp plate character edges
        denoised = cv2.bilateralFilter(gray, d=11, sigmaColor=17, sigmaSpace=17)

        # 4. Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # 5. Otsu thresholding
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # If majority of pixels are dark (black background / white text), invert
        white_pixels = np.sum(binary == 255)
        total_pixels = binary.size
        if white_pixels < (total_pixels * 0.45):
            binary = cv2.bitwise_not(binary)

        return enhanced, binary

    @staticmethod
    def deskew_plate(image: np.ndarray) -> np.ndarray:
        """Corrects slight tilt/skew in license plate bounding boxes."""
        if image is None or image.size == 0:
            return image

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50, minLineLength=image.shape[1] // 3, maxLineGap=10)

        if lines is not None and len(lines) > 0:
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(x2 - x1) > 10:
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    if abs(angle) < 30:  # Only subtle tilts
                        angles.append(angle)

            if angles:
                median_angle = float(np.median(angles))
                if abs(median_angle) > 1.5:
                    h, w = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    return rotated

        return image
