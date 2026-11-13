import unittest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from database.seed import seed_database


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(reset=True)
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def login(self):
        return self.client.post("/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)

    def test_unauthenticated_api_access(self):
        unauth_client = self.app.test_client()
        res = unauth_client.get("/api/dashboard")
        self.assertEqual(res.status_code, 401)

    def test_dashboard_api(self):
        self.login()
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("summary", data["data"])
        self.assertIn("slots", data["data"])

    def test_parking_slots_api(self):
        self.login()
        res = self.client.get("/api/parking-slots")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["slots"]), 12)

    def test_simulation_entry_and_exit_api(self):
        self.login()
        # Simulate Entry
        entry_res = self.client.post("/api/simulate-entry", json={
            "plate_number": "KA02CD1111",
            "vehicle_type": "car"
        })
        self.assertEqual(entry_res.status_code, 200)
        entry_data = json.loads(entry_res.data)
        self.assertTrue(entry_data["success"])

        # Simulate Exit
        exit_res = self.client.post("/api/simulate-exit", json={
            "plate_number": "KA02CD1111",
            "duration_minutes": 65.0
        })
        self.assertEqual(exit_res.status_code, 200)
        exit_data = json.loads(exit_res.data)
        self.assertTrue(exit_data["success"])

    def test_blacklist_api(self):
        self.login()
        res = self.client.get("/api/blacklist")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["blacklist"]), 1)

    def test_tariffs_api(self):
        self.login()
        res = self.client.get("/api/tariffs")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("tariffs", data)

    def test_receipt_api(self):
        self.login()
        # Get parking history to find a completed record
        res = self.client.get("/api/parking-history?status=COMPLETED")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        if data["records"]:
            rec_id = data["records"][0]["id"]
            rec_res = self.client.get(f"/api/parking-records/{rec_id}/receipt")
            self.assertEqual(rec_res.status_code, 200)
            rec_data = json.loads(rec_res.data)
            self.assertTrue(rec_data["success"])
            self.assertIn("receipt_number", rec_data["receipt"])
            self.assertIn("total_amount", rec_data["receipt"])


if __name__ == "__main__":
    unittest.main()
