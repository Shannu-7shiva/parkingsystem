# Chapter 5: Proposed System

## 5.1 Architecture Overview
The proposed Smart Parking System uses software-only Computer Vision and Optical Character Recognition (ANPR) executed on a standard PC. It removes the need for physical per-bay sensors while delivering higher operational speed, automated accounting, and real-time visualization.

## 5.2 Key Advantages of the Proposed Architecture
1. **Zero Hardware Dependency:** Operates using existing webcams, security IP cameras, or prerecorded video files without requiring physical sensor infrastructure.
2. **Autonomous Turnaround:** Vehicle arrival, plate extraction, database lookup, slot assignment, and departure checkout occur automatically in sub-second intervals.
3. **Resilient Computer Vision Fallbacks:** The pipeline utilizes YOLOv8 when available and automatically switches to an OpenCV morphological Sobel localizer if specialized neural weights are absent.
4. **Tailored for Indian License Plates:** Features contextual optical character disambiguation to correct common OCR errors (such as `O` for `0`, `B` for `8`, and `I` for `1`) based on standard Indian state and RTO formatting.
5. **Interactive Demonstration System:** Features an integrated Virtual Simulator that synthesizes camera frames, allowing students and evaluators to test all edge cases (full parking lot, blacklisted plates, EV charging priority, long-stay billing) on a standard laptop.
