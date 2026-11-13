import time
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from anpr.plate_processor import PlateProcessor


class MultiFrameTracker:
    """
    Multi-Frame Temporal Consensus & Confidence-Weighted Voting Tracker.
    Aggregates consecutive frames of a detected vehicle, weights readings by OCR confidence
    and image sharpness, and resolves visual character noise through character-level voting.
    """

    def __init__(self, max_buffer_size: int = 8, time_window_seconds: float = 6.0):
        self.max_buffer_size = max_buffer_size
        self.time_window = time_window_seconds
        # Buffer keyed by gate_id or vehicle_track: {"ENTRY": [...], "EXIT": [...]}
        self.tracks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.last_finalized_plate: Dict[str, str] = {}
        self.last_finalized_time: Dict[str, float] = {}

    def add_reading(
        self,
        gate_id: str,
        plate_text: str,
        raw_text: str,
        confidence: float,
        sharpness: float = 100.0,
        crop_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Appends a newly detected frame reading and calculates real-time consensus.
        """
        now = time.time()
        track = self.tracks[gate_id]

        # Prune expired readings outside the sliding time window
        self.tracks[gate_id] = [r for r in track if (now - r["timestamp"]) <= self.time_window]
        track = self.tracks[gate_id]

        cleaned = PlateProcessor.clean_raw_text(plate_text)
        if len(cleaned) >= 5:
            # Check for duplicate consecutive readings in under 150ms to ensure frame diversity
            is_redundant = False
            if track and (now - track[-1]["timestamp"]) < 0.15:
                if track[-1]["cleaned_plate"] == cleaned and abs(track[-1]["sharpness"] - sharpness) < 5.0:
                    is_redundant = True

            if not is_redundant:
                track.append({
                    "timestamp": now,
                    "cleaned_plate": cleaned,
                    "raw_text": raw_text,
                    "confidence": max(0.1, min(1.0, float(confidence))),
                    "sharpness": max(10.0, float(sharpness)),
                    "crop_url": crop_url
                })
                # Keep sliding buffer at max_buffer_size
                if len(track) > self.max_buffer_size:
                    # Drop oldest entry
                    track.pop(0)

        # Compute consensus from available frames
        return self.compute_consensus(gate_id)

    def compute_consensus(self, gate_id: str) -> Dict[str, Any]:
        """
        Executes position-by-position confidence-weighted voting across buffered frames.
        """
        now = time.time()
        readings = [r for r in self.tracks[gate_id] if (now - r["timestamp"]) <= self.time_window]

        if not readings:
            return {
                "consensus_plate": "",
                "raw_ocr": "",
                "confidence": 0.0,
                "frames_count": 0,
                "status": "NO_READINGS",
                "is_confident": False,
                "voting_breakdown": {}
            }

        # 1. Consensus on Plate Length
        length_weights: Dict[int, float] = defaultdict(float)
        for r in readings:
            plate = r["cleaned_plate"]
            w = r["confidence"] * min(2.0, max(0.5, r["sharpness"] / 80.0))
            length_weights[len(plate)] += w

        consensus_len = max(length_weights.keys(), key=lambda l: length_weights[l])

        # 2. Filter readings matching consensus length (or near it)
        eligible = [r for r in readings if len(r["cleaned_plate"]) == consensus_len]
        if not eligible:
            eligible = readings

        # 3. Position-Wise Confidence-Weighted Voting
        voted_chars: List[str] = []
        voting_details: Dict[int, Dict[str, float]] = {}
        total_pos_confidence = 0.0

        for pos in range(consensus_len):
            char_votes: Dict[str, float] = defaultdict(float)
            for r in eligible:
                plate = r["cleaned_plate"]
                if pos < len(plate):
                    c = plate[pos]
                    # Weight = confidence * sharpness factor
                    weight = r["confidence"] * min(2.0, max(0.5, r["sharpness"] / 80.0))
                    char_votes[c] += weight

            voting_details[pos] = dict(char_votes)
            if char_votes:
                winning_char = max(char_votes.keys(), key=lambda c: char_votes[c])
                total_votes = sum(char_votes.values())
                char_agreement = (char_votes[winning_char] / total_votes) if total_votes > 0 else 0.5
                voted_chars.append(winning_char)
                total_pos_confidence += char_agreement
            else:
                voted_chars.append("?")

        raw_voted_string = "".join(voted_chars)

        # 4. Syntactic Disambiguation & Indian Validation
        resolved_plate, val_details = PlateProcessor.disambiguate_indian_plate(raw_voted_string)

        # Base confidence is the average character agreement across frames
        char_conf = (total_pos_confidence / consensus_len) if consensus_len > 0 else 0.0
        # Multiplied by grammatical validation score
        gram_score = val_details.get("score", 0.5)
        
        # Frame sample boost: more agreeing frames -> higher confidence
        frame_boost = min(0.12, (len(eligible) - 1) * 0.03)
        final_confidence = round(min(0.99, max(0.20, (char_conf * 0.45 + gram_score * 0.55) + frame_boost)), 3)

        # 5. Determine Confidence Tier
        # HIGH: >= 85% confidence & Valid statutory structure
        # MEDIUM: 60% - 84% confidence
        # LOW: < 60% or conflicting
        if final_confidence >= 0.85 and val_details.get("valid", False):
            tier = "HIGH_CONFIDENCE_AUTO"
            is_confident = True
        elif final_confidence >= 0.60:
            tier = "MEDIUM_CONFIDENCE_CONFIRM"
            is_confident = False
        else:
            tier = "UNCERTAIN_REJECT"
            is_confident = False

        return {
            "consensus_plate": resolved_plate,
            "raw_ocr": raw_voted_string,
            "confidence": final_confidence,
            "frames_count": len(eligible),
            "total_frames_buffered": len(readings),
            "status": tier,
            "is_confident": is_confident,
            "validation": val_details,
            "voting_breakdown": voting_details
        }

    def clear_track(self, gate_id: str):
        """Clears buffer for specified gate after transaction commit."""
        self.tracks.pop(gate_id, None)

    def is_duplicate_event(self, gate_id: str, plate: str, cooldown_seconds: float = 60.0) -> bool:
        """Checks if identical plate was finalized recently at this gate to avoid double entry."""
        now = time.time()
        last_plate = self.last_finalized_plate.get(gate_id)
        last_time = self.last_finalized_time.get(gate_id, 0.0)

        if last_plate == plate and (now - last_time) < cooldown_seconds:
            return True
        return False

    def mark_finalized(self, gate_id: str, plate: str):
        """Records a successful registration event timestamp."""
        now = time.time()
        self.last_finalized_plate[gate_id] = plate
        self.last_finalized_time[gate_id] = now
        self.clear_track(gate_id)


# Module-level singleton
global_multi_frame_tracker = MultiFrameTracker()

