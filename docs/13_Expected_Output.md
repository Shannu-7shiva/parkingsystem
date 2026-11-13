# Chapter 13: Expected Output & User Workflows

## 13.1 Demonstration Workflows

### 1. Dashboard Overview
- Shows 15 total slots, live counts of available and occupied spaces, daily vehicle count, and collected revenue.
- Displays a mini virtual parking lot preview where occupied slots render 2D vehicle graphics with license plate badges.

### 2. Live ANPR Recognition
- Pointing a webcam or uploading an image of a car extracts the license plate.
- The UI highlights the vehicle with a cyan bounding box and the license plate with a green bounding box.
- Displays raw OCR text, normalized plate, confidence score, vehicle classification, and assigned bay.
- Triggers an on-screen check-in receipt modal.

### 3. Virtual Parking Lot Floor Plan
- The bay status switches to `OCCUPIED`.
- A 2D CSS car visual appears parked inside the bay, displaying headlights, windshield, roof, and license plate.
- Clicking any slot opens an interactive management modal to inspect parked vehicles, process checkouts, or toggle reservations.

### 4. Vehicle Departure & Settlement
- The system automatically detects when a parked vehicle is leaving.
- Computes elapsed duration (e.g. 1 hour 45 minutes) and calculates the fee according to configured rates (e.g. ₹50.00).
- Releases the bay back to `AVAILABLE`, and updates the dashboard metrics.

### 5. Analytics & Business Intelligence
- Interactive Chart.js graphs illustrate daily vehicle volume, weekly revenue trends, 24-hour peak hours, and vehicle demographics (cars, bikes, buses, trucks, EVs).
