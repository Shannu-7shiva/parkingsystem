# Chapter 6: System Architecture

## 6.1 Architectural Block Diagram

```mermaid
flowchart TD
    A[Camera Feed / Uploaded Video / Virtual Simulator] --> B[Vehicle Detection Layer\nYOLOv8 / OpenCV Contour Geometry]
    B --> C[License Plate Localization Layer\nYOLO Weights / OpenCV Sobel Edge Filter]
    C --> D[Image Preprocessing Engine\nGrayscale, CLAHE Contrast, Bilateral Filter, Otsu]
    D --> E[OCR Engine\nEasyOCR / Character Extractor]
    E --> F[Plate Normalization & Indian Format Validation\nRegex, State Codes, Positional Disambiguation]
    F --> G{Parking Service Facade}
    G -->|Blacklisted?| H[Access Denied / Security Alert]
    G -->|Not Parked| I[Entry Manager: Assign Slot & Store Record]
    G -->|Already Parked| J[Exit Manager: Calculate Duration, Fee & Release Slot]
    I --> K[(SQLite Database\nSQLAlchemy ORM)]
    J --> K
    K --> L[Web Frontend Dashboard & Virtual Lot 2D Visualization]
```

## 6.2 Component Interactions
- **Presentation Tier:** Built using HTML5, modern Vanilla CSS, and JavaScript. Connects with backend endpoints via asynchronous Fetch API polling.
- **Application Services Tier:** Developed in Flask, structured around modular blueprints: `auth`, `dashboard`, `vehicles`, `analytics`, and `api`.
- **AI / ANPR Engine Tier:** Executes computer vision detection on incoming image matrices using OpenCV, Ultralytics YOLO, and EasyOCR.
- **Persistence Tier:** Encapsulated in SQLite via SQLAlchemy ORM, enforcing foreign key relationships and transaction isolation.
