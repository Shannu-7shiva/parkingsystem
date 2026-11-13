import sys
import random
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash
from database.database import init_db, get_db
from database.models import User, Vehicle, ParkingSlot, ParkingRecord, Blacklist, SystemSetting
import config


# Realistic Master Dataset of Indian Vehicles
SAMPLE_VEHICLES_DATA = [
    {"plate": "TN09AB1234", "type": "car", "model": "Honda City 1.5 i-VTEC", "owner": "Ramesh Kumar", "phone": "+91 98765 43210", "color": "#4A90E2", "blacklisted": False},
    {"plate": "TN10CD5678", "type": "car", "model": "Hyundai Creta SX(O)", "owner": "Priya Sharma", "phone": "+91 98451 23456", "color": "#E74C3C", "blacklisted": False},
    {"plate": "KA01AB7890", "type": "car", "model": "Maruti Baleno Alpha", "owner": "Karthik Subramanian", "phone": "+91 99001 12233", "color": "#F39C12", "blacklisted": False},
    {"plate": "KA05MH8821", "type": "car", "model": "Kia Seltos GTX+", "owner": "Sneha Patil", "phone": "+91 98860 55443", "color": "#2C3E50", "blacklisted": False},
    {"plate": "MH02CD4455", "type": "car", "model": "Mahindra Thar 4x4", "owner": "Rohit Sharma", "phone": "+91 98200 44556", "color": "#16A085", "blacklisted": False},
    {"plate": "MH12DE3456", "type": "car", "model": "Toyota Innova Crysta", "owner": "Sunil Patil", "phone": "+91 98220 11223", "color": "#7F8C8D", "blacklisted": False},
    {"plate": "TS09PQ2345", "type": "ev", "model": "Tata Nexon EV Max", "owner": "Vikram Reddy", "phone": "+91 91234 56789", "color": "#2ECC71", "blacklisted": False},
    {"plate": "DL03CC1001", "type": "car", "model": "BMW 330i M Sport", "owner": "Dr. Arjun Malhotra", "phone": "+91 98110 99887", "color": "#2980B9", "blacklisted": False},
    {"plate": "AP28XY4567", "type": "motorcycle", "model": "Royal Enfield Hunter 350", "owner": "Ananya Rao", "phone": "+91 97123 45678", "color": "#34495E", "blacklisted": False},
    {"plate": "KA03JK6712", "type": "motorcycle", "model": "Ather 450X Gen 3", "owner": "Gautam Menon", "phone": "+91 99800 33221", "color": "#27AE60", "blacklisted": False},
    {"plate": "UP16AK9021", "type": "car", "model": "Maruti Suzuki Swift ZXi+", "owner": "Amit Chaudhary", "phone": "+91 98101 22334", "color": "#D35400", "blacklisted": False},
    {"plate": "HR26DK4009", "type": "car", "model": "Mahindra XUV700 AX7L", "owner": "Vikas Hooda", "phone": "+91 98120 77665", "color": "#34495E", "blacklisted": False},
    {"plate": "GJ01LM5566", "type": "car", "model": "Tata Punch Creative", "owner": "Bhavin Patel", "phone": "+91 98980 11223", "color": "#E67E22", "blacklisted": False},
    {"plate": "KL07BN3344", "type": "car", "model": "Volkswagen Virtus GT", "owner": "Mathew Varghese", "phone": "+91 98470 55667", "color": "#C0392B", "blacklisted": False},
    {"plate": "WB02AZ7788", "type": "car", "model": "Tata Harrier Dark Edition", "owner": "Sourav Banerjee", "phone": "+91 98300 44332", "color": "#111111", "blacklisted": False},
    {"plate": "22BH1982AA", "type": "car", "model": "Skoda Slavia Style", "owner": "Capt. Rajeev Nair", "phone": "+91 94440 12345", "color": "#8E44AD", "blacklisted": False},
    {"plate": "TG03A7349", "type": "motorcycle", "model": "Royal Enfield Classic 350", "owner": "Shiva (Owner)", "phone": "+91 98765 43210", "color": "#1A252F", "blacklisted": False},
    {"plate": "AP39CJ5337", "type": "car", "model": "Volkswagen Polo GT TSI (Red)", "owner": "Shiva (Owner)", "phone": "+91 98765 43210", "color": "#E74C3C", "blacklisted": False},
    {"plate": "AP39CJ5327", "type": "car", "model": "Volkswagen Polo GT TSI (Red)", "owner": "Shiva (Owner)", "phone": "+91 98765 43210", "color": "#E74C3C", "blacklisted": False},
    {"plate": "DL01ZA9999", "type": "car", "model": "Mahindra Scorpio-N", "owner": "Security Intercept Record", "phone": "+91 90000 00000", "color": "#111111", "blacklisted": True},
    {"plate": "MH12AB0000", "type": "car", "model": "Commercial Van", "owner": "Suspended Fleet License", "phone": "+91 90000 00001", "color": "#7F8C8D", "blacklisted": True},
    {"plate": "KA04XY0007", "type": "car", "model": "Honda Civic (Stolen Alert)", "owner": "Cybercrime Interpol Alert", "phone": "+91 90000 00002", "color": "#34495E", "blacklisted": True},
]


