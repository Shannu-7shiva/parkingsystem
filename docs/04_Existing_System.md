# Chapter 4: Existing System Analysis

## 4.1 Description of Current Practices
Existing parking management solutions broadly fall into two categories:
1. **Manual Gate Guard Operations:** A human attendant logs vehicle details by hand or presses a button to issue a barcode/thermal paper ticket.
2. **Hardware-Sensor Driven Lots:** Embedded hardware (e.g. inductive ground loops, ultrasonic sensors per bay, RFID boom barriers, Arduino/Raspberry Pi microcontrollers).

## 4.2 Disadvantages of Existing Systems
| Feature | Manual System | Hardware IoT System |
| :--- | :--- | :--- |
| **Speed** | Extremely slow (30–60s per vehicle) | Moderate (requires scanning tag/card) |
| **Capital Cost** | Low upfront, high labor recurring | Very high (sensors in every slot) |
| **Hardware Fragility** | None | High (sensor wear, wiring faults, weather) |
| **Accuracy** | Prone to human transcription errors | Tag read errors or lost cards |
| **Simulation Capability** | None | Hardware required to demonstrate |
| **Blacklist Screening** | Dependent on guard memory | Limited or manual lookup |
