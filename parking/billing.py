import math
import uuid
from typing import Dict, Any, Optional
from database.database import get_db
from database.models import SystemSetting
import config


class BillingCalculator:
    """Calculates parking duration and pricing based on configurable hourly rates and vehicle tiers."""

    @staticmethod
    def get_rate_settings(vehicle_type: str = "car") -> Dict[str, float]:
        """Fetches active rates from TARIFF_BY_VEHICLE_TYPE config or database overrides."""
        v_clean = (vehicle_type or "car").lower()
        tariff = config.TARIFF_BY_VEHICLE_TYPE.get(v_clean, config.TARIFF_BY_VEHICLE_TYPE.get("car", {"first_hour": 30.0, "additional_hour": 20.0}))
        first_hour = float(tariff["first_hour"])
        additional_hour = float(tariff["additional_hour"])
        grace_period = config.GRACE_PERIOD_MINUTES

        try:
            with get_db() as session:
                # Check vehicle-specific override first, e.g. PARKING_FIRST_HOUR_RATE_MOTORCYCLE
                v_key = f"PARKING_FIRST_HOUR_RATE_{v_clean.upper()}"
                s_v = session.query(SystemSetting).filter_by(setting_name=v_key).first()
                if s_v:
                    first_hour = float(s_v.setting_value)
                elif v_clean == "car":
                    s1 = session.query(SystemSetting).filter_by(setting_name="PARKING_FIRST_HOUR_RATE").first()
                    if s1:
                        first_hour = float(s1.setting_value)

                v_add_key = f"PARKING_ADDITIONAL_HOUR_RATE_{v_clean.upper()}"
                s_add_v = session.query(SystemSetting).filter_by(setting_name=v_add_key).first()
                if s_add_v:
                    additional_hour = float(s_add_v.setting_value)
                elif v_clean == "car":
                    s2 = session.query(SystemSetting).filter_by(setting_name="PARKING_ADDITIONAL_HOUR_RATE").first()
                    if s2:
                        additional_hour = float(s2.setting_value)

                s3 = session.query(SystemSetting).filter_by(setting_name="GRACE_PERIOD_MINUTES").first()
                if s3:
                    grace_period = float(s3.setting_value)
        except Exception:
            pass

        return {
            "first_hour_rate": first_hour,
            "additional_hour_rate": additional_hour,
            "grace_period_minutes": grace_period,
            "gst_percentage": config.GST_PERCENTAGE
        }

    @classmethod
    def calculate_bill(
        cls,
        duration_minutes: float,
        vehicle_type: str = "car",
        payment_mode: str = "Fastag Auto-Debit"
    ) -> Dict[str, Any]:
        """
        Calculates fee given parking duration in minutes.
        Rounding:
        - <= grace period: ₹0.0
        - <= 60 mins: first_hour_rate (₹30.0)
        - > 60 mins: first_hour_rate + ceil((duration - 60) / 60) * additional_hour_rate (₹20.0/hr)
        """
        rates = cls.get_rate_settings(vehicle_type)
        first_hour_rate = rates["first_hour_rate"]
        additional_hour_rate = rates["additional_hour_rate"]
        grace_period = rates["grace_period_minutes"]
        gst_pct = rates["gst_percentage"]

        duration_minutes = max(0.0, float(duration_minutes))

        if duration_minutes <= grace_period:
            amount = 0.0
            hours_charged = 0
        elif duration_minutes <= 60.0:
            amount = first_hour_rate
            hours_charged = 1
        else:
            extra_minutes = duration_minutes - 60.0
            extra_hours = math.ceil(extra_minutes / 60.0)
            amount = first_hour_rate + (extra_hours * additional_hour_rate)
            hours_charged = 1 + extra_hours

        # Format duration string
        hours = int(duration_minutes // 60)
        mins = int(duration_minutes % 60)
        formatted_duration = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"

        # Itemized tax computation (inclusive GST 18%)
        net_taxable = round(amount / (1 + (gst_pct / 100.0)), 2) if amount > 0 else 0.0
        gst_amount = round(amount - net_taxable, 2)

        # Receipt reference ID
        receipt_id = f"REC-{uuid.uuid4().hex[:8].upper()}"
        fastag_ref = f"FTAG-IND-{uuid.uuid4().hex[:6].upper()}" if "fastag" in payment_mode.lower() else None

        return {
            "duration_minutes": round(duration_minutes, 1),
            "formatted_duration": formatted_duration,
            "hours_charged": hours_charged,
            "amount": round(amount, 2),
            "base_amount": net_taxable,
            "gst_amount": gst_amount,
            "currency": "₹",
            "receipt_id": receipt_id,
            "payment_mode": payment_mode,
            "fastag_ref": fastag_ref,
            "vehicle_type": vehicle_type,
            "rates_applied": {
                "first_hour": first_hour_rate,
                "additional_hour": additional_hour_rate,
                "grace_period": grace_period,
                "gst_percentage": gst_pct
            }
        }
