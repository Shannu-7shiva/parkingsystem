# Chapter 12: Testing & Quality Assurance

## 12.1 Testing Strategy
The system underwent unit, integration, and UI acceptance testing using Python's `unittest` framework.

## 12.2 Test Suite Execution Summary
A total of **19 automated test cases** are distributed across dedicated test modules:

| Test Module | Scope & Objectives | Test Count | Status |
| :--- | :--- | :--- | :--- |
| `tests/test_database.py` | Validates schema tables, relationships, and seed data. | 3 | **PASS** |
| `tests/test_billing.py` | Tests grace period, 1st hour tariff, and multi-hour rounding. | 4 | **PASS** |
| `tests/test_parking_slots.py` | Tests slot assignment, duplicate entries, exits, and blacklist checks. | 2 | **PASS** |
| `tests/test_plate_validation.py` | Tests standard format, spaces/hyphens, OCR disambiguation, and Bharat series. | 5 | **PASS** |
| `tests/test_api.py` | Tests authentication guards, dashboard, slot, simulator, and blacklist APIs. | 5 | **PASS** |
| `tests/test_routes.py` | Validates frontend rendering and HTTP status codes. | 2 | **PASS** |

## 12.3 Key Test Scenarios & Results
1. **Grace Period Verification:** A simulated duration of 4.0 minutes against a 5.0-minute grace period resulted in a ₹0.00 charge.
2. **First Hour & Graduated Tariff:**
   - 45.0 minutes resulted in ₹30.00 (1 hour charged).
   - 75.0 minutes resulted in ₹50.00 (1 hour base + 1 additional hour).
   - 135.0 minutes resulted in ₹70.00 (1 hour base + 2 additional hours).
3. **Duplicate Entry Rejection:** Attempting to park an already parked vehicle returns `already_parked: True`, identifying the occupied slot.
4. **Blacklist Enforcement:** Inputting `DL01ZA9999` returns `blacklisted: True`, blocks slot allocation, and logs an alert.
5. **OCR Positional Correction:** The string `TN O9 AB 123B` was corrected to `TN09AB1238`.
