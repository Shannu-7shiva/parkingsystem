# Chapter 8: Methodology

## 8.1 Research & Engineering Workflow
The development followed an agile, incremental methodology:
1. **Domain Modeling:** Defined the relational schema (Users, Vehicles, Slots, Records, Blacklist, Settings) with SQLite.
2. **Computer Vision Development:** Built and validated vehicle categorization, plate localization, and preprocessing using OpenCV and YOLO.
3. **OCR Evaluation:** Tuned image filtering (bilateral filter + CLAHE) to optimize EasyOCR text extraction and handle illumination variance.
4. **Business Logic & Service Layer:** Implemented billing calculations, slot allocation heuristics, and blacklist screening.
5. **Simulation & Virtual Camera Engine:** Engineered synthetic frame generators to enable reliable offline testing and demonstrations.
6. **Frontend Integration:** Built responsive dashboard views, real-time polling hooks, and interactive 2D CSS vehicle visualizations.
7. **Automated Verification:** Implemented 19 unit and integration tests to validate all edge cases and transaction flows.
