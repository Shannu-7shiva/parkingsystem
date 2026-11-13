# Chapter 3: Objectives

## 3.1 Primary Objective
To design, implement, and validate an automated, software-only intelligent parking management system powered by Computer Vision and Optical Character Recognition that operates reliably on a standard laptop.

## 3.2 Specific Technical Objectives
1. **Vehicle & Plate Detection:** Detect motor vehicles (cars, motorcycles, buses, trucks) and locate their license plates from live webcam feeds, uploaded video clips, or synthesized frames using YOLO and OpenCV.
2. **Text Recognition & Indian Standard Formatting:** Extract alphanumeric plate strings using EasyOCR and normalize characters against the Indian Motor Vehicle Act standards (`[State][RTO][Series][Number]`) with error correction.
3. **Automated State Tracking:** Automatically determine whether a vehicle is **entering** or **exiting** without requiring manual operator toggle.
4. **Dynamic Slot Allocation:** Intelligently allocate parking spaces across multiple tiers (Normal, EV, VIP, and Accessible slots).
5. **Billing Automation:** Calculate parking duration and graduated fees using configurable hourly rate parameters.
6. **Virtual Lot Simulation:** Render an interactive 2D floor plan with vehicle animations to demonstrate full end-to-end functionality in software.
7. **Security Blacklisting:** Screen all recognized plates against a persistent blacklist and deny unauthorized entry.
