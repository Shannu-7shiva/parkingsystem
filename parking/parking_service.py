from typing import Dict, Any, Optional, List
from database.database import get_db
from database.models import Vehicle, ParkingSlot, ParkingRecord, Blacklist, SystemSetting
from parking.slot_manager import SlotManager
from parking.occupancy import OccupancyManager
from parking.entry_manager import EntryManager
from parking.exit_manager import ExitManager
from parking.billing import BillingCalculator
import config


class ParkingService:
    """Unified service coordinating slot operations, ANPR entry/exit determination, and occupancy."""

    @classmethod
    def process_plate_event(
        cls,
        plate_number: str,
        vehicle_type: str = "car",
        image_path: Optional[str] = None,
        force_action: Optional[str] = None,  # "ENTRY", "EXIT", or None for auto-detect
        simulated_duration: Optional[float] = None,
        payment_mode: str = "Fastag Auto-Debit"
    ) -> Dict[str, Any]:
        """
        Determines whether the vehicle is entering or exiting, and processes accordingly.
        - If force_action is specified, executes that action.
        - Otherwise: if currently PARKED, processes EXIT; if NOT parked, processes ENTRY.
        """
        plate_clean = plate_number.strip().upper()

        with get_db() as session:
            # Check blacklist first
            blacklisted = session.query(Blacklist).filter_by(plate_number=plate_clean).first()
            if blacklisted:
                return {
                    "success": False,
                    "blacklisted": True,
                    "action": "BLOCKED",
                    "barrier_status": "LOCKED",
                    "plate_number": plate_clean,
                    "reason": blacklisted.reason,
                    "message": f"CRITICAL SECURITY ALERT: Blacklisted vehicle {plate_clean} flagged! Reason: {blacklisted.reason}. Barrier locked."
                }

            # Check current status
            active_session = session.query(ParkingRecord).filter_by(
                plate_number=plate_clean, status="PARKED"
            ).first()

            if force_action == "EXIT" or (force_action is None and active_session is not None):
                # Vehicle is exiting
                result = ExitManager.process_exit(
                    session=session,
                    plate_number=plate_clean,
                    exit_image=image_path,
                    simulated_duration_minutes=simulated_duration,
                    payment_mode=payment_mode,
                    vehicle_type=vehicle_type
                )
                return result
            else:
                # Vehicle is entering
                result = EntryManager.process_entry(
                    session=session,
                    plate_number=plate_clean,
                    vehicle_type=vehicle_type,
                    entry_image=image_path
                )
                return result

    @classmethod
    def get_dashboard_data(cls) -> Dict[str, Any]:
        """Returns consolidated dashboard statistics, slots, and recent records."""
        with get_db() as session:
            summary = OccupancyManager.get_summary_statistics(session)
            slots = SlotManager.get_all_slots(session)
            recent_records = session.query(ParkingRecord).order_by(
                ParkingRecord.id.desc()
            ).limit(10).all()

            return {
                "summary": summary,
                "slots": slots,
                "recent_records": [r.to_dict() for r in recent_records]
            }

    @classmethod
    def get_all_slots(cls) -> List[Dict[str, Any]]:
        with get_db() as session:
            return SlotManager.get_all_slots(session)

    @classmethod
    def toggle_slot_reservation(cls, slot_number: str) -> Dict[str, Any]:
        with get_db() as session:
            return SlotManager.toggle_reservation(session, slot_number)

    @classmethod
    def set_slot_status(cls, slot_number: str, status: str) -> Dict[str, Any]:
        """Sets slot status: AVAILABLE, RESERVED, MAINTENANCE."""
        with get_db() as session:
            slot = session.query(ParkingSlot).filter_by(slot_number=slot_number.upper()).first()
            if not slot:
                return {"success": False, "message": f"Slot {slot_number} not found."}
            if slot.status == "OCCUPIED" and status != "OCCUPIED":
                return {"success": False, "message": "Cannot change status of currently occupied slot."}

            slot.status = status.upper()
            return {"success": True, "slot": slot.to_dict(), "message": f"Slot {slot_number} marked as {status}."}

    @classmethod
    def get_record_receipt(cls, record_id: int) -> Optional[Dict[str, Any]]:
        """Generates full printable digital receipt with tax breakdown and QR payload."""
        with get_db() as session:
            rec = session.query(ParkingRecord).filter_by(id=record_id).first()
            if not rec:
                return None

            terminal_name = "Metro Smart ANPR Terminal"
            t_setting = session.query(SystemSetting).filter_by(setting_name="PARKING_LOT_NAME").first()
            if t_setting:
                terminal_name = t_setting.setting_value

            v_type = rec.vehicle.vehicle_type if rec.vehicle else "car"
            gst_pct = config.GST_PERCENTAGE
            total_amt = rec.amount or 0.0
            base_amt = round(total_amt / (1 + (gst_pct / 100.0)), 2) if total_amt > 0 else 0.0
            gst_amt = round(total_amt - base_amt, 2)

            return {
                "record_id": rec.id,
                "receipt_number": rec.receipt_number or f"REC-2026-{rec.id:05d}",
                "terminal_name": terminal_name,
                "plate_number": rec.plate_number,
                "slot_number": rec.slot_number,
                "vehicle_type": v_type,
                "vehicle_model": rec.vehicle.model if rec.vehicle else "Vehicle",
                "owner_name": rec.vehicle.owner_name if rec.vehicle else "Visitor",
                "entry_time": rec.entry_time.strftime("%Y-%m-%d %H:%M:%S") if rec.entry_time else None,
                "exit_time": rec.exit_time.strftime("%Y-%m-%d %H:%M:%S") if rec.exit_time else "ACTIVE",
                "duration_formatted": f"{int(rec.duration_minutes // 60)}h {int(rec.duration_minutes % 60)}m" if rec.duration_minutes else "Active",
                "status": rec.status,
                "payment_mode": rec.payment_mode or "Fastag Auto-Debit",
                "base_amount": base_amt,
                "gst_amount": gst_amt,
                "gst_percentage": gst_pct,
                "total_amount": total_amt,
                "currency": "₹",
                "qr_code_data": f"PARKVISION|{rec.receipt_number}|{rec.plate_number}|INR_{total_amt}|{rec.status}"
            }
