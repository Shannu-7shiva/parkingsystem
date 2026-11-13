# Chapter 10: Implementation Details

## 10.1 Software Modules & Key Classes

### 1. Central Configuration (`config.py`)
- Defines centralized application paths (`UPLOAD_FOLDER`, `MODEL_DIR`, `LOGS_DIR`).
- Manages AI confidence thresholds (`VEHICLE_CONFIDENCE = 0.40`, `PLATE_CONFIDENCE = 0.45`, `OCR_CONFIDENCE = 0.35`).
- Sets default pricing rules (`PARKING_FIRST_HOUR_RATE = 30.0`, `PARKING_ADDITIONAL_HOUR_RATE = 20.0`).

### 2. Vehicle Detector (`anpr/vehicle_detector.py`)
- Employs `ultralytics.YOLO` targeting classes 2 (car), 3 (motorcycle), 5 (bus), and 7 (truck).
- Features automatic lazy-loading to conserve memory on startup.
- Implements an OpenCV geometric contour detector as a fallback if PyTorch neural weights are unavailable.

### 3. Number Plate Localization (`anpr/plate_detector.py`)
- Supports loading custom-trained YOLO weights (`license_plate_detector.pt`) from `models/`.
- Fallback localizer applies Sobel horizontal filters (`cv2.Sobel`) followed by horizontal rectangular morphological closing (`cv2.morphologyEx`) to identify character clusters conforming to standard 2.0 to 5.5 aspect ratios.

### 4. Image Preprocessing & OCR (`anpr/image_processor.py` & `anpr/ocr_engine.py`)
- Resizes crops to a standardized height of 120 pixels using bicubic interpolation.
- Applies bilateral filtering (`d=11, sigmaColor=17, sigmaSpace=17`) to preserve character edges while eliminating noise.
- Enhances local contrast with CLAHE (`clipLimit=2.5, tileGridSize=(8, 8)`).
- Employs EasyOCR Reader (English) with automatic binarization retry logic.

### 5. Indian Plate Normalizer (`anpr/plate_processor.py`)
- Validates against all 36 Indian State and Union Territory codes.
- Corrects common OCR character substitutions based on character position (e.g. `TN O9 AB 123B` -> `TN09AB1238`).
- Provides support for Bharat (`BH`) series registrations.

### 6. Parking State Engine (`parking/parking_service.py`)
- Automatically differentiates between arrivals and departures by querying active sessions.
- Computes parking durations and applies graduated tariffs.
- Enforces security blacklist restrictions.

### 7. Virtual Camera Simulator (`simulation/virtual_camera.py`)
- Synthesizes realistic asphalt entry lane scenes with high-contrast Indian license plates, car bodies, windshields, headlights, and camera HUD overlays.
