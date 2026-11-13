# AI & Computer Vision Models Directory

This folder contains pre-trained neural network weights for **Vehicle Detection** and **License Plate Recognition (ANPR)**.

---

## 1. Models Overview

| Model File | Purpose | Framework | Architecture | Input Size | Default Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `yolov8n.pt` | Vehicle Detection (Car, Bike, Bus, Truck) | Ultralytics PyTorch | YOLOv8 Nano | 640x640 | Auto-downloaded / Pre-installed |
| `license_plate_detector.pt` | License Plate Localization (Optional) | Ultralytics PyTorch | Custom YOLOv8 | 640x640 | Optional custom weights |

---

## 2. Vehicle Detection Model (`yolov8n.pt`)

- **Classes Detected:** `car` (ID: 2), `motorcycle` (ID: 3), `bus` (ID: 5), `truck` (ID: 7).
- **Default Confidence Threshold:** `0.40` (Configurable via `config.py` as `VEHICLE_CONFIDENCE`).
- **Download Command:**
  ```bash
  python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
  ```
- **Automatic Fallback:**
  If PyTorch or YOLO is not present, our system automatically falls back to an **OpenCV Edge & Contour Vehicle Detector**, ensuring 100% operational uptime on any PC.

---

## 3. Dedicated License Plate Detector (`license_plate_detector.pt`)

To install a custom trained YOLO model for Indian license plates:
1. Train or download a license plate detection YOLO weight file (e.g. from Roboflow or custom training).
2. Rename the weights file to `license_plate_detector.pt`.
3. Place it into this folder: `models/license_plate_detector.pt`.
4. The system will automatically detect and load it on startup without changing any code!

### Fallback Mode (Morphological Sobel & Edge Detector)
If `license_plate_detector.pt` is not added:
- The system activates the built-in **OpenCV Morphological Sobel Horizontal Filter + Aspect Ratio Contour Localizer**.
- Users can also use the **Manual Crop Mode** directly on the Live ANPR dashboard.

---

## 4. OCR Engine Configuration

- **Primary OCR:** EasyOCR English (`en`) engine.
- **Preprocessing Pipeline:**
  1. Bilateral edge-preserving denoising.
  2. Contrast Limited Adaptive Histogram Equalization (CLAHE).
  3. Otsu & Adaptive Gaussian binarization.
  4. Deskew tilt correction.
- **Post-Processing:**
  Indian State code lookup (`TN`, `KA`, `DL`, `AP`, `TS`, `MH`, etc.) with positional optical character disambiguation (`O` ↔ `0`, `I` ↔ `1`, `B` ↔ `8`).
