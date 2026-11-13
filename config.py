import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
IS_VERCEL = (
    os.environ.get("VERCEL") == "1"
    or os.environ.get("VERCEL_ENV") is not None
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    or not os.access(str(BASE_DIR), os.W_OK)
)

if IS_VERCEL:
    STORAGE_DIR = Path("/tmp")
    DATABASE_PATH = STORAGE_DIR / "parking.db"
    UPLOAD_FOLDER = STORAGE_DIR / "uploads"
    LOGS_DIR = STORAGE_DIR / "logs"
else:
    STORAGE_DIR = BASE_DIR
    DATABASE_PATH = BASE_DIR / "database" / "parking.db"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    LOGS_DIR = BASE_DIR / "logs"

VEHICLE_UPLOADS = UPLOAD_FOLDER / "vehicles"
VIDEO_UPLOADS = UPLOAD_FOLDER / "videos"
PLATE_UPLOADS = UPLOAD_FOLDER / "plates"
MODEL_DIR = BASE_DIR / "models"

# Ensure essential directories exist safely
for folder in [UPLOAD_FOLDER, VEHICLE_UPLOADS, VIDEO_UPLOADS, PLATE_UPLOADS, MODEL_DIR, LOGS_DIR, DATABASE_PATH.parent]:
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# Flask Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "smart-parking-anpr-secret-key-2026-btech-project")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Database Configuration
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# File Upload Configuration
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB max upload size

# Camera Configuration
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))

# Computer Vision & AI Configuration
VEHICLE_CONFIDENCE = float(os.environ.get("VEHICLE_CONFIDENCE", 0.40))
PLATE_CONFIDENCE = float(os.environ.get("PLATE_CONFIDENCE", 0.45))
OCR_CONFIDENCE = float(os.environ.get("OCR_CONFIDENCE", 0.35))

# Tesseract OCR Paths to search automatically
TESSERACT_SEARCH_PATHS = [
    os.environ.get("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\SHIVA\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
]

# Model Weights
YOLO_MODEL_PATH = MODEL_DIR / "yolov8n.pt"
PLATE_MODEL_PATH = MODEL_DIR / "license_plate_detector.pt"

# Parking Billing Defaults (INR ₹)
PARKING_FIRST_HOUR_RATE = 30.0       # Standard first hour charge (Cars)
PARKING_ADDITIONAL_HOUR_RATE = 20.0  # Standard additional hour charge
GRACE_PERIOD_MINUTES = 5.0           # 5 min free grace period
GST_PERCENTAGE = 18.0                # 18% GST

# Vehicle-Specific Tier Rates: (first_hour, additional_hour)
TARIFF_BY_VEHICLE_TYPE = {
    "car": {"first_hour": 30.0, "additional_hour": 20.0},
    "motorcycle": {"first_hour": 15.0, "additional_hour": 10.0},
    "bike": {"first_hour": 15.0, "additional_hour": 10.0},
    "ev": {"first_hour": 25.0, "additional_hour": 15.0},
    "bus": {"first_hour": 60.0, "additional_hour": 40.0},
    "truck": {"first_hour": 60.0, "additional_hour": 40.0},
    "van": {"first_hour": 35.0, "additional_hour": 25.0},
    "auto": {"first_hour": 20.0, "additional_hour": 15.0},
}

# Rate per hour lookup (used by billing)
VEHICLE_RATES = {
    "car": 50,
    "motorcycle": 20,
    "bike": 20,
    "bus": 100,
    "truck": 80,
    "van": 60,
    "auto": 30,
    "ev": 40,
}

# Slot Setup
TOTAL_SLOTS_DEFAULT = 15             # 12 Normal (P01-P12), 1 VIP, 1 EV, 1 Disabled