def seed_database(reset=False):
    """Initializes schema and populates rich, realistic parking data."""
    from database.database import reset_db
    if reset:
        print("[INFO] Resetting existing database schema and records...")
        reset_db()
    else:
        init_db()

    with get_db() as session:
        admin_user = session.query(User).filter_by(username="admin").first()
        if admin_user and not reset:
            print("[INFO] Database already seeded. Skipping initial seeding.")
            return

        # 1. Admin & Operator Users
        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            created_at=datetime.now()
        )
        operator = User(
            username="operator",
            password_hash=generate_password_hash("operator123"),
            role="operator",
            created_at=datetime.now()
        )
        session.add_all([admin, operator])

        # 2. System Settings
        settings = [
            SystemSetting(setting_name="PARKING_FIRST_HOUR_RATE", setting_value="30.0"),
            SystemSetting(setting_name="PARKING_ADDITIONAL_HOUR_RATE", setting_value="20.0"),
            SystemSetting(setting_name="GRACE_PERIOD_MINUTES", setting_value="5.0"),
            SystemSetting(setting_name="GST_PERCENTAGE", setting_value="18.0"),
            SystemSetting(setting_name="CURRENCY_SYMBOL", setting_value="₹"),
            SystemSetting(setting_name="PARKING_LOT_NAME", setting_value="ParkVision Smart AI Terminal 01"),
            SystemSetting(setting_name="FASTAG_AUTO_DEBIT", setting_value="ENABLED"),
            SystemSetting(setting_name="TOTAL_CAPACITY", setting_value="15"),
        ]
        session.add_all(settings)

        # 3. Create Vehicles
        created_vehicles = {}
        for vd in SAMPLE_VEHICLES_DATA:
            v = Vehicle(
                plate_number=vd["plate"],
                vehicle_type=vd["type"],
                model=vd["model"],
                color=vd["color"],
                owner_name=vd["owner"],
                phone=vd["phone"],
                fastag_id=f"FTAG-{vd['plate'][:4]}-{random.randint(1000, 9999)}",
                is_blacklisted=vd["blacklisted"],
                created_at=datetime.now() - timedelta(days=random.randint(5, 20))
            )
            session.add(v)
            created_vehicles[vd["plate"]] = v

        session.flush()

        # 4. Blacklist Entries
        bl1 = Blacklist(
            plate_number="DL01ZA9999",
            reason="Traffic Police Alert: Multiple reckless speeding and red light violations across NCR",
            created_at=datetime.now() - timedelta(days=6)
        )
        bl2 = Blacklist(
            plate_number="MH12AB0000",
            reason="Toll Evasion & Commercial permit revocation by RTO Pune",
            created_at=datetime.now() - timedelta(days=12)
        )
        bl3 = Blacklist(
            plate_number="KA04XY0007",
            reason="Stolen vehicle broadcast flagged by Bengaluru City Cyber Crime",
            created_at=datetime.now() - timedelta(days=3)
        )
        session.add_all([bl1, bl2, bl3])

        # 5. Parking Slots (12 Normal, 1 VIP, 1 EV, 1 Disabled)
        slot_definitions = [
            ("P01", "NORMAL", "G"),
            ("P02", "NORMAL", "G"),
            ("P03", "NORMAL", "G"),
            ("P04", "NORMAL", "G"),
            ("P05", "NORMAL", "G"),
            ("P06", "NORMAL", "G"),
            ("P07", "NORMAL", "G"),
            ("P08", "NORMAL", "G"),
            ("P09", "NORMAL", "G"),
            ("P10", "NORMAL", "G"),
            ("P11", "NORMAL", "G"),
            ("P12", "NORMAL", "G"),
            ("VIP01", "VIP", "G"),
            ("EV01", "EV", "G"),
            ("DIS01", "DISABLED", "G"),
        ]

        created_slots = {}
        for s_num, s_type, floor in slot_definitions:
            slot = ParkingSlot(
                slot_number=s_num,
                slot_type=s_type,
                floor=floor,
                status="AVAILABLE",
                vehicle_id=None
            )
            session.add(slot)
            created_slots[s_num] = slot

        session.flush()

        # 6. Seed Realistic Multi-Day Historical Parking Records (Past 7 Days)
        now = datetime.now()
        records_to_add = []
        payment_modes = ["Fastag Auto-Debit", "UPI / QR Code", "Credit/Debit Card", "Fastag Auto-Debit", "Cash Counter"]

        # Generate realistic traffic over 7 days
        eligible_vehicles = [v for v in SAMPLE_VEHICLES_DATA if not v["blacklisted"]]

        for days_ago in range(6, 0, -1):
            daily_vehicle_count = random.randint(6, 11)
            for _ in range(daily_vehicle_count):
                v_data = random.choice(eligible_vehicles)
                veh = created_vehicles[v_data["plate"]]
                # Pick realistic parking arrival hour (8 AM to 9 PM)
                arr_hour = random.randint(8, 20)
                arr_minute = random.randint(0, 59)
                entry_dt = (now - timedelta(days=days_ago)).replace(hour=arr_hour, minute=arr_minute, second=0)

                # Duration between 25 and 280 minutes
                duration = round(random.uniform(25.0, 275.0), 1)
                exit_dt = entry_dt + timedelta(minutes=duration)

                # Billing
                extra_hours = max(0, int((duration - 60) // 60) + (1 if (duration - 60) % 60 > 0 else 0)) if duration > 5 else 0
                base_first = 15.0 if v_data["type"] == "motorcycle" else (25.0 if v_data["type"] == "ev" else 30.0)
                base_add = 10.0 if v_data["type"] == "motorcycle" else (15.0 if v_data["type"] == "ev" else 20.0)
                base_total = 0.0 if duration <= 5 else (base_first + extra_hours * base_add)
                total_with_tax = round(base_total * 1.18, 2)

                slot_choice = random.choice(["P01", "P03", "P04", "P06", "P07", "P09", "P10", "P11", "P12"])

                rec = ParkingRecord(
                    vehicle_id=veh.id,
                    plate_number=veh.plate_number,
                    slot_number=slot_choice,
                    entry_time=entry_dt,
                    exit_time=exit_dt,
                    duration_minutes=duration,
                    amount=total_with_tax,
                    status="COMPLETED",
                    payment_mode=random.choice(payment_modes),
                    receipt_number=f"REC-{entry_dt.strftime('%y%m%d')}-{random.randint(1000, 9999)}",
                    entry_image="/uploads/vehicles/snap_demo.jpg",
                    exit_image="/uploads/vehicles/snap_demo.jpg",
                    created_at=entry_dt
                )
                records_to_add.append(rec)

        # 7. Active Currently Parked Vehicles (Realistic Occupancy: 5 bays occupied)
        currently_parked = [
            ("TN09AB1234", "P02", 95.0),   # Honda City in P02 for 1h 35m
            ("KA05MH8821", "P05", 140.0),  # Kia Seltos in P05 for 2h 20m
            ("MH02CD4455", "P08", 45.0),   # Thar in P08 for 45m
            ("TS09PQ2345", "EV01", 110.0), # Nexon EV in EV01 for 1h 50m
            ("DL03CC1001", "VIP01", 75.0), # BMW in VIP01 for 1h 15m
        ]

        for plate, s_num, elapsed_mins in currently_parked:
            v_obj = created_vehicles[plate]
            entry_dt = now - timedelta(minutes=elapsed_mins)

            active_rec = ParkingRecord(
                vehicle_id=v_obj.id,
                plate_number=v_obj.plate_number,
                slot_number=s_num,
                entry_time=entry_dt,
                exit_time=None,
                duration_minutes=elapsed_mins,
                amount=50.0,
                status="PARKED",
                payment_mode="Pending Checkout",
                receipt_number=f"TCK-{now.strftime('%y%m%d')}-{s_num}",
                entry_image="/uploads/vehicles/snap_demo.jpg",
                created_at=entry_dt
            )
            records_to_add.append(active_rec)

            # Update slot status
            created_slots[s_num].status = "OCCUPIED"
            created_slots[s_num].vehicle_id = v_obj.id

        session.add_all(records_to_add)
        session.flush()

        print(f"[SUCCESS] Database seeded with {len(SAMPLE_VEHICLES_DATA)} vehicles, {len(slot_definitions)} slots, and {len(records_to_add)} realistic parking sessions.")


if __name__ == "__main__":
    seed_database(reset=True)
