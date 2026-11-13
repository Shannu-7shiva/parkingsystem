from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def current_time():
    return datetime.now()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin", nullable=False)  # admin, operator, viewer
    created_at = Column(DateTime, default=current_time)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(30), default="car", nullable=False)  # car, motorcycle, bus, truck, auto, ev
    model = Column(String(80), default="Sedan / Hatchback")
    color = Column(String(30), default="#4A90E2")
    owner_name = Column(String(100), default="Guest / Visitor")
    phone = Column(String(20), default="")
    fastag_id = Column(String(50), default="")
    is_blacklisted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=current_time)
    updated_at = Column(DateTime, default=current_time, onupdate=current_time)

    parking_records = relationship("ParkingRecord", back_populates="vehicle", cascade="all, delete-orphan")
    active_slot = relationship("ParkingSlot", back_populates="current_vehicle", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "vehicle_type": self.vehicle_type,
            "model": self.model or "Vehicle",
            "color": self.color or "#4A90E2",
            "owner_name": self.owner_name,
            "phone": self.phone,
            "fastag_id": self.fastag_id or f"FTAG-{self.plate_number[:4]}-{(self.id or 100):04d}",
            "is_blacklisted": self.is_blacklisted,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_number = Column(String(20), unique=True, nullable=False, index=True)
    slot_type = Column(String(30), default="NORMAL", nullable=False)  # NORMAL, VIP, EV, DISABLED
    status = Column(String(30), default="AVAILABLE", nullable=False)   # AVAILABLE, OCCUPIED, RESERVED, MAINTENANCE
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    floor = Column(String(10), default="G")
    created_at = Column(DateTime, default=current_time)
    updated_at = Column(DateTime, default=current_time, onupdate=current_time)

    current_vehicle = relationship("Vehicle", back_populates="active_slot")

    def to_dict(self):
        return {
            "id": self.id,
            "slot_number": self.slot_number,
            "slot_type": self.slot_type,
            "status": self.status,
            "vehicle_id": self.vehicle_id,
            "vehicle_plate": self.current_vehicle.plate_number if self.current_vehicle else None,
            "vehicle_type": self.current_vehicle.vehicle_type if self.current_vehicle else None,
            "vehicle_model": self.current_vehicle.model if self.current_vehicle else None,
            "owner_name": self.current_vehicle.owner_name if self.current_vehicle else None,
            "floor": self.floor or "G",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ParkingRecord(Base):
    __tablename__ = "parking_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    plate_number = Column(String(20), nullable=False, index=True)
    slot_number = Column(String(20), nullable=False, index=True)
    entry_time = Column(DateTime, default=current_time, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    status = Column(String(30), default="PARKED", nullable=False)  # PARKED, COMPLETED
    payment_mode = Column(String(50), default="Fastag Auto-Debit")  # Fastag Auto-Debit, UPI, Cash, Card
    receipt_number = Column(String(50), nullable=True)
    entry_image = Column(String(255), nullable=True)
    exit_image = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=current_time)

    vehicle = relationship("Vehicle", back_populates="parking_records")

    def to_dict(self):
        hours = int(self.duration_minutes // 60) if self.duration_minutes else 0
        mins = int(self.duration_minutes % 60) if self.duration_minutes else 0
        formatted_dur = f"{hours}h {mins}m" if hours > 0 else (f"{mins} mins" if self.duration_minutes else "Active")

        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "plate_number": self.plate_number,
            "slot_number": self.slot_number,
            "entry_time": self.entry_time.strftime("%Y-%m-%d %H:%M:%S") if self.entry_time else None,
            "exit_time": self.exit_time.strftime("%Y-%m-%d %H:%M:%S") if self.exit_time else None,
            "duration_minutes": round(self.duration_minutes, 1) if self.duration_minutes else 0.0,
            "duration_formatted": formatted_dur,
            "amount": round(self.amount, 2),
            "status": self.status,
            "payment_mode": self.payment_mode or "Fastag Auto-Debit",
            "receipt_number": self.receipt_number or f"REC-2026-{self.id:05d}",
            "entry_image": self.entry_image,
            "exit_image": self.exit_image,
            "vehicle_type": self.vehicle.vehicle_type if self.vehicle else "car",
            "owner_name": self.vehicle.owner_name if self.vehicle else "Visitor",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class Blacklist(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), unique=True, nullable=False, index=True)
    reason = Column(Text, default="Unauthorized or flagged vehicle")
    created_at = Column(DateTime, default=current_time)

    def to_dict(self):
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "reason": self.reason,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_name = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(255), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "setting_name": self.setting_name,
            "setting_value": self.setting_value,
        }
