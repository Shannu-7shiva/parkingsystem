# Chapter 9: Core ANPR & Parking Algorithm

## 9.1 Formal Step-by-Step Procedure

```text
ALGORITHM: Automated ANPR Parking Management

INPUT:
    Frame F (from webcam, video stream, uploaded image, or virtual simulator)
    Database Connection DB

OUTPUT:
    Updated parking slot state, vehicle record, billing receipt, and UI telemetry.

BEGIN
    1. Read input frame F into memory as a BGR matrix.
    
    2. Execute Vehicle Detection:
       Detect bounding box V_box and category (car, motorcycle, bus, truck) using YOLO or OpenCV contours.
       If no vehicle detected:
           Continue with full frame F as region of interest (ROI).
       Else:
           Crop ROI = F[V_box.y1:V_box.y2, V_box.x1:V_box.x2].
    
    3. Execute License Plate Localization:
       Locate plate bounding box P_box within ROI using YOLO plate model or OpenCV Sobel edge filter.
       Crop plate image P_crop = ROI[P_box.y1:P_box.y2, P_box.x1:P_box.x2].
    
    4. Image Preprocessing:
       Resize P_crop to standard height (120px).
       Convert to Grayscale.
       Apply Bilateral Filter to suppress noise while preserving character boundaries.
       Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).
       Apply Otsu thresholding to generate enhanced binary image P_bin.
    
    5. Optical Character Recognition (OCR):
       Pass enhanced image to EasyOCR reader.
       Extract raw text string T_raw and confidence score C_score.
    
    6. Plate Normalization & Validation:
       Remove spaces, hyphens, and punctuation -> T_clean.
       Check Indian regex patterns:
           Standard Pattern: ^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$
           Bharat Pattern:   ^(\d{2})(BH)(\d{4})([A-Z]{1,2})$
       If match fails, apply contextual character disambiguation:
           Positions 0-1 (State): Digits -> Letters (e.g. '0' -> 'O')
           Positions 2-3 (RTO): Letters -> Digits (e.g. 'O' -> '0')
           Last 4 positions (Number): Letters -> Digits (e.g. 'B' -> '8', 'S' -> '5')
       Verify state code against valid Indian States & Union Territories.
       Result -> Verified Plate P_num.
    
    7. Database Query:
       Query Blacklist table for P_num:
       IF P_num in Blacklist:
           Flag SECURITY ALERT;
           Deny entry;
           RETURN "Access Denied: Blacklisted Vehicle".
       
       Query active ParkingRecord where plate_number = P_num AND status = 'PARKED':
       
       IF active record NOT found:
           // Vehicle is entering
           Find optimal available slot S from ParkingSlot where status = 'AVAILABLE':
               (Prioritize EV slots for electric vehicles, Normal slots for regular cars)
           IF no slots available:
               RETURN "Parking Lot Full";
           Assign S.status = 'OCCUPIED', S.vehicle_id = V.id;
           Create new ParkingRecord(plate=P_num, slot=S.number, entry_time=NOW, status='PARKED');
           Save entry frame snapshot to uploads/vehicles/;
           RETURN "Entry Registered, Slot Assigned".
       
       ELSE:
           // Vehicle is exiting
           Calculate Duration = (NOW - active_record.entry_time) in minutes;
           Compute Tariff via BillingCalculator:
               IF Duration <= Grace_Period: Fee = 0;
               ELSE IF Duration <= 60: Fee = First_Hour_Rate;
               ELSE: Fee = First_Hour_Rate + ceil((Duration - 60)/60) * Add_Hour_Rate;
           Update active_record: exit_time = NOW, duration = Duration, amount = Fee, status = 'COMPLETED';
           Release slot S: S.status = 'AVAILABLE', S.vehicle_id = NULL;
           Save exit frame snapshot to uploads/vehicles/;
           RETURN "Exit Processed, Fee Calculated, Slot Released".

    8. Broadcast updated slot and revenue metrics to dashboard.
END
```
