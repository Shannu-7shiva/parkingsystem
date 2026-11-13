# Chapter 7: Functional Modules

## 7.1 Module Specifications

### Module 1: Vehicle Detection Module (`anpr/vehicle_detector.py`)
- Detects presence and bounds of `car`, `motorcycle`, `bus`, and `truck` within an input frame.
- Uses confidence thresholds defined in `config.py`.
- Generates labelled bounding boxes and crops the primary vehicle region for downstream plate localization.

### Module 2: License Plate Detection Module (`anpr/plate_detector.py`)
- Isolates the high-contrast horizontal rectangular license plate region within the vehicle bounding box.
- Supports optional custom YOLO weights (`license_plate_detector.pt`) or native OpenCV Sobel vertical edge gradient detection.
- Provides fallback for manual user coordinate cropping.

### Module 3: Preprocessing & OCR Module (`anpr/image_processor.py` & `anpr/ocr_engine.py`)
- Enhances cropped plate images via resizing, bilateral filtering, CLAHE contrast balancing, and Otsu adaptive thresholding.
- Extracts alphanumeric character sequences using EasyOCR and computes average confidence percentages.

### Module 4: Plate Normalization Module (`anpr/plate_processor.py`)
- Cleans symbols, spaces, and hyphens.
- Enforces Indian standard license plate rules (`[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}`) and Bharat (`BH`) series.
- Contextually swaps OCR-confused characters (e.g. `O` ↔ `0`, `I` ↔ `1`, `B` ↔ `8`) based on position within the string.

### Module 5: Parking Allocation & Billing Module (`parking/`)
- Dynamically allocates available bays across 15 slots (P01–P12 Normal, VIP01, EV01, DIS01).
- Implements duration-based graduated tariff rules with grace period support.
- Automatically handles slot release and updates real-time occupancy statistics.

### Module 6: Simulation & Demonstration Module (`simulation/`)
- Generates synthetic high-resolution camera frames with vehicles and authentic Indian license plates.
- Provides automated sequences for testing arrivals, departures, and full-lot conditions without requiring physical vehicles.

### Module 7: Web Dashboard & Analytics (`templates/` & `static/`)
- Renders an interactive 2D visualization of the parking facility.
- Displays key performance indicators, live activity feeds, blacklist management, and historical logs.
- Visualizes peak hours and revenue trends using Chart.js.
