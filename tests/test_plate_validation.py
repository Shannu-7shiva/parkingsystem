import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anpr.plate_processor import PlateProcessor


class TestPlateValidation(unittest.TestCase):
    def test_standard_indian_plate(self):
        res = PlateProcessor.validate_and_format("TN09AB1234")
        self.assertTrue(res["valid"])
        self.assertEqual(res["cleaned_plate"], "TN09AB1234")
        self.assertEqual(res["state_code"], "TN")
        self.assertEqual(res["rto_code"], "09")
        self.assertEqual(res["series"], "AB")
        self.assertEqual(res["number"], "1234")
        self.assertTrue(res["is_indian_format"])
        self.assertTrue(res["is_valid_state"])

    def test_plate_with_spaces_and_hyphens(self):
        res = PlateProcessor.validate_and_format("KA - 01 - MB - 5678")
        self.assertTrue(res["valid"])
        self.assertEqual(res["cleaned_plate"], "KA01MB5678")
        self.assertEqual(res["state_code"], "KA")

    def test_ocr_artifact_correction(self):
        # 'O' instead of '0' in RTO code, 'B' instead of '8' in numbers
        res = PlateProcessor.validate_and_format("TN O9 AB 123B")
        self.assertTrue(res["valid"])
        self.assertEqual(res["cleaned_plate"], "TN09AB1238")

    def test_bharat_series(self):
        res = PlateProcessor.validate_and_format("22BH1234AA")
        self.assertTrue(res["valid"])
        self.assertEqual(res["cleaned_plate"], "22BH1234AA")
        self.assertEqual(res["state_code"], "BH")

    def test_invalid_short_noise(self):
        res = PlateProcessor.validate_and_format("ABC")
        self.assertFalse(res["valid"])


if __name__ == "__main__":
    unittest.main()
