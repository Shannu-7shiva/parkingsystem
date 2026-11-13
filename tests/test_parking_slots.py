import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.database import get_db
from database.seed import seed_database
from parking.slot_manager import SlotManager
from parking.entry_manager import EntryManager
from parking.exit_manager import ExitManager
from parking.parking_service import ParkingService


class TestParkingSlots(unittest.TestCase):
    def setUp(self):
        seed_database(reset=True)

    def test_entry_allocation_and_exit(self):
        with get_db() as session:
            # P01 is available initially
            entry_res = EntryManager.process_entry(
                session=session,
                plate_number="KA05MN1234",
                vehicle_type="car"
            )
            self.assertTrue(entry_res["success"])
            self.assertEqual(entry_res["action"], "ENTRY")
            slot_num = entry_res["slot_number"]
            self.assertEqual(slot_num, "P01")

        with get_db() as session:
            # Check slot is occupied and find next available
            next_slot = SlotManager.find_available_slot(session)
            self.assertIsNotNone(next_slot)
            # Try duplicate entry
            dup_res = EntryManager.process_entry(
                session=session,
                plate_number="KA05MN1234",
                vehicle_type="car"
            )
            self.assertFalse(dup_res["success"])
            self.assertTrue(dup_res.get("already_parked"))

            # Process exit
            exit_res = ExitManager.process_exit(
                session=session,
                plate_number="KA05MN1234",
                simulated_duration_minutes=90.0
            )
            self.assertTrue(exit_res["success"])
            self.assertEqual(exit_res["action"], "EXIT")
            self.assertEqual(exit_res["amount"], 50.0)

    def test_blacklist_rejection(self):
        with get_db() as session:
            bl_res = EntryManager.process_entry(
                session=session,
                plate_number="DL01ZA9999",  # Seeded as blacklisted
                vehicle_type="car"
            )
            self.assertFalse(bl_res["success"])
            self.assertTrue(bl_res["blacklisted"])


if __name__ == "__main__":
    unittest.main()
