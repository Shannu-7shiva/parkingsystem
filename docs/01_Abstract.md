# Chapter 1: Abstract

## 1.1 Overview
The **Smart Parking Management System Using Automatic Number Plate Recognition (ANPR)** is an intelligent, software-only computer vision solution designed to optimize urban parking facility operations. By eliminating the necessity for costly and maintenance-intensive physical hardware sensors—such as ground loop detectors, ultrasonic transducers, and RFID transponders—the proposed platform executes real-time vehicle identification, localization, and entry/exit processing using standard video streams or laptop webcams.

## 1.2 Core Contributions
1. **Edge-Capable Computer Vision Pipeline:** Integrates Ultralytics YOLOv8 for vehicle category classification and license plate localization, supplemented by an adaptive OpenCV morphological edge-filtering fallback mechanism.
2. **Indian License Plate Normalization Engine:** Utilizes Optical Character Recognition (OCR) combined with rule-based heuristics that resolve optical character ambiguity (e.g., distinguishing numeric `0` from alphabetic `O`, and numeric `8` from alphabetic `B`) based on Indian Motor Vehicle Act alphanumeric standards.
3. **Automated Parking Operations:** Programmatically tracks lot occupancy, assigns designated bays (including Normal, VIP, EV, and Accessible slots), computes graduated duration-based tariffs upon departure, and manages a security blacklist.
4. **Interactive Virtual Simulation:** Features an end-to-end 2D web-based visualization and virtual camera frame synthesis system allowing complete system demonstration on a standard consumer laptop without requiring physical cars or live roadway cameras.

## 1.3 Key Results
The system demonstrates reliable plate detection and text extraction under varying illumination conditions, sub-second transaction dispatch times, and seamless database transaction integrity across concurrent requests.
