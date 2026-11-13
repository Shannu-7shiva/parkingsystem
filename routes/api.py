import io
import csv
import cv2
import uuid
import numpy as np
from datetime import datetime, timedelta, date
from flask import Blueprint, request, jsonify, Response, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import func, or_

import config
from database.database import get_db
from database.models import Vehicle, ParkingSlot, ParkingRecord, Blacklist, SystemSetting
from parking.parking_service import ParkingService
from parking.slot_manager import SlotManager
from simulation.simulator import ParkingSimulator
from simulation.virtual_camera import VirtualCamera
from anpr.anpr_pipeline import ANPRPipeline, make_json_serializable
from anpr.plate_processor import PlateProcessor
from routes.authentication import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ----------------------------------------------------
# 1. Dashboard & Slots Endpoints
# ----------------------------------------------------

@api_bp.route("/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    try:
        data = ParkingService.get_dashboard_data()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/parking-slots", methods=["GET"])
@login_required
def get_slots():
    try:
        slots = ParkingService.get_all_slots()
        return jsonify({"success": True, "slots": slots})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/parking-slots/<slot_number>/reserve", methods=["POST"])
@login_required
def toggle_slot_reservation(slot_number):
    try:
        result = ParkingService.toggle_slot_reservation(slot_number)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/parking-slots/<slot_number>/status", methods=["POST"])
@login_required
def set_slot_status(slot_number):
    try:
        data = request.get_json() or {}
        new_status = data.get("status", "AVAILABLE")
        result = ParkingService.set_slot_status(slot_number, new_status)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------------------------------
# 2. Vehicle Operations & Entry / Exit
# ----------------------------------------------------

@api_bp.route("/vehicle-entry", methods=["POST"])
@login_required
def manual_vehicle_entry():
    data = request.get_json() or {}
    plate = data.get("plate_number", "").strip().upper()
    v_type = data.get("vehicle_type", "car")
    owner = data.get("owner_name", "Visitor")
    phone = data.get("phone", "")

    if not plate:
        return jsonify({"success": False, "message": "License plate number is required."}), 400

    result = ParkingService.process_plate_event(
        plate_number=plate,
        vehicle_type=v_type,
        force_action="ENTRY"
    )
    return jsonify(result)


@api_bp.route("/vehicle-exit", methods=["POST"])
@login_required
def manual_vehicle_exit():
    data = request.get_json() or {}
    plate = data.get("plate_number", "").strip().upper()
    duration = data.get("simulated_duration")
    pay_mode = data.get("payment_mode", "Fastag Auto-Debit")
    v_type = data.get("vehicle_type")

    if not plate:
        return jsonify({"success": False, "message": "License plate number is required."}), 400

    result = ParkingService.process_plate_event(
        plate_number=plate,
        vehicle_type=v_type,
        force_action="EXIT",
        simulated_duration=float(duration) if duration else None,
        payment_mode=pay_mode
    )
    return jsonify(result)


@api_bp.route("/camera-exit", methods=["POST"])
@login_required
def camera_exit():
    """Called by exit camera page when a plate is detected."""
    data = request.get_json() or {}
    plate = data.get("plate_number", "").strip().upper()
    pay_mode = data.get("payment_mode", "UPI / Online")
    v_type = data.get("vehicle_type")
    if not plate:
        return jsonify({"success": False, "message": "No plate provided"}), 400
    result = ParkingService.process_plate_event(
        plate_number=plate,
        vehicle_type=v_type,
        force_action="EXIT",
        payment_mode=pay_mode
    )
    return jsonify(result)


# ----------------------------------------------------
# 3. Simulation Endpoints
# ----------------------------------------------------

@api_bp.route("/simulate-entry", methods=["POST"])
@login_required
def simulate_entry():
    data = request.get_json() or {}
    plate = data.get("plate_number")
    v_type = data.get("vehicle_type")
    result = ParkingSimulator.simulate_entry(plate_number=plate, vehicle_type=v_type)
    return jsonify(result)


@api_bp.route("/simulate-exit", methods=["POST"])
@login_required
def simulate_exit():
    data = request.get_json() or {}
    plate = data.get("plate_number")
    duration = data.get("duration_minutes")
    result = ParkingSimulator.simulate_exit(
        plate_number=plate,
        simulated_duration=float(duration) if duration else None
    )
    return jsonify(result)


@api_bp.route("/auto-demo", methods=["POST"])
@login_required
def auto_demo():
    result = ParkingSimulator.auto_demo_step()
    return jsonify(result)


# ----------------------------------------------------
# 4. ANPR Processing Endpoints
# ----------------------------------------------------

@api_bp.route("/anpr/process", methods=["POST"])
@login_required
def process_anpr_media():
    try:
        # Check if file was uploaded
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"success": False, "message": "No file selected."}), 400

            file_bytes = np.frombuffer(file.read(), np.uint8)
            frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({"success": False, "message": "Could not decode uploaded image."}), 400
        else:
            return jsonify({"success": False, "message": "No image/frame payload provided."}), 400

        # Optional manual coordinates
        manual_box = None
        if "box" in request.form:
            import json
            box_data = json.loads(request.form["box"])
            manual_box = (int(box_data["x1"]), int(box_data["y1"]), int(box_data["x2"]), int(box_data["y2"]))

        override_text = request.form.get("plate_text", "").strip() or None
        force_action = request.form.get("force_action", "").strip() or None
        pref_vehicle_type = request.form.get("vehicle_type", "").strip() or None

        result = ANPRPipeline.process_frame(
            frame=frame,
            manual_plate_box=manual_box,
            force_action=force_action,
            override_plate_text=override_text,
            auto_parking_trigger=True,
            preferred_vehicle_type=pref_vehicle_type
        )
        return jsonify(make_json_serializable(result))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/anpr/debug-pipeline", methods=["POST"])
