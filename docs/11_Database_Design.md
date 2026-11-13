# Chapter 11: Database Design & Schema

## 11.1 Entity Relationship Overview
The database is structured around six core relational entities managed through SQLAlchemy ORM and persisted in SQLite (`database/parking.db`).

## 11.2 Database Schema Specifications

### 1. `users` Table
Stores authenticated administrative and operator accounts.
- `id` (INTEGER, Primary Key, Auto Increment)
- `username` (VARCHAR(80), Unique, Not Null, Indexed)
- `password_hash` (VARCHAR(255), Not Null) — PBKDF2/SHA256 salted hash.
- `role` (VARCHAR(50), Default 'admin')
- `created_at` (DATETIME)

### 2. `vehicles` Table
Maintains historical records of vehicles that have entered the facility.
- `id` (INTEGER, Primary Key, Auto Increment)
- `plate_number` (VARCHAR(20), Unique, Not Null, Indexed)
- `vehicle_type` (VARCHAR(30), Default 'car')
- `owner_name` (VARCHAR(100))
- `phone` (VARCHAR(20))
- `is_blacklisted` (BOOLEAN, Default False)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 3. `parking_slots` Table
Represents physical/virtual parking bays in the facility.
- `id` (INTEGER, Primary Key, Auto Increment)
- `slot_number` (VARCHAR(20), Unique, Not Null, Indexed) — e.g. P01 to P12, VIP01, EV01, DIS01.
- `slot_type` (VARCHAR(30), Default 'NORMAL') — NORMAL, VIP, EV, DISABLED.
- `status` (VARCHAR(30), Default 'AVAILABLE') — AVAILABLE, OCCUPIED, RESERVED.
- `vehicle_id` (INTEGER, Foreign Key -> `vehicles.id`, Nullable)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 4. `parking_records` Table
Tracks individual parking sessions from entry to departure.
- `id` (INTEGER, Primary Key, Auto Increment)
- `vehicle_id` (INTEGER, Foreign Key -> `vehicles.id`, Not Null, Indexed)
- `plate_number` (VARCHAR(20), Not Null, Indexed)
- `slot_number` (VARCHAR(20), Not Null, Indexed)
- `entry_time` (DATETIME, Not Null)
- `exit_time` (DATETIME, Nullable)
- `duration_minutes` (FLOAT, Default 0.0)
- `amount` (FLOAT, Default 0.0)
- `status` (VARCHAR(30), Default 'PARKED') — PARKED, COMPLETED.
- `entry_image` (VARCHAR(255), Nullable) — Path to entry frame snapshot.
- `exit_image` (VARCHAR(255), Nullable) — Path to exit frame snapshot.
- `created_at` (DATETIME)

### 5. `blacklist` Table
Maintains restricted and flagged vehicles.
- `id` (INTEGER, Primary Key, Auto Increment)
- `plate_number` (VARCHAR(20), Unique, Not Null, Indexed)
- `reason` (TEXT)
- `created_at` (DATETIME)

### 6. `system_settings` Table
Dynamic operational parameters and parking tariff configuration.
- `id` (INTEGER, Primary Key, Auto Increment)
- `setting_name` (VARCHAR(100), Unique, Not Null, Indexed)
- `setting_value` (VARCHAR(255), Not Null)
