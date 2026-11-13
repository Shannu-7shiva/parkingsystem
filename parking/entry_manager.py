from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from database.models import Vehicle, ParkingSlot, ParkingRecord, Blacklist
from parking.slot_manager import SlotManager
import logging

logger = logging.getLogger("parking.entry")


class EntryManager:
    """Handles vehicle arrival, blacklist verification, slot assignment, and entry recording."""

    @classmethod
    def process_entry(
        cls,
        session: Session,
        plate_number: str,
        vehicle_type: str = "car",
        entry_image: Optional[str] = None,
        owner_name: str = "Guest / Visitor",
        phone: str = "",
        model: str = "Sedan / Hatchback"
    ) -> Dict[str, Any]:
        plate_clean = plate_number.strip().upper()

        # 1. Blacklist check
        blacklist_entry = session.query(Blacklist).filter_by(plate_number=plate_clean).first()
        if blacklist_entry:
            logger.warning(f"ALERT: Blacklisted vehicle attempted entry: {plate_clean}")
            return {
                "success": False,
                "blacklisted": True,
                "action": "BLOCKED",
                "plate_number": plate_clean,
                "reason": blacklist_entry.reason,
                "message": f"CRITICAL SECURITY ALERT: Blacklisted vehicle {plate_clean} detected! Entry barrier locked."
            }

        # 2. Check if already parked
        active_record = session.query(ParkingRecord).filter_by(
            plate_number=plate_clean, status="PARKED"
        ).first()
        if active_record:
            logger.info(f"Vehicle {plate_clean} is already parked in slot {active_record.slot_number}")
            return {
                "success": False,
                "already_parked": True,
                "action": "ALREADY_PARKED",
                "plate_number": plate_clean,
                "slot_number": active_record.slot_number,
                "entry_time": active_record.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Vehicle {plate_clean} is already registered in Bay {active_record.slot_number}."
            }

        # 3. Find or create Vehicle in database
        vehicle = session.query(Vehicle).filter_by(plate_number=plate_clean).first()
        if not vehicle:
            vehicle = Vehicle(
                plate_number=plate_clean,
                vehicle_type=vehicle_type,
                model=model,
                owner_name=owner_name,
                phone=phone,
                is_blacklisted=False,
                created_at=datetime.now()
            )
            session.add(vehicle)
            session.flush()
        else:
            # Update type if newly recognized with higher certainty
            if vehicle_type and vehicle_type != "unknown":
                vehicle.vehicle_type = vehicle_type
            session.flush()

        # 4. Find available slot matching type
        slot = SlotManager.find_available_slot(session, vehicle_type=vehicle.vehicle_type)
        if not slot:
            logger.warning(f"Parking full when attempting to park {plate_clean}")
            return {
                "success": False,
                "lot_full": True,
                "action": "LOT_FULL",
                "plate_number": plate_clean,
                "message": "PARKING LOT FULL: No available slots for entry. Entry barrier held."
            }

        # 5. Assign slot & create record
        SlotManager.assign_slot(session, slot, vehicle)

        now = datetime.now()
        ticket_number = f"TCK-{now.strftime('%y%m%d')}-{slot.slot_number}"
        new_record = ParkingRecord(
            vehicle_id=vehicle.id,
            plate_number=plate_clean,
            slot_number=slot.slot_number,
            entry_time=now,
            exit_time=None,
            duration_minutes=0.0,
            amount=0.0,
            status="PARKED",
            payment_mode="Pending Checkout",
            receipt_number=ticket_number,
            entry_image=entry_image,
            created_at=now
        )
        session.add(new_record)
        session.flush()

        logger.info(f"Entry registered: {plate_clean} -> Slot {slot.slot_number} at {now}")
        return {
            "success": True,
            "action": "ENTRY",
            "barrier_status": "OPEN",
            "record_id": new_record.id,
            "ticket_number": ticket_number,
            "plate_number": plate_clean,
            "slot_number": slot.slot_number,
            "slot_type": slot.slot_type,
            "vehicle_type": vehicle.vehicle_type,
            "owner_name": vehicle.owner_name,
            "entry_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "entry_image": entry_image,
            "message": f"Welcome! Vehicle {plate_clean} assigned to Bay {slot.slot_number}. Barrier open."
        }
