import cv2
import numpy as np
from datetime import datetime
from typing import Tuple, Optional


class VirtualCamera:
    """Generates synthetic high-resolution camera frames featuring vehicles and license plates."""

    @classmethod
    def generate_vehicle_frame(
        cls,
        plate_text: str = "TN09AB1234",
        vehicle_color: Tuple[int, int, int] = (180, 50, 40),  # BGR
        vehicle_type: str = "car",
        gate_status: str = "ENTRY GATE 01",
        width: int = 800,
        height: int = 500
    ) -> np.ndarray:
        """
        Synthesizes a realistic parking entry lane scene with a vehicle and high-contrast Indian plate.
        """
        # 1. Background tarmac / lane
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Gradient background (parking garage entry lane)
        for y in range(height):
            c_val = int(35 + (y / height) * 45)
            frame[y, :] = (c_val, c_val + 2, c_val + 5)

        # Lane markings
        cv2.line(frame, (80, height), (220, int(height * 0.3)), (240, 240, 240), 4)
        cv2.line(frame, (width - 80, height), (width - 220, int(height * 0.3)), (240, 240, 240), 4)
        cv2.line(frame, (width // 2, height), (width // 2, int(height * 0.7)), (0, 220, 255), 3)

        # 2. Draw Vehicle Body
        car_cx = width // 2
        car_cy = int(height * 0.58)
        car_w = int(width * 0.55)
        car_h = int(height * 0.45)

        x1 = car_cx - (car_w // 2)
        y1 = car_cy - (car_h // 2)
        x2 = car_cx + (car_w // 2)
        y2 = car_cy + (car_h // 2)

        # Wheels / Shadow
        cv2.ellipse(frame, (car_cx, y2 + 10), (car_w // 2 + 20, 25), 0, 0, 360, (15, 15, 15), -1)
        cv2.rectangle(frame, (x1 + 15, y2 - 25), (x1 + 65, y2 + 15), (20, 20, 20), -1)
        cv2.rectangle(frame, (x2 - 65, y2 - 25), (x2 - 15, y2 + 15), (20, 20, 20), -1)

        # Main Chassis / Bumper
        cv2.rectangle(frame, (x1, y1 + int(car_h * 0.35)), (x2, y2), vehicle_color, -1)
        # Curved Roof / Windshield
        roof_pts = np.array([
            [x1 + 45, y1 + int(car_h * 0.35)],
            [x1 + 95, y1],
            [x2 - 95, y1],
            [x2 - 45, y1 + int(car_h * 0.35)]
        ], np.int32)
        cv2.fillPoly(frame, [roof_pts], vehicle_color)

        # Windshield glass (dark tinted cyan)
        windshield_pts = np.array([
            [x1 + 60, y1 + int(car_h * 0.33)],
            [x1 + 105, y1 + 10],
            [x2 - 105, y1 + 10],
            [x2 - 60, y1 + int(car_h * 0.33)]
        ], np.int32)
        cv2.fillPoly(frame, [windshield_pts], (60, 45, 25))

        # Headlights
        cv2.ellipse(frame, (x1 + 35, y1 + int(car_h * 0.55)), (25, 15), 0, 0, 360, (230, 245, 255), -1)
        cv2.ellipse(frame, (x2 - 35, y1 + int(car_h * 0.55)), (25, 15), 0, 0, 360, (230, 245, 255), -1)

        # Grille
        grille_y1 = y1 + int(car_h * 0.48)
        grille_y2 = y1 + int(car_h * 0.70)
        cv2.rectangle(frame, (x1 + 90, grille_y1), (x2 - 90, grille_y2), (25, 25, 25), -1)

        # 3. License Plate Area (White plate, black border, black text)
        plate_w = 200
        plate_h = 50
        px1 = car_cx - (plate_w // 2)
        py1 = y2 - 65
        px2 = px1 + plate_w
        py2 = py1 + plate_h

        # Plate background
        cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 255, 255), -1)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (20, 20, 20), 2)

        # Blue IND strip on left of plate
        cv2.rectangle(frame, (px1 + 2, py1 + 2), (px1 + 24, py2 - 2), (180, 50, 20), -1)
        cv2.putText(frame, "IND", (px1 + 3, py1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (255, 255, 255), 1)

        # Plate text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size, _ = cv2.getTextSize(plate_text, font, 0.75, 2)
        tx = px1 + 32 + max(0, (plate_w - 38 - text_size[0]) // 2)
        ty = py1 + 33
        cv2.putText(frame, plate_text, (tx, ty), font, 0.75, (10, 10, 10), 2)

        # 4. Camera HUD Overlays
        now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        cv2.putText(frame, f"CAM-01  [{gate_status}]  FPS: 30.0", (25, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 128), 2)
        cv2.putText(frame, now_str, (width - 250, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (220, 220, 220), 1)

        # Blinking REC dot
        cv2.circle(frame, (width - 275, 28), 6, (0, 0, 255), -1)

        return frame
