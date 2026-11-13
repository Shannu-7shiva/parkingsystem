import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from database.seed import seed_database


class TestWebRoutes(unittest.TestCase):
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

    def test_login_page_renders(self):
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"ParkVision ANPR", res.data)

    def test_protected_routes_render_when_logged_in(self):
        self.login()
        routes = [
            "/dashboard",
            "/live-camera",
            "/parking-lot",
            "/vehicles",
            "/parking-history",
            "/analytics",
            "/blacklist",
            "/settings"
        ]
        for route in routes:
            with self.subTest(route=route):
                res = self.client.get(route)
                self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
