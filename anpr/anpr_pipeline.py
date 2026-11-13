import cv2
import re
import uuid
import time
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import config
from anpr.vehicle_detector import VehicleDetector
from anpr.plate_detector import PlateDetector
from anpr.ocr_engine import OCREngine, get_easyocr_reader
from anpr.plate_processor import PlateProcessor
from anpr.image_processor import ImageProcessor
from anpr.multi_frame_tracker import global_multi_frame_tracker
from parking.parking_service import ParkingService

logger = logging.getLogger("anpr.pipeline")


def make_json_serializable(data: Any) -> Any:
    """Recursively converts numpy data types, tuples, etc. into JSON-serializable Python native types."""
    if isinstance(data, (np.integer, np.int32, np.int64, np.int16, np.int8)):
        return int(data)
    elif isinstance(data, (np.floating, np.float32, np.float64)):
        return float(data)
    elif isinstance(data, np.bool_):
        return bool(data)
    elif isinstance(data, np.ndarray):
        return [make_json_serializable(x) for x in data.tolist()]
    elif isinstance(data, (list, tuple)):
        return [make_json_serializable(x) for x in data]
    elif isinstance(data, dict):
        return {str(k): make_json_serializable(v) for k, v in data.items()}
    return data


class ANPRPipeline:
    """
    State-of-the-Art Automatic Number Plate Recognition and Parking Integration Pipeline.
    Combines YOLO vehicle detection, morphological/YOLO plate localization,
    padding expansion, perspective deskewing, multi-variant OCR, Indian statutory syntax
    disambiguation, multi-frame consensus voting, and duplicate entry prevention.
    """

    @classmethod
    def process_frame(
        cls,
        frame: np.ndarray,
        manual_plate_box: Optional[Tuple[int, int, int, int]] = None,
        force_action: Optional[str] = None,
        override_plate_text: Optional[str] = None,
        auto_parking_trigger: bool = True,
        preferred_vehicle_type: Optional[str] = None,
        enable_multi_frame: bool = True
    ) -> Dict[str, Any]:
        """
        Executes complete ANPR cycle on a video frame or image:
        Frame -> Vehicle Detection -> Padded Plate Crop -> Perspective Correction ->
        Multi-Variant OCR -> Syntactic Disambiguation -> Multi-Frame Voting -> Gatekeeper Parking Action
        """
        start_total = time.perf_counter()

        if frame is None or frame.size == 0:
            return {
                "success": False,
                "error": "Empty or corrupted frame passed to ANPR pipeline."
            }

        annotated_frame = frame.copy()
        orig_h, orig_w = frame.shape[:2]

        # Fast scaling for ultra-fast detection if image is ultra-high-resolution (> 1280px)
        scale_ratio = 1.0
        detection_frame = frame
        if orig_w > 1280:
            scale_ratio = 1280.0 / orig_w
            new_h = int(orig_h * scale_ratio)
            detection_frame = cv2.resize(frame, (1280, new_h), interpolation=cv2.INTER_LINEAR)

        # Step 1: Detect Vehicles
        vehicles = VehicleDetector.detect_vehicles(detection_frame)
        if scale_ratio != 1.0 and vehicles:
            for v in vehicles:
                bx1, by1, bx2, by2 = v["bbox"]
                v["bbox"] = (
                    int(bx1 / scale_ratio),
                    int(by1 / scale_ratio),
                    int(bx2 / scale_ratio),
                    int(by2 / scale_ratio)
                )

        primary_vehicle = vehicles[0] if vehicles else None

        # Vehicle type resolution: manual preference or vision detection
        norm_pref = (preferred_vehicle_type or "").strip().lower()
        if norm_pref in ("motorcycle", "bike", "scooter", "two-wheeler", "two_wheeler"):
            vehicle_type = "motorcycle"
        elif norm_pref in ("car", "four-wheeler", "sedan", "suv"):
            vehicle_type = "car"
        elif norm_pref in ("auto", "autorickshaw", "rickshaw"):
            vehicle_type = "auto"
        elif norm_pref in ("bus", "truck", "van", "ev"):
            vehicle_type = norm_pref
        elif norm_pref and norm_pref not in ("auto-detect", "detect", "none", "auto", ""):
            vehicle_type = norm_pref
        else:
            vehicle_type = primary_vehicle["class_name"] if primary_vehicle else "car"

        if primary_vehicle:
            primary_vehicle["class_name"] = vehicle_type

        vehicle_bbox = primary_vehicle["bbox"] if primary_vehicle else None

        if vehicles:
            annotated_frame = VehicleDetector.draw_detections(annotated_frame, vehicles)

        # Step 2: Detect Number Plate
        plates = PlateDetector.detect_plates(
            frame,
            vehicle_box=vehicle_bbox,
            manual_box=manual_plate_box
        )
        primary_plate = plates[0] if plates else None

        # Step 3: Padded Cropping & Perspective Deskewing
        plate_crop_path = None
        sharpness_score = 100.0
        ocr_result = {
            "raw_text": "",
            "cleaned_plate": "",
            "confidence": 0.0,
            "valid": False,
            "engine": "none",
            "processing_time_ms": 0.0
        }

        if primary_plate and primary_plate.get("bbox") is not None:
            bbox = primary_plate["bbox"]
            # Crop with adaptive safety padding to avoid character boundary clipping
            crop_padded = ImageProcessor.crop_with_padding(frame, bbox, pad_x_pct=0.08, pad_y_pct=0.12)
            # Deskew and correct perspective tilt
            deskewed_crop = ImageProcessor.correct_perspective_and_deskew(crop_padded)
            sharpness_score = ImageProcessor.calculate_sharpness(deskewed_crop)

            # Save clean plate crop preview to disk
            crop_filename = f"plate_{uuid.uuid4().hex[:8]}.jpg"
            crop_file_path = config.PLATE_UPLOADS / crop_filename
            cv2.imwrite(str(crop_file_path), deskewed_crop)
            plate_crop_path = f"/uploads/plates/{crop_filename}"
            primary_plate["crop"] = deskewed_crop

            ocr_result = OCREngine.recognize_plate_text(deskewed_crop)

            if override_plate_text:
                val = PlateProcessor.validate_and_format(override_plate_text)
                if val.get("valid") or not ocr_result.get("valid"):
                    ocr_result = {
                        "raw_text": override_plate_text,
                        "cleaned_plate": val["cleaned_plate"],
                        "confidence": 0.98 if val["valid"] else 0.70,
                        "valid": val["valid"],
                        "details": val,
                        "engine": "Client-AI / Manual Input",
                        "processing_time_ms": 1.0
                    }

        # Step 4: Multi-Frame Temporal Consensus & Voting
        gate_channel = (force_action or "ENTRY").upper()
        single_plate = ocr_result.get("cleaned_plate") or ocr_result.get("raw_text") or ""
        single_conf = float(ocr_result.get("confidence", 0.0))

        consensus_info = {
            "consensus_plate": single_plate,
            "confidence": single_conf,
            "status": "SINGLE_FRAME",
            "is_confident": ocr_result.get("valid", False) and single_conf >= 0.85,
            "frames_count": 1
        }

        if enable_multi_frame and len(single_plate) >= 5:
            consensus_info = global_multi_frame_tracker.add_reading(
                gate_id=gate_channel,
                plate_text=single_plate,
                raw_text=ocr_result.get("raw_text", single_plate),
                confidence=single_conf,
                sharpness=sharpness_score,
                crop_url=plate_crop_path
            )

        detected_plate_number = consensus_info.get("consensus_plate") or single_plate
        consensus_confidence = consensus_info.get("confidence") or single_conf
        recognition_status = consensus_info.get("status", "SINGLE_FRAME")

        # Step 5: Vehicle Registry Enrichment
        owner_name = "Guest / Visitor"
        vehicle_model = "Vehicle"

        if detected_plate_number:
            try:
                from database.database import get_db
                from database.models import Vehicle
                with get_db() as session:
                    v_clean = detected_plate_number.replace(" ", "").replace("-", "").upper()
                    v_rec = session.query(Vehicle).filter(Vehicle.plate_number.like(f"%{v_clean}%")).first()
                    if v_rec:
                        owner_name = v_rec.owner_name or "Guest / Visitor"
                        vehicle_model = v_rec.model or "Vehicle"
                        if not preferred_vehicle_type or preferred_vehicle_type.lower() in ("auto", "auto-detect", "detect", "none", ""):
                            vehicle_type = v_rec.vehicle_type
            except Exception as e:
                logger.debug(f"Vehicle registry lookup notice: {e}")

        # Step 6: Visual HUD Annotation
        if primary_plate:
            annotated_frame = PlateDetector.draw_plates(
                annotated_frame,
                [primary_plate],
                plate_text=f"{detected_plate_number} ({int(consensus_confidence * 100)}%)"
            )

        snap_filename = f"snap_{uuid.uuid4().hex[:8]}.jpg"
        snap_path = config.VEHICLE_UPLOADS / snap_filename
        cv2.imwrite(str(snap_path), annotated_frame)
        saved_snap_url = f"/uploads/vehicles/{snap_filename}"

        # Step 7: Gatekeeper & Incorrect Vehicle Entry Prevention
        # Conditions:
        # 1. Duplicate Suppression: Check if same vehicle already registered within last 60s
        # 2. Confidence Tiering:
        #    - HIGH (>= 0.85 & Valid): Auto-process parking entry/exit
        #    - MEDIUM (0.60 - 0.84): Flag for operator review
        #    - LOW (< 0.60): Reject database entry, display "PLATE RECOGNITION UNCERTAIN - PLEASE VERIFY"
        parking_result = None
        action_allowed = False
        status_message = "Ready"

        is_duplicate = False
        if not override_plate_text and detected_plate_number and len(detected_plate_number) >= 5:
            is_duplicate = global_multi_frame_tracker.is_duplicate_event(
                gate_id=gate_channel, plate=detected_plate_number, cooldown_seconds=60.0
            )

        if is_duplicate:
            parking_result = {
                "success": True,
                "action": "DUPLICATE_SUPPRESSED",
                "plate_number": detected_plate_number,
                "barrier_status": "CLOSED",
                "message": f"Vehicle {detected_plate_number} was already processed at this gate. Duplicate entry suppressed."
            }
            status_message = "DUPLICATE ENTRY COOLED DOWN"
        elif auto_parking_trigger and detected_plate_number and len(detected_plate_number) >= 5:
            # Check validation confidence
            if consensus_confidence >= 0.82 and ocr_result.get("valid", True):
                # High confidence -> allow automatic gate barrier and database entry
                parking_result = ParkingService.process_plate_event(
                    plate_number=detected_plate_number,
                    vehicle_type=vehicle_type,
                    image_path=saved_snap_url,
                    force_action=force_action
                )
                if parking_result.get("success"):
                    global_multi_frame_tracker.mark_finalized(gate_channel, detected_plate_number)
                status_message = "AUTOMATIC ENTRY PASS"
            elif consensus_confidence >= 0.60:
                # Medium confidence -> require confirmation
                parking_result = {
                    "success": False,
                    "requires_confirmation": True,
                    "action": "CONFIRM_REQUIRED",
                    "plate_number": detected_plate_number,
                    "barrier_status": "CLOSED",
                    "confidence": consensus_confidence,
                    "message": f"Plate {detected_plate_number} detected with moderate confidence ({int(consensus_confidence*100)}%). Please verify."
                }
                status_message = "CONFIRMATION REQUIRED"
            else:
                # Low confidence -> Reject database mutation
                parking_result = {
                    "success": False,
                    "requires_confirmation": False,
                    "action": "REJECTED_UNCERTAIN",
                    "plate_number": detected_plate_number,
                    "barrier_status": "CLOSED",
                    "confidence": consensus_confidence,
                    "message": "PLATE RECOGNITION UNCERTAIN - PLEASE VERIFY"
                }
                status_message = "PLATE RECOGNITION UNCERTAIN - PLEASE VERIFY"

        total_latency_ms = round((time.perf_counter() - start_total) * 1000, 2)

        raw_result = {
            "success": True,
            "plate_number": detected_plate_number,
            "owner_name": owner_name,
            "vehicle_model": vehicle_model,
            "vehicle_detected": len(vehicles) > 0,
            "vehicle_type": vehicle_type,
            "vehicle_confidence": primary_vehicle["confidence"] if primary_vehicle else 0.0,
            "vehicle_box": list(vehicle_bbox) if vehicle_bbox else None,
            "plate_detected": primary_plate is not None,
            "plate_box": list(primary_plate["bbox"]) if primary_plate else None,
            "plate_crop_url": plate_crop_path,
            "annotated_image_url": saved_snap_url,
            "ocr": {
                "raw_text": ocr_result["raw_text"],
                "cleaned_plate": detected_plate_number,
                "confidence": consensus_confidence,
                "valid": ocr_result["valid"],
                "engine": ocr_result["engine"],
                "ocr_time_ms": ocr_result.get("processing_time_ms", 0.0)
            },
            "multi_frame": {
                "frames_aggregated": consensus_info.get("frames_count", 1),
                "total_buffered": consensus_info.get("total_frames_buffered", 1),
                "status": recognition_status,
                "status_message": status_message,
                "sharpness": round(sharpness_score, 1)
            },
            "parking_action": parking_result,
            "latency_ms": total_latency_ms
        }
        return make_json_serializable(raw_result)
