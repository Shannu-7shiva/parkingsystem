# Smart Parking Management System Using Automatic Number Plate Recognition (ANPR)

An intelligent, software-only Computer Vision and AI-based Parking Management Platform designed as a final-year B.Tech CSE / AIML major project. The system detects incoming/outgoing vehicles, localizes license plates, performs Optical Character Recognition (OCR) with Indian license plate normalization, automatically allocates parking slots, calculates duration and parking fees upon departure, and maintains security blacklists.

---

## 1. Project Overview & Problem Statement

Urban parking complexes, commercial facilities, and residential societies face immense challenges with manual gate ticketing:
- Long queues at entry and exit barriers.
- Human errors in recording license plate numbers and billing durations.
- High hardware installation and maintenance costs associated with physical ground sensors, loop detectors, and RFID tags.

**Solution:**
This project is an **end-to-end software-only solution** running on standard Windows PC/laptops. Utilizing modern Computer Vision (YOLO + OpenCV) and Optical Character Recognition (OCR), it processes video streams or camera frames to automate parking operations without requiring physical IoT sensors.

---

## 2. Key Features

1. **Multi-Mode Video Input:**
   - **Laptop Webcam:** Real-time camera feed.
   - **Media Upload:** Upload vehicle images or recorded video frames.
   - **Interactive Simulation Mode:** Integrated synthetic parking gate camera generating real image frames with cars and Indian license plates.
   - **Manual Fallback / Crop Mode:** Crop or specify plate numbers manually.
2. **AI & Computer Vision Pipeline:**
   - Vehicle detection (`car`, `motorcycle`, `bus`, `truck`).
   - Dedicated number plate detection (custom YOLO weights or OpenCV morphological Sobel localizer).
   - Image enhancement: Bilateral edge-preserving denoising, CLAHE contrast enhancement, Otsu thresholding, and deskewing.
   - OCR engine using EasyOCR with character confusion correction (`O` ↔ `0`, `I` ↔ `1`, `B` ↔ `8`).
   - Format validation for Indian State Codes (`TN`, `KA`, `DL`, `AP`, `TS`, `MH`, etc.) and Bharat (`BH`) series.
3. **Automated Parking Operations:**
   - Automatic determination of **ENTRY** vs **EXIT**.
   - Smart slot allocation (NORMAL slots P01–P12, VIP01, EV01 with charger support, and DIS01 accessible).
   - Automated hourly billing calculator with configurable base and additional rates.
   - Slot release upon checkout.
4. **Interactive Virtual Parking Lot (2D Visualization):**
   - Live bay occupancy floor plan.
   - 2D vehicle rendering inside occupied bays with license plates and timestamps.
   - One-click slot reservation / release.
5. **Security & Fleet Management:**
   - Security Blacklist monitoring with automatic entry denial.
   - Comprehensive vehicle registry and lifetime visit dossier.
   - Audit history log with search, filters, and CSV export.
   - Analytics with Chart.js: Traffic volume, revenue trends, peak hours, and fleet demographics.

---

## 3. Technology Stack

- **Backend:** Python 3.11+, Flask, SQLAlchemy, Werkzeug.
- **Computer Vision & AI:** OpenCV (`cv2`), Ultralytics YOLO (`yolov8n`), EasyOCR, NumPy.
- **Database:** SQLite with SQLAlchemy ORM.
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Chart.js, FontAwesome.
- **Testing:** Python `unittest` suite (19 automated unit & integration tests).

---

## 4. Project Directory Structure

```text
smart-parking-anpr/
├── app.py                      # Flask Application Entry Point
├── config.py                   # Centralized Configuration Parameters
├── requirements.txt            # Python Dependencies
├── setup.bat                   # Automated Windows Setup Script
├── run.bat                     # Windows Run Script
├── README.md                   # Complete Documentation
├── .gitignore                  # Git Ignore Rules
├── database/
│   ├── database.py             # SQLAlchemy Engine & Session Factory
│   ├── models.py               # ORM Models (User, Vehicle, Slot, Record, etc.)
│   ├── seed.py                 # Initial Database Seed Script
│   └── parking.db              # SQLite Database
├── anpr/
│   ├── vehicle_detector.py     # YOLO / OpenCV Vehicle Detector
│   ├── plate_detector.py       # YOLO / Morphological Plate Localizer
│   ├── image_processor.py      # CLAHE, Bilateral Filter, Otsu Binarizer
│   ├── ocr_engine.py           # EasyOCR & Fallback Text Extractor
│   ├── plate_processor.py      # Indian Plate Normalization & Regex Validation
│   └── anpr_pipeline.py        # End-to-End Orchestrator
├── parking/
│   ├── slot_manager.py         # Slot Allocation & Reservation Logic
│   ├── occupancy.py            # Real-Time Utilization Metrics
│   ├── entry_manager.py        # Vehicle Check-In & Slot Assignment
│   ├── exit_manager.py         # Vehicle Departure & Billing Settlement
│   ├── billing.py              # Hourly Tariff & Grace Period Calculator
│   └── parking_service.py      # Facade Coordinating Parking Logic
├── simulation/
│   ├── virtual_camera.py       # Synthetic Scene & Plate Generator
│   ├── demo_data.py            # Sample Fleet & Blacklist Data
│   └── simulator.py            # Automated Arrival, Departure & Auto-Demo
├── routes/
│   ├── authentication.py       # Session Login & Auth Guard
│   ├── dashboard.py            # Dashboard Views
│   ├── vehicles.py             # Vehicle & History Views
│   ├── analytics.py            # Analytics Views
│   └── api.py                  # Full REST API Endpoints
├── templates/                  # Modern Dark UI HTML Templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── live_camera.html
│   ├── parking_lot.html
│   ├── vehicles.html
│   ├── vehicle_details.html
│   ├── parking_history.html
│   ├── analytics.html
│   ├── blacklist.html
│   └── settings.html
├── static/
│   ├── css/                    # Custom CSS Stylesheets
│   │   ├── style.css
│   │   ├── dashboard.css
│   │   └── parking.css
│   └── js/                     # Client Controllers
│       ├── dashboard.js
│       ├── camera.js
│       ├── parking.js
│       ├── analytics.js
│       └── vehicles.js
├── models/
│   ├── README.md               # Guide to Model Weights & Custom Training
│   └── yolov8n.pt              # YOLOv8 Vehicle Weights
├── uploads/                    # Runtime Saved Media
│   ├── vehicles/               # Annotated Camera Snapshots
│   └── plates/                 # High-Res Plate Crops
├── logs/
│   └── application.log         # Technical Application Log File
├── docs/                       # Academic Project Documentation (15 Chapters)
└── tests/                      # Automated Unit Test Suite (19 Tests)
```

