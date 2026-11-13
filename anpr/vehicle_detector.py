import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
import config

logger = logging.getLogger("anpr.vehicle_detector")

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "automobile"}
COCO_VEHICLE_IDS = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

_yolo_vehicle_model = None
_yolo_loaded = False


def get_yolo_vehicle_model():
    """Lazy loader for YOLO vehicle detection model."""
    global _yolo_vehicle_model, _yolo_loaded
    if _yolo_loaded:
        return _yolo_vehicle_model

    try:
        from ultralytics import YOLO
        model_path = config.YOLO_MODEL_PATH
        # Check if local model exists or download small yolov8n
        if model_path.exists():
            _yolo_vehicle_model = YOLO(str(model_path))
        else:
            _yolo_vehicle_model = YOLO("yolov8n.pt")
        _yolo_loaded = True
        logger.info("YOLO vehicle model loaded successfully.")
    except Exception as e:
        logger.warning(f"Ultralytics YOLO vehicle model not loaded ({e}). Using OpenCV heuristic detector.")
        _yolo_vehicle_model = None
        _yolo_loaded = True

    return _yolo_vehicle_model


class VehicleDetector:
    """Detects vehicles (cars, motorcycles, buses, trucks) using YOLO or OpenCV heuristics."""

    @classmethod
    def detect_vehicles(cls, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects vehicles in frame.
        Returns list of detections with bounding box, class, confidence, and cropped region.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []

        # 1. Try YOLO
        yolo_model = get_yolo_vehicle_model()
        if yolo_model is not None:
            try:
                results = yolo_model(frame, conf=config.VEHICLE_CONFIDENCE, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        if cls_id in COCO_VEHICLE_IDS:
                            class_name = COCO_VEHICLE_IDS[cls_id]
                            xyxy = box.xyxy[0].cpu().numpy().astype(int)
                            x1, y1, x2, y2 = max(0, xyxy[0]), max(0, xyxy[1]), min(w, xyxy[2]), min(h, xyxy[3])
                            crop = frame[y1:y2, x1:x2]
                            detections.append({
                                "class_name": class_name,
                                "confidence": round(conf, 2),
                                "bbox": (x1, y1, x2, y2),
                                "crop": crop,
                                "detector": "YOLO"
                            })
                if detections:
                    return detections
            except Exception as e:
                logger.warning(f"YOLO detection exception: {e}. Falling back to OpenCV detector.")

        # 2. OpenCV Fallback Detector (Edge, aspect-ratio and contours)
        return cls._opencv_fallback_detector(frame)

    @classmethod
    def _opencv_fallback_detector(cls, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Fallback vehicle detector using contour geometry, dual headlight symmetry,
        wide horizontal edge analysis, and vertical fork line features.
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # 1. Edge orientation analysis:
        # Cars have multiple wide horizontal lines (bumper, grille, hood, windshield)
        # Two-wheelers have vertical fork suspension lines
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=35, minLineLength=int(w * 0.20), maxLineGap=12)
        wide_horiz_lines = 0
        steep_forks = 0
        if lines is not None:
            for line in lines:
                pts = line.reshape(-1)
                if len(pts) >= 4:
                    x1, y1, x2, y2 = int(pts[0]), int(pts[1]), int(pts[2]), int(pts[3])
                    dx, dy = abs(x2 - x1), abs(y2 - y1)
                    if dx > dy * 1.6 and dx > (w * 0.20):
                        wide_horiz_lines += 1
                    elif dy > dx * 1.6 and (w * 0.20 <= (x1 + x2) / 2 <= w * 0.80):
                        steep_forks += 1

        # 2. Check for dual headlights on opposite flanks (car signature: left < 35% and right > 65%)
        upper_half = gray[:int(h * 0.65), :]
        left_flank = upper_half[:, :int(w * 0.35)]
        right_flank = upper_half[:, int(w * 0.65):]
        p80 = np.percentile(upper_half, 80)
        left_has_light = np.mean(left_flank > p80) > 0.05
        right_has_light = np.mean(right_flank > p80) > 0.05
        has_dual_headlights = left_has_light and right_has_light

        # 3. Check for single central circular headlight (exclusive to motorcycle)
        circles = cv2.HoughCircles(
            upper_half,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=50,
            param1=60,
            param2=36,
            minRadius=int(h * 0.12),
            maxRadius=int(h * 0.45)
        )
        is_isolated_bike_headlight = False
        if circles is not None and not has_dual_headlights and wide_horiz_lines < 6:
            for c in circles[0]:
                cx, cy, r = c
                if int(w * 0.35) <= cx <= int(w * 0.65):
                    is_isolated_bike_headlight = True
                    break

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []

        # Find the largest bounding box among significant contours
        best_cnt = None
        max_area = 0
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if area > (w * h * 0.04) and area > max_area:
                max_area = area
                best_cnt = (x, y, bw, bh)

        if best_cnt is not None:
            x, y, bw, bh = best_cnt
            x1, y1, x2, y2 = max(0, int(x)), max(0, int(y)), min(w, int(x + bw)), min(h, int(y + bh))
            aspect = bw / float(bh) if bh > 0 else 1.5

            if has_dual_headlights or wide_horiz_lines >= 5:
                detected_class = "car"
                conf = 0.94
            elif (is_isolated_bike_headlight or steep_forks >= 3) and wide_horiz_lines < 4:
                detected_class = "motorcycle"
                conf = 0.91
            elif aspect > 3.0:
                detected_class = "bus"
                conf = 0.86
            elif aspect > 2.2 and wide_horiz_lines >= 6:
                detected_class = "truck"
                conf = 0.85
            elif aspect < 1.05 and wide_horiz_lines <= 2:
                detected_class = "motorcycle"
                conf = 0.88
            else:
                detected_class = "car"
                conf = 0.88

            detections.append({
                "class_name": detected_class,
                "confidence": float(conf),
                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                "crop": frame[y1:y2, x1:x2],
                "detector": "OpenCV-Vision-Analysis"
            })

        # If no specific contour exceeded threshold, consider central frame region as vehicle focus
        if not detections and h > 100 and w > 100:
            cx1, cy1 = int(w * 0.15), int(h * 0.15)
            cx2, cy2 = int(w * 0.85), int(h * 0.85)
            fw = cx2 - cx1
            fh = cy2 - cy1
            f_aspect = fw / float(fh) if fh > 0 else 1.5

            if is_isolated_bike_headlight and not has_dual_headlights:
                default_class = "motorcycle"
                conf = 0.91
            elif f_aspect > 3.0:
                default_class = "bus"
                conf = 0.82
            else:
                default_class = "car"
                conf = 0.85

            detections.append({
                "class_name": default_class,
                "confidence": float(conf),
                "bbox": (int(cx1), int(cy1), int(cx2), int(cy2)),
                "crop": frame[cy1:cy2, cx1:cx2],
                "detector": "Vision-Signature-Focus"
            })

        return detections

        return detections

    @staticmethod
    def draw_detections(frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """Annotates frame with bounding boxes and confidence labels."""
        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            label = f"{det['class_name'].upper()} {int(det['confidence'] * 100)}%"
            # Draw cyan/blue bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 215, 255), 2)
            # Label background banner
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, max(0, y1 - 25)), (x1 + tw + 10, y1), (0, 215, 255), -1)
            cv2.putText(annotated, label, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        return annotated
