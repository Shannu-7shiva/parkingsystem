import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import config

logger = logging.getLogger("anpr.plate_detector")

_plate_yolo_model = None
_plate_model_attempted = False


def get_plate_yolo_model():
    """Attempts to load custom trained YOLO license plate detection weights if available in models/."""
    global _plate_yolo_model, _plate_model_attempted
    if _plate_model_attempted:
        return _plate_yolo_model

    _plate_model_attempted = True
    candidates = [
        config.MODEL_DIR / "license_plate_detector.pt",
        config.MODEL_DIR / "plate_detector.pt",
        config.MODEL_DIR / "best.pt",
    ]

    for model_path in candidates:
        if model_path.exists():
            try:
                from ultralytics import YOLO
                _plate_yolo_model = YOLO(str(model_path))
                logger.info(f"Loaded custom license plate YOLO model from {model_path}")
                return _plate_yolo_model
            except Exception as e:
                logger.warning(f"Could not load plate model from {model_path}: {e}")

    logger.info("No custom plate YOLO model found in models/. Using OpenCV morphological plate detector.")
    return None


class PlateDetector:
    """Detects and crops vehicle number plates using YOLO weights or OpenCV morphological localization."""

    @classmethod
    def detect_plates(
        cls,
        frame: np.ndarray,
        vehicle_box: Optional[Tuple[int, int, int, int]] = None,
        manual_box: Optional[Tuple[int, int, int, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detects license plates in frame or inside a specified vehicle crop.
        Returns list of plate detections:
            [
                {
                    "bbox": (x1, y1, x2, y2), # absolute coordinates in frame
                    "crop": plate_crop_img,
                    "confidence": float,
                    "method": str
                }
            ]
        """
        if frame is None or frame.size == 0:
            return []

        # 1. Check if user provided manual bounding box coordinates
        if manual_box is not None:
            mx1, my1, mx2, my2 = manual_box
            h, w = frame.shape[:2]
            mx1, my1 = max(0, mx1), max(0, my1)
            mx2, my2 = min(w, mx2), min(h, my2)
            if mx2 > mx1 and my2 > my1:
                return [{
                    "bbox": (mx1, my1, mx2, my2),
                    "crop": frame[my1:my2, mx1:mx2],
                    "confidence": 1.0,
                    "method": "Manual Crop"
                }]

        # Determine ROI (region of interest)
        fh, fw = frame.shape[:2]
        if vehicle_box is not None:
            vx1, vy1, vx2, vy2 = vehicle_box
            roi = frame[vy1:vy2, vx1:vx2]
            offset_x, offset_y = vx1, vy1
        else:
            roi = frame
            offset_x, offset_y = 0, 0

        if roi.size == 0:
            roi = frame
            offset_x, offset_y = 0, 0

        rh, rw = roi.shape[:2]

        # 2. Try YOLO plate detector
        plate_model = get_plate_yolo_model()
        if plate_model is not None:
            try:
                results = plate_model(roi, conf=config.PLATE_CONFIDENCE, verbose=False)
                detections = []
                for r in results:
                    for box in r.boxes:
                        conf = float(box.conf[0].item())
                        xyxy = box.xyxy[0].cpu().numpy().astype(int)
                        px1 = max(0, xyxy[0]) + offset_x
                        py1 = max(0, xyxy[1]) + offset_y
                        px2 = min(fw, xyxy[2]) + offset_x
                        py2 = min(fh, xyxy[3]) + offset_y
                        crop = frame[py1:py2, px1:px2]
                        if crop.size > 0:
                            detections.append({
                                "bbox": (px1, py1, px2, py2),
                                "crop": crop,
                                "confidence": round(conf, 2),
                                "method": "YOLO Plate Model"
                            })
                if detections:
                    return detections
            except Exception as e:
                logger.warning(f"Error during YOLO plate inference: {e}")

        # 3. Morphological & Contour Plate Localization (OpenCV Fallback)
        return cls._morphological_plate_detector(roi, offset_x, offset_y, frame)

    @classmethod
    def _morphological_plate_detector(
        cls,
        roi: np.ndarray,
        offset_x: int,
        offset_y: int,
        full_frame: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Localizes rectangular high-contrast license plate regions using Sobel vertical edges,
        bright luminance plate segmentation, and morphological rectangular closing.
        """
        rh, rw = roi.shape[:2]
        fh, fw = full_frame.shape[:2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

        candidates = []

        # Strategy 1: Sobel vertical gradient edge band detection
        grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        blurred = cv2.GaussianBlur(abs_grad_x, (9, 9), 0)
        _, thresh_sobel = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Multi-scale rectangular kernels to merge character strokes into solid plate bands
        for k_size in ((25, 5), (17, 5), (31, 7)):
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, k_size)
            closed = cv2.morphologyEx(thresh_sobel, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = w / float(h) if h > 0 else 0
                area = w * h

                # Broad aspect range: 1.2 to 12.0 covers square, two-line, and standard wide plates
                if 1.2 <= aspect <= 12.0 and (rw * rh * 0.003) <= area <= (rw * rh * 0.85) and h >= 14:
                    pad_w = int(w * 0.10)
                    pad_h = int(h * 0.25)
                    abs_x1 = max(0, offset_x + x - pad_w)
                    abs_y1 = max(0, offset_y + y - pad_h)
                    abs_x2 = min(fw, offset_x + x + w + pad_w)
                    abs_y2 = min(fh, offset_y + y + h + pad_h)

                    crop = full_frame[abs_y1:abs_y2, abs_x1:abs_x2]
                    if crop.size > 0:
                        candidates.append({
                            "bbox": (abs_x1, abs_y1, abs_x2, abs_y2),
                            "crop": crop,
                            "confidence": 0.88,
                            "method": "OpenCV Morphological"
                        })

        # Strategy 2: High-contrast bright plate region detection (white/yellow license plates)
        _, thresh_bright = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel_bright = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        closed_bright = cv2.morphologyEx(thresh_bright, cv2.MORPH_CLOSE, kernel_bright)
        contours_b, _ = cv2.findContours(closed_bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours_b:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / float(h) if h > 0 else 0
            area = w * h
            if 1.3 <= aspect <= 9.0 and (rw * rh * 0.008) <= area <= (rw * rh * 0.80) and h >= 16:
                pad_w = int(w * 0.08)
                pad_h = int(h * 0.12)
                abs_x1 = max(0, offset_x + x - pad_w)
                abs_y1 = max(0, offset_y + y - pad_h)
                abs_x2 = min(fw, offset_x + x + w + pad_w)
                abs_y2 = min(fh, offset_y + y + h + pad_h)

                crop = full_frame[abs_y1:abs_y2, abs_x1:abs_x2]
                if crop.size > 0:
                    candidates.append({
                        "bbox": (abs_x1, abs_y1, abs_x2, abs_y2),
                        "crop": crop,
                        "confidence": 0.85,
                        "method": "Luminance Rectangular"
                    })

        # Return best candidate
        if candidates:
            # Prefer candidates closest to standard plate aspect ratios (2.5 - 5.5) and significant area
            def score_candidate(c):
                bx1, by1, bx2, by2 = c["bbox"]
                bw = bx2 - bx1
                bh = by2 - by1
                ar = bw / float(bh) if bh > 0 else 1.0
                aspect_fit = 1.0 - min(1.0, abs(ar - 4.0) / 4.0)
                area_ratio = (bw * bh) / float(rw * rh)
                return aspect_fit * 0.6 + min(area_ratio * 3.0, 0.4)

            candidates.sort(key=score_candidate, reverse=True)
            return candidates[:1]

        # Geometric default:
        # If inside a vehicle box: lower center of vehicle ROI typically holds the plate.
        # If no vehicle detected (user holding plate directly to webcam): CENTER of frame!
        if offset_x == 0 and offset_y == 0 and rw == fw and rh == fh:
            # User holding plate in front of camera / viewfinder zone
            def_w = int(rw * 0.70)
            def_h = int(rh * 0.45)
            def_x = int((rw - def_w) / 2)
            def_y = int((rh - def_h) / 2)
        else:
            def_w = int(rw * 0.55)
            def_h = int(rh * 0.25)
            def_x = offset_x + int((rw - def_w) / 2)
            def_y = offset_y + int(rh * 0.55)

        abs_x1 = max(0, def_x)
        abs_y1 = max(0, def_y)
        abs_x2 = min(fw, def_x + def_w)
        abs_y2 = min(fh, def_y + def_h)

        crop = full_frame[abs_y1:abs_y2, abs_x1:abs_x2]
        return [{
            "bbox": (abs_x1, abs_y1, abs_x2, abs_y2),
            "crop": crop,
            "confidence": 0.75,
            "method": "Viewfinder Center Geometric"
        }]

    @staticmethod
    def draw_plates(frame: np.ndarray, plates: List[Dict[str, Any]], plate_text: str = "") -> np.ndarray:
        """Draws vibrant green plate bounding box with detected license plate text."""
        annotated = frame.copy()
        for p in plates:
            x1, y1, x2, y2 = p["bbox"]
            # Draw bright green plate border
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 127), 2)
            label = plate_text if plate_text else f"PLATE {int(p['confidence'] * 100)}%"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated, (x1, max(0, y1 - 22)), (x1 + tw + 8, y1), (0, 255, 127), -1)
            cv2.putText(annotated, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
        return annotated