---

## 5. Quick Start Guide (Windows)

### Option A: 1-Click Batch Execution (Recommended)
1. Double-click `setup.bat`:
   - Checks Python.
   - Installs dependencies.
   - Seeds database tables with 15 parking slots, sample vehicles, and records.
   - Runs the automated test suite.
2. Double-click `run.bat`:
   - Starts the server at `http://127.0.0.1:5000`.
3. Open your browser to `http://127.0.0.1:5000`.

### Option B: Manual Command Line Execution
```bash
# 1. Initialize virtual environment (optional)
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed Database
python database/seed.py

# 4. Start Flask Application
python app.py
```

---

## 6. Default Login Credentials

| Role | Username | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` |
| **Operator** | `operator` | `operator123` |

---

## 7. Step-by-Step Demonstration Workflow

### Step 1: Terminal Overview
- Log in with `admin / admin123`.
- The dashboard displays 15 total slots, occupancy rate, today's vehicle count, and real-time revenue.

### Step 2: Live ANPR Camera & Detection
- Navigate to **Live ANPR** from the left navigation bar.
- Choose your preferred mode:
  - **Simulation Feed:** Click **"Simulate Arrival"** to generate a vehicle (`TN09AB1234`).
  - **Webcam:** Point your webcam at a printed or displayed license plate, and click **"Capture & Process Plate"**.
  - **Upload:** Upload a picture of a car with a number plate.
- The pipeline draws cyan bounding boxes around the car, green bounding boxes around the plate, extracts the string (`TN09AB1234`), verifies Indian state formatting, and assigns an available bay (e.g., `P01`).
- An official Parking Check-In receipt modal appears on screen.

### Step 3: Virtual Parking Lot Visualization
- Go to **Parking Map**.
- Bay `P01` status immediately switches to `OCCUPIED`.
- A 2D CSS car visual appears parked inside `P01` displaying the plate `TN09AB1234`.
- Click on `P01` to view vehicle details or trigger early checkout.

### Step 4: Departure & Billing Settlement
- Click **"Simulate Departure"** or use the dashboard's **"Simulate Exit"** button.
- The system recognizes `TN09AB1234` as already parked.
- Automatically calculates parking duration (e.g. 1h 45m).
- Applies configured hourly tariff:
  - 0–60 mins = ₹30
  - Additional hours = ₹20/hr
  - Total Fee = ₹50
- The slot `P01` is released back to `AVAILABLE`.
- The car graphic departs from the bay.
- Today's revenue metric updates immediately.

### Step 5: Security Blacklist Protection
- Go to **Blacklist** and add a vehicle (e.g., `DL01ZA9999`).
- Attempt to check in `DL01ZA9999`.
- The system flags the vehicle: `CRITICAL: Blacklisted vehicle detected! Entry denied.`
- Slot assignment is blocked, and a red alert modal is triggered.

---

## 8. Automated Testing

To run the complete automated test suite:
```bash
python -m unittest discover tests
```
The test suite validates:
- `test_database.py`: User security, seed integrity, model relationships.
- `test_billing.py`: Grace period calculations, first-hour and multi-hour rounding rules.
- `test_parking_slots.py`: Slot assignment, duplicate entry protection, checkout, blacklist blocking.
- `test_plate_validation.py`: Indian standard formats, Bharat series, OCR character confusion correction.
- `test_api.py`: REST API endpoints and session authentication.
- `test_routes.py`: Frontend templates and HTTP status codes.

---

## 9. Academic Documentation

A complete 15-chapter academic project report is available in the `docs/` directory:
- `01_Abstract.md`
- `02_Problem_Statement.md`
- `03_Objectives.md`
- `04_Existing_System.md`
- `05_Proposed_System.md`
- `06_System_Architecture.md`
- `07_Modules.md`
- `08_Methodology.md`
- `09_Algorithm.md`
- `10_Implementation.md`
- `11_Database_Design.md`
- `12_Testing.md`
- `13_Expected_Output.md`
- `14_Future_Enhancements.md`
- `15_Conclusion.md`

---

## 10. License

Developed for Academic and Research Purposes as a B.Tech CSE / AIML Capstone Project.
