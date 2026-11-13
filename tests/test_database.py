import unittest
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database import init_db, get_db
from database.models import User, Vehicle, ParkingSlot, ParkingRecord, Blacklist, SystemSetting
from database.seed import seed_database


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(reset=True)

    def test_admin_user_exists(self):
        with get_db() as session:
            admin = session.query(User).filter_by(username="admin").first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, "admin")

    def test_slots_seeded(self):
        with get_db() as session:
            slots = session.query(ParkingSlot).all()
            self.assertGreaterEqual(len(slots), 12)
            slot_p01 = session.query(ParkingSlot).filter_by(slot_number="P01").first()
            self.assertIsNotNone(slot_p01)
            self.assertEqual(slot_p01.slot_type, "NORMAL")

    def test_sample_vehicles_and_blacklist(self):
        with get_db() as session:
            vehicle = session.query(Vehicle).filter_by(plate_number="TN09AB1234").first()
            self.assertIsNotNone(vehicle)
            blacklisted = session.query(Blacklist).filter_by(plate_number="DL01ZA9999").first()
            self.assertIsNotNone(blacklisted)


if __name__ == "__main__":
    unittest.main()