@login_required
def debug_anpr_pipeline():
    """
    Dedicated Computer Vision Debugging API:
    Returns full preprocessing pipeline inspection: original crop, deskewed crop,
    all 5 filtered variants in base64, candidate ranking, and multi-frame voting simulation.
    """
    import base64
    from anpr.image_processor import ImageProcessor
    from anpr.ocr_engine import OCREngine
    from anpr.plate_processor import PlateProcessor
    from anpr.plate_detector import PlateDetector

    try:
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No image file uploaded."}), 400

        file = request.files["file"]
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"success": False, "message": "Invalid image payload."}), 400

        # Step 1: Detect Plate
        plates = PlateDetector.detect_plates(frame)
        if plates:
            plate_box = plates[0]["bbox"]
            plate_crop = ImageProcessor.crop_with_padding(frame, plate_box)
        else:
            plate_box = (0, 0, frame.shape[1], frame.shape[0])
            plate_crop = frame.copy()

        # Step 2: Perspective Deskewing
        deskewed = ImageProcessor.correct_perspective_and_deskew(plate_crop)
        sharpness = ImageProcessor.calculate_sharpness(deskewed)

        # Step 3: Preprocessing Variants
        variants = ImageProcessor.generate_preprocessing_variants(deskewed)

        def img_to_b64(img_arr):
            if img_arr is None or img_arr.size == 0:
                return ""
            _, buf = cv2.imencode(".jpg", img_arr)
            return "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")

        variant_previews = {name: img_to_b64(img) for name, img in variants.items()}

        # Step 4: Run Multi-Variant OCR Extraction
        ocr_result = OCREngine.recognize_plate_text(deskewed)

        # Step 5: Indian Plate Syntax Disambiguation
        disambiguated, val_details = PlateProcessor.disambiguate_indian_plate(
            ocr_result.get("cleaned_plate") or ocr_result.get("raw_text") or ""
        )

        return jsonify({
            "success": True,
            "sharpness": round(sharpness, 1),
            "plate_detected": len(plates) > 0,
            "plate_bbox": list(plate_box),
            "original_crop_b64": img_to_b64(plate_crop),
            "deskewed_b64": img_to_b64(deskewed),
            "variants": variant_previews,
            "ocr_output": ocr_result,
            "resolved_plate": disambiguated,
            "validation": val_details
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------------------------------
# 5. Vehicles & Parking History Endpoints
# ----------------------------------------------------

@api_bp.route("/vehicles", methods=["GET"])
@login_required
def get_vehicles():
    search = request.args.get("search", "").strip()
    v_type = request.args.get("type", "").strip()
    status_filter = request.args.get("status", "").strip()  # "parked", "all"

    with get_db() as session:
        query = session.query(Vehicle)

        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                or_(
                    Vehicle.plate_number.ilike(search_fmt),
                    Vehicle.owner_name.ilike(search_fmt),
                    Vehicle.phone.ilike(search_fmt),
                    Vehicle.model.ilike(search_fmt)
                )
            )

        if v_type and v_type != "all":
            query = query.filter(Vehicle.vehicle_type == v_type)

        vehicles_list = query.order_by(Vehicle.id.desc()).all()
        result_data = []

        for v in vehicles_list:
            v_dict = v.to_dict()
            active_rec = session.query(ParkingRecord).filter_by(
                vehicle_id=v.id, status="PARKED"
            ).first()

            v_dict["is_currently_parked"] = active_rec is not None
            v_dict["current_slot"] = active_rec.slot_number if active_rec else None
            v_dict["entry_time"] = active_rec.entry_time.strftime("%Y-%m-%d %H:%M:%S") if active_rec else None

            # Total visits and total revenue paid
            all_records = session.query(ParkingRecord).filter_by(vehicle_id=v.id).all()
            v_dict["total_visits"] = len(all_records)
            v_dict["total_paid"] = round(sum(r.amount for r in all_records), 2)

            if status_filter == "parked" and not v_dict["is_currently_parked"]:
                continue

            result_data.append(v_dict)

        return jsonify({"success": True, "count": len(result_data), "vehicles": result_data})


@api_bp.route("/vehicles/<plate>", methods=["GET"])
@login_required
def get_vehicle_details(plate):
    plate_clean = plate.strip().upper()
    with get_db() as session:
        vehicle = session.query(Vehicle).filter_by(plate_number=plate_clean).first()
        if not vehicle:
            return jsonify({"success": False, "message": f"Vehicle {plate_clean} not found."}), 404

        v_dict = vehicle.to_dict()
        records = session.query(ParkingRecord).filter_by(vehicle_id=vehicle.id).order_by(
            ParkingRecord.entry_time.desc()
        ).all()

        active_rec = next((r for r in records if r.status == "PARKED"), None)
        v_dict["current_slot"] = active_rec.slot_number if active_rec else None
        v_dict["is_currently_parked"] = active_rec is not None
        v_dict["total_visits"] = len(records)
        v_dict["total_paid"] = round(sum(r.amount for r in records), 2)
        v_dict["history"] = [r.to_dict() for r in records]

        return jsonify({"success": True, "vehicle": v_dict})


@api_bp.route("/parking-history", methods=["GET"])
@login_required
def get_parking_history():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    with get_db() as session:
        query = session.query(ParkingRecord)

        if search:
            query = query.filter(
                or_(
                    ParkingRecord.plate_number.ilike(f"%{search}%"),
                    ParkingRecord.slot_number.ilike(f"%{search}%"),
                    ParkingRecord.receipt_number.ilike(f"%{search}%")
                )
            )

        if status_filter and status_filter != "all":
            query = query.filter(ParkingRecord.status == status_filter)

        records = query.order_by(ParkingRecord.id.desc()).all()
        return jsonify({"success": True, "count": len(records), "records": [r.to_dict() for r in records]})


@api_bp.route("/parking-records/<int:record_id>/receipt", methods=["GET"])
@login_required
def get_record_receipt(record_id):
    try:
        receipt = ParkingService.get_record_receipt(record_id)
        if not receipt:
            return jsonify({"success": False, "message": f"Parking record #{record_id} not found."}), 404
        return jsonify({"success": True, "receipt": receipt})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/parking-history/export", methods=["GET"])
@login_required
def export_parking_history_csv():
    with get_db() as session:
        records = session.query(ParkingRecord).order_by(ParkingRecord.entry_time.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Record ID", "Receipt Number", "Plate Number", "Slot", "Status", "Payment Mode", "Entry Time", "Exit Time", "Duration (mins)", "Amount (INR)"])

        for r in records:
            writer.writerow([
                r.id,
                r.receipt_number or f"REC-2026-{r.id:05d}",
                r.plate_number,
                r.slot_number,
                r.status,
                r.payment_mode or "Fastag",
                r.entry_time.strftime("%Y-%m-%d %H:%M:%S") if r.entry_time else "",
                r.exit_time.strftime("%Y-%m-%d %H:%M:%S") if r.exit_time else "",
                r.duration_minutes,
                r.amount
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=smart_parking_records.csv"}
        )


# ----------------------------------------------------
# 6. Blacklist Endpoints
# ----------------------------------------------------

@api_bp.route("/blacklist", methods=["GET"])
@login_required
def get_blacklist():
    with get_db() as session:
        entries = session.query(Blacklist).order_by(Blacklist.created_at.desc()).all()
        return jsonify({"success": True, "blacklist": [e.to_dict() for e in entries]})


@api_bp.route("/blacklist", methods=["POST"])
@login_required
def add_blacklist():
    data = request.get_json() or {}
    plate = data.get("plate_number", "").strip().upper()
    reason = data.get("reason", "Flagged by administrator").strip()

    if not plate:
        return jsonify({"success": False, "message": "License plate number is required."}), 400

    with get_db() as session:
        existing = session.query(Blacklist).filter_by(plate_number=plate).first()
        if existing:
            existing.reason = reason
        else:
            new_entry = Blacklist(plate_number=plate, reason=reason)
            session.add(new_entry)

        # Update vehicle flag if exists
        vehicle = session.query(Vehicle).filter_by(plate_number=plate).first()
        if vehicle:
            vehicle.is_blacklisted = True

        return jsonify({"success": True, "message": f"Vehicle {plate} added to security blacklist."})


@api_bp.route("/blacklist/<plate>", methods=["DELETE"])
@login_required
def remove_blacklist(plate):
    plate_clean = plate.strip().upper()
    with get_db() as session:
        entry = session.query(Blacklist).filter_by(plate_number=plate_clean).first()
        if not entry:
            return jsonify({"success": False, "message": f"Vehicle {plate_clean} not found in blacklist."}), 404

        session.delete(entry)
        vehicle = session.query(Vehicle).filter_by(plate_number=plate_clean).first()
        if vehicle:
            vehicle.is_blacklisted = False

        return jsonify({"success": True, "message": f"Vehicle {plate_clean} removed from blacklist."})


# ----------------------------------------------------
# 7. Analytics Endpoints
# ----------------------------------------------------

@api_bp.route("/analytics", methods=["GET"])
@login_required
def get_analytics():
    with get_db() as session:
        now = datetime.now()
        # 7-day vehicle count & revenue trend
        dates = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
        date_labels = [d.strftime("%a (%b %d)") for d in dates]
        daily_counts = []
        daily_revenue = []

        for d in dates:
            d_start = datetime.combine(d, datetime.min.time())
            d_end = datetime.combine(d, datetime.max.time())
            records = session.query(ParkingRecord).filter(
                ParkingRecord.created_at >= d_start,
                ParkingRecord.created_at <= d_end
            ).all()

            daily_counts.append(len(records))
            daily_revenue.append(round(sum(r.amount for r in records), 2))

        # Peak hours distribution (0 to 23 hours)
        hourly_counts = [0] * 24
        all_records = session.query(ParkingRecord).all()
        for r in all_records:
            if r.entry_time:
                h = r.entry_time.hour
                hourly_counts[h] += 1

        # Vehicle type distribution
        vehicle_types = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "ev": 0}
        all_vehicles = session.query(Vehicle).all()
        for v in all_vehicles:
            t = (v.vehicle_type or "car").lower()
            if "ev" in t or "electric" in t:
                vehicle_types["ev"] += 1
            elif t in vehicle_types:
                vehicle_types[t] += 1
            else:
                vehicle_types["car"] += 1

        # Slot occupancy percentage
        total_slots = session.query(ParkingSlot).count()
        occupied_slots = session.query(ParkingSlot).filter_by(status="OCCUPIED").count()
        occupancy_pct = round((occupied_slots / total_slots * 100), 1) if total_slots > 0 else 0

        # Totals
        total_revenue_all = round(sum(r.amount for r in all_records), 2)
        avg_duration = 0.0
        completed_recs = [r for r in all_records if r.duration_minutes > 0]
        if completed_recs:
            avg_duration = round(sum(r.duration_minutes for r in completed_recs) / len(completed_recs), 1)

        return jsonify({
            "success": True,
            "data": {
                "chart_labels": date_labels,
                "daily_vehicle_counts": daily_counts,
                "daily_revenue": daily_revenue,
                "peak_hours": hourly_counts,
                "vehicle_types": vehicle_types,
                "occupancy_percentage": occupancy_pct,
                "total_vehicles_all_time": len(all_vehicles),
                "total_records_all_time": len(all_records),
                "total_revenue_all_time": total_revenue_all,
                "average_duration_minutes": avg_duration
            }
        })


# ----------------------------------------------------
# 8. Tariffs & Settings Endpoints
# ----------------------------------------------------

@api_bp.route("/tariffs", methods=["GET"])
@login_required
def get_tariffs():
    return jsonify({
        "success": True,
        "tariffs": config.TARIFF_BY_VEHICLE_TYPE,
        "grace_period_minutes": config.GRACE_PERIOD_MINUTES,
        "gst_percentage": config.GST_PERCENTAGE
    })


@api_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    with get_db() as session:
        settings_objs = session.query(SystemSetting).all()
        settings_dict = {s.setting_name: s.setting_value for s in settings_objs}
        return jsonify({"success": True, "settings": settings_dict})


@api_bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    data = request.get_json() or {}
    with get_db() as session:
        for key, val in data.items():
            s = session.query(SystemSetting).filter_by(setting_name=key).first()
            if s:
                s.setting_value = str(val)
            else:
                session.add(SystemSetting(setting_name=key, setting_value=str(val)))
        return jsonify({"success": True, "message": "Settings updated successfully."})
