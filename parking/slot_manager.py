from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.models import ParkingSlot, Vehicle


class SlotManager:
    """Manages parking slot allocation, reservations, and occupancy status."""

    @staticmethod
    def get_all_slots(session: Session) -> List[Dict[str, Any]]:
        """Retrieves list of all slots ordered by slot number."""
        slots = session.query(ParkingSlot).order_by(ParkingSlot.slot_number.asc()).all()
        return [slot.to_dict() for slot in slots]

    @staticmethod
    def find_available_slot(session: Session, vehicle_type: str = "car") -> Optional[ParkingSlot]:
        """
        Finds the most suitable available slot.
        - EV vehicles prioritize EV slots
        - Normal cars/vehicles choose NORMAL slots first, then other available non-reserved slots
        """
        v_type_lower = vehicle_type.lower()

        if "ev" in v_type_lower or "electric" in v_type_lower:
            ev_slot = session.query(ParkingSlot).filter_by(
                slot_type="EV", status="AVAILABLE"
            ).first()
            if ev_slot:
                return ev_slot

        # For normal cars, prefer NORMAL slots first
        normal_slot = session.query(ParkingSlot).filter_by(
            slot_type="NORMAL", status="AVAILABLE"
        ).order_by(ParkingSlot.slot_number.asc()).first()

        if normal_slot:
            return normal_slot

        # If normal slots are full, any available slot (excluding VIP if possible)
        available_fallback = session.query(ParkingSlot).filter(
            ParkingSlot.status == "AVAILABLE",
            ParkingSlot.slot_type != "VIP"
        ).order_by(ParkingSlot.slot_number.asc()).first()

        if available_fallback:
            return available_fallback

        # Check VIP as last resort
        return session.query(ParkingSlot).filter_by(
            slot_type="VIP", status="AVAILABLE"
        ).first()

    @staticmethod
    def assign_slot(session: Session, slot: ParkingSlot, vehicle: Vehicle) -> bool:
        """Assigns an available slot to a vehicle."""
        if slot.status != "AVAILABLE":
            return False
        slot.status = "OCCUPIED"
        slot.vehicle_id = vehicle.id
        session.flush()
        return True

    @staticmethod
    def release_slot(session: Session, slot_number: str) -> bool:
        """Releases a parking slot back to AVAILABLE."""
        slot = session.query(ParkingSlot).filter_by(slot_number=slot_number).first()
        if not slot:
            return False
        slot.status = "AVAILABLE"
        slot.vehicle_id = None
        session.flush()
        return True

    @staticmethod
    def toggle_reservation(session: Session, slot_number: str) -> Dict[str, Any]:
        """Toggles a slot between AVAILABLE and RESERVED (for admin management)."""
        slot = session.query(ParkingSlot).filter_by(slot_number=slot_number).first()
        if not slot:
            return {"success": False, "message": f"Slot {slot_number} not found"}
        if slot.status == "OCCUPIED":
            return {"success": False, "message": f"Cannot reserve occupied slot {slot_number}"}

        if slot.status == "AVAILABLE":
            slot.status = "RESERVED"
            message = f"Slot {slot_number} reserved successfully"
        else:
            slot.status = "AVAILABLE"
            message = f"Slot {slot_number} is now available"

        session.flush()
        return {"success": True, "status": slot.status, "message": message}
