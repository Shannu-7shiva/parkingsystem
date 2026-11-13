import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
import time
from typing import Dict, Any, List, Tuple
from anpr.image_processor import ImageProcessor
from anpr.plate_processor import PlateProcessor
from anpr.ocr_engine import OCREngine, get_char_templates
from anpr.multi_frame_tracker import MultiFrameTracker


def generate_synthetic_plate_image(text: str, width: int = 240, height: int = 60) -> np.ndarray:
    """Generates a standard Indian high-security registration plate (HSRP) synthetic image."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 245
    # Outer black plate border
    cv2.rectangle(img, (2, 2), (width - 3, height - 3), (20, 20, 20), 2)
    # Blue IND stripe on left
    cv2.rectangle(img, (3, 3), (24, height - 4), (180, 70, 20), -1)
    cv2.putText(img, "IND", (5, height // 2 + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (255, 255, 255), 1)

    # Render license plate text
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.95
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    tx = 32 + max(0, (width - 40 - tw) // 2)
    ty = (height + th) // 2 - 1
    cv2.putText(img, text, (tx, ty), font, scale, (15, 15, 15), thickness, cv2.LINE_AA)
    return img


def apply_blur(img: np.ndarray, ksize: int = 5) -> np.ndarray:
    """Simulates motion blur or out-of-focus camera capture."""
    return cv2.GaussianBlur(img, (ksize, ksize), 0)


def apply_low_light(img: np.ndarray, factor: float = 0.35) -> np.ndarray:
    """Simulates night-time or poorly illuminated entry gate lighting."""
    return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def apply_tilt(img: np.ndarray, angle: float = 8.0) -> np.ndarray:
    """Simulates angled or tilted license plate mounting."""
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def apply_noise(img: np.ndarray, noise_level: float = 0.05) -> np.ndarray:
    """Simulates road grime, dirt, or camera sensor digital noise."""
    noisy = img.copy()
    num_noise = int(noise_level * img.shape[0] * img.shape[1])
    for _ in range(num_noise):
        y = np.random.randint(0, img.shape[0])
        x = np.random.randint(0, img.shape[1])
        noisy[y, x] = [np.random.randint(0, 50), np.random.randint(0, 50), np.random.randint(0, 50)]
    return noisy


class ANPRTestSuite:
    """
    Automated Benchmark & Verification Suite for ParkVision ANPR.
    Measures character-level accuracy and complete plate-level accuracy
    across diverse real-world environmental conditions.
    """

    TEST_DATASET = [
        {"ground_truth": "TS09AB1234", "category": "Clear Daytime"},
        {"ground_truth": "AP39CD4567", "category": "Clear Daytime"},
        {"ground_truth": "KA01MN1234", "category": "Clear Daytime"},
        {"ground_truth": "TN10AB1234", "category": "Clear Daytime"},
        {"ground_truth": "MH12EF1234", "category": "Clear Daytime"},
        {"ground_truth": "DL8CAF1234", "category": "Single Digit RTO"},
        {"ground_truth": "22BH1234AA", "category": "Bharat Series"},
        {"ground_truth": "TG03A7349",  "category": "Telangana Motorcycle"},
        {"ground_truth": "AP39CJ5337", "category": "Fleet Vehicle"},
    ]

    @classmethod
    def run_benchmark(cls) -> Dict[str, Any]:
        """Runs comprehensive test suite across environmental variations and prints benchmark."""
        total_plates = 0
        correct_plates = 0
        total_chars = 0
        correct_chars = 0

        results: List[Dict[str, Any]] = []

        print("\n=========================================================================")
        print("          PARKVISION ANPR BENCHMARK & ACCURACY VERIFICATION              ")
        print("=========================================================================")

        # Condition generators
        conditions = [
            ("Standard", lambda x: x),
            ("Tilted 7deg", lambda x: apply_tilt(x, 7.0)),
            ("Low-Light", lambda x: apply_low_light(x, 0.40)),
            ("Blurry", lambda x: apply_blur(x, 3)),
            ("Noisy/Dirty", lambda x: apply_noise(x, 0.03)),
        ]

        for item in cls.TEST_DATASET:
            gt = item["ground_truth"]
            cat = item["category"]

            # Generate base clean plate
            base_plate = generate_synthetic_plate_image(gt)

            for cond_name, cond_fn in conditions:
                test_img = cond_fn(base_plate)
                deskewed = ImageProcessor.correct_perspective_and_deskew(test_img)
                ocr_out = OCREngine.recognize_plate_text(deskewed)

                raw_rec = ocr_out.get("raw_text") or ""
                cleaned_rec = ocr_out.get("cleaned_plate") or ""
                conf = ocr_out.get("confidence", 0.0)

                # Character-level matching
                n_gt = len(gt)
                c_matches = sum(1 for a, b in zip(cleaned_rec, gt) if a == b) if len(cleaned_rec) == n_gt else 0

                is_exact = (cleaned_rec == gt)
                total_plates += 1
                if is_exact:
                    correct_plates += 1

                total_chars += n_gt
                correct_chars += c_matches

                results.append({
                    "ground_truth": gt,
                    "condition": cond_name,
                    "category": cat,
                    "predicted": cleaned_rec,
                    "exact_match": is_exact,
                    "char_accuracy": round((c_matches / n_gt) * 100, 1),
                    "confidence": conf
                })

        plate_acc = round((correct_plates / total_plates) * 100, 2)
        char_acc = round((correct_chars / total_chars) * 100, 2)

        print(f"Total Test Cases Evaluated : {total_plates}")
        print(f"Plate-Level Exact Accuracy : {plate_acc}% ({correct_plates}/{total_plates})")
        print(f"Character-Level Accuracy   : {char_acc}% ({correct_chars}/{total_chars})")
        print("=========================================================================\n")

        return {
            "total_tested": total_plates,
            "plate_accuracy_pct": plate_acc,
            "char_accuracy_pct": char_acc,
            "details": results
        }


if __name__ == "__main__":
    ANPRTestSuite.run_benchmark()
