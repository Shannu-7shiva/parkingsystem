import random
from typing import Dict, Any, Optional
from database.database import get_db
from database.models import ParkingRecord, ParkingSlot, Vehicle
from simulation.demo_data import SAMPLE_VEHICLES
from simulation.virtual_camera import VirtualCamera
from anpr.anpr_pipeline import ANPRPipeline
from parking.parking_service import ParkingService


class ParkingSimulator:
    """Simulates realistic vehicle entry and exit events with visual camera frame synthesis."""

    @classmethod
    def simulate_entry(
        cls,
        plate_number: Optional[str] = None,
        vehicle_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Simulates a vehicle approaching the entrance gate, ANPR detection, and slot assignment."""
        # Select vehicle
        if plate_number:
            vehicle_info = next(
                (v for v in SAMPLE_VEHICLES if v["plate_number"] == plate_number.upper()),
                {
                    "plate_number": plate_number.upper(),
                    "vehicle_type": vehicle_type or "car",
                    "model": "Guest Vehicle",
                    "color": (226, 144, 74),
                    "color_hex": "#4A90E2",
                    "owner_name": "Manual Demo Entry"
                }
            )
        else:
            # Pick non-parked sample vehicle if possible
            with get_db() as session:
                parked_plates = {
                    r.plate_number for r in session.query(ParkingRecord).filter_by(status="PARKED").all()
                }
            available_samples = [v for v in SAMPLE_VEHICLES if v["plate_number"] not in parked_plates and not v.get("is_blacklisted")]
            if available_samples:
                vehicle_info = random.choice(available_samples)
            else:
                vehicle_info = random.choice(SAMPLE_VEHICLES)

        plate = vehicle_info["plate_number"]
        v_type = vehicle_type or vehicle_info.get("vehicle_type", "car")
        v_color = vehicle_info.get("color", (180, 50, 40))

        # Synthesize virtual camera entry frame
        frame = VirtualCamera.generate_vehicle_frame(
            plate_text=plate,
            vehicle_color=v_color,
            vehicle_type=v_type,
            gate_status="ENTRY GATE 01"
        )

        # Run ANPR pipeline
        from anpr.multi_frame_tracker import global_multi_frame_tracker
        global_multi_frame_tracker.clear_track("ENTRY")

        pipeline_res = ANPRPipeline.process_frame(
            frame=frame,
            force_action="ENTRY",
            override_plate_text=plate,
            auto_parking_trigger=True
        )

        pipeline_res["simulated_vehicle"] = vehicle_info
        return pipeline_res

    @classmethod
    def simulate_exit(
        cls,
        plate_number: Optional[str] = None,
        simulated_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """Simulates a currently parked vehicle reaching the exit gate, ANPR recognition, and checkout."""
        with get_db() as session:
            parked_records = session.query(ParkingRecord).filter_by(status="PARKED").all()

            if not parked_records:
                return {
                    "success": False,
                    "message": "No vehicles are currently parked to simulate exit."
                }

            if plate_number:
                target_rec = next((r for r in parked_records if r.plate_number == plate_number.upper()), None)
                if not target_rec:
                    return {
                        "success": False,
                        "message": f"Vehicle {plate_number} is not currently parked."
                    }
            else:
                target_rec = random.choice(parked_records)

            plate = target_rec.plate_number
            v_type = target_rec.vehicle.vehicle_type if target_rec.vehicle else "car"

        # Match sample vehicle color if possible
        v_match = next((v for v in SAMPLE_VEHICLES if v["plate_number"] == plate), None)
        v_color = v_match.get("color", (180, 50, 40)) if v_match else (180, 50, 40)

        # Random realistic simulated parking duration between 40 and 190 minutes if none provided
        if simulated_duration is None:
            simulated_duration = round(random.uniform(40.0, 190.0), 1)

        # Generate virtual exit camera frame
        frame = VirtualCamera.generate_vehicle_frame(
            plate_text=plate,
            vehicle_color=v_color,
            vehicle_type=v_type,
            gate_status="EXIT GATE 01"
        )

        # Process exit
        from anpr.multi_frame_tracker import global_multi_frame_tracker
        global_multi_frame_tracker.clear_track("EXIT")

        pipeline_res = ANPRPipeline.process_frame(
            frame=frame,
            force_action="EXIT",
            override_plate_text=plate,
            auto_parking_trigger=False
        )

        # Process exit action with duration
        exit_action = ParkingService.process_plate_event(
            plate_number=plate,
            force_action="EXIT",
            image_path=pipeline_res.get("annotated_image_url"),
            simulated_duration=simulated_duration,
            payment_mode="Fastag Auto-Debit"
        )

        pipeline_res["parking_action"] = exit_action
        return pipeline_res

    @classmethod
    def auto_demo_step(cls) -> Dict[str, Any]:
        """Performs a step in auto-demo sequence, alternating intelligently between entry and exit."""
        with get_db() as session:
            parked_count = session.query(ParkingRecord).filter_by(status="PARKED").count()
            available_slots = session.query(ParkingSlot).filter_by(status="AVAILABLE").count()

        if parked_count == 0 or (available_slots > 3 and random.random() < 0.60):
            # Prefer entry
            return cls.simulate_entry()
        else:
            # Prefer exit
            return cls.simulate_exit()
