import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parking.billing import BillingCalculator
from database.seed import seed_database


class TestBilling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_database(reset=True)

    def test_grace_period(self):
        bill = BillingCalculator.calculate_bill(4.0)
        self.assertEqual(bill["amount"], 0.0)
        self.assertEqual(bill["hours_charged"], 0)

    def test_first_hour(self):
        bill = BillingCalculator.calculate_bill(45.0)
        self.assertEqual(bill["amount"], 30.0)
        self.assertEqual(bill["hours_charged"], 1)

    def test_second_hour(self):
        bill = BillingCalculator.calculate_bill(75.0)
        # First hour = 30 + 1 additional hour @ 20 = 50
        self.assertEqual(bill["amount"], 50.0)
        self.assertEqual(bill["hours_charged"], 2)

    def test_third_hour(self):
        bill = BillingCalculator.calculate_bill(135.0)
        # First hour = 30 + 2 additional hours @ 20 = 70
        self.assertEqual(bill["amount"], 70.0)
        self.assertEqual(bill["hours_charged"], 3)


if __name__ == "__main__":
    unittest.main()
