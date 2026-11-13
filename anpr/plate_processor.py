import re
from typing import Dict, Any, List, Tuple, Optional

# Valid Indian State & Union Territory Codes (36 official states/UTs including Telangana TS & TG)
INDIAN_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "TG", "UK", "UP",
    "WB"
}

# OCR Visual Ambiguity Mappings
DIGIT_TO_LETTER = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '7': 'T',
    '8': 'B'
}

LETTER_TO_DIGIT = {
    'O': '0',
    'D': '0',
    'Q': '0',
    'I': '1',
    'L': '1',
    'Z': '2',
    'A': '4',
    'S': '5',
    'G': '6',
    'T': '7',
    'B': '8'
}

# Common state prefix confusions
STATE_PREFIX_CORRECTIONS = {
    '1G': 'TG', 'IG': 'TG', 'TC': 'TG', 'TO': 'TG', 'T6': 'TG', 'T9': 'TG',
    '1S': 'TS', 'T5': 'TS', 'IS': 'TS',
    'D1': 'DL', 'DI': 'DL',
    'K4': 'KA', 'KI': 'KL',
    'M1': 'MH', 'MI': 'MH',
    'T1': 'TN', 'TI': 'TN',
    'U1': 'UP', 'UI': 'UP',
    'H1': 'HR', 'HI': 'HR',
    'A1': 'AP', 'AI': 'AP'
}


class PlateProcessor:
    """
    Grammar-Guided Indian Vehicle Registration Plate Processor and Disambiguation Engine.
    Resolves OCR visual confusions (0 vs O, 1 vs I, 8 vs B, 5 vs S, 2 vs Z, 6 vs G)
    strictly using the grammatical positioning of Indian license plate syntax.
    """

    @staticmethod
    def clean_raw_text(raw_text: str) -> str:
        """Removes spaces, hyphens, dots, special characters, and forces uppercase."""
        if not raw_text:
            return ""
        # Strip common OCR noise like 'IND' on HSRP plates if attached at start
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        if cleaned.startswith("IND") and len(cleaned) >= 11:
            cleaned = cleaned[3:]
        return cleaned

    @classmethod
    def disambiguate_indian_plate(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Syntactically resolves character ambiguities in Indian plates.
        Analyzes all possible grammatical segmentations:
        - Format A: State (2 letters) + RTO (2 digits) + Series (1-3 letters) + Number (4 digits) -> e.g. TS09AB1234
        - Format B: State (2 letters) + RTO (1 digit)  + Series (1-3 letters) + Number (4 digits) -> e.g. DL8CAF1234
        - Format C: Bharat Series (2 digits) + BH + Number (4 digits) + Series (1-2 letters)     -> e.g. 22BH1234AA
        - Format D: Vintage / Commercial (2 letters) + RTO (1-2 digits) + Number (4 digits)       -> e.g. MH011234
        """
        cleaned = cls.clean_raw_text(text)
        if len(cleaned) < 6:
            return cleaned, {"valid": False, "score": 0.20, "pattern": "too_short"}

        candidates: List[Dict[str, Any]] = []

        # Candidate 0: Raw cleaned text direct test
        val_direct = cls._evaluate_candidate(cleaned, cleaned)
        if val_direct["valid"]:
            candidates.append(val_direct)

        # Candidate 1: Standard Format with 2-digit RTO (e.g. TS 09 AB 1234)
        # Lengths typically 9 to 11 characters
        if len(cleaned) >= 8:
            n = len(cleaned)
            # Last 4 characters must be registration digits
            num_part = cleaned[-4:]
            num_corr = "".join(LETTER_TO_DIGIT.get(c, c) for c in num_part)

            # First 2 characters must be State code letters
            state_part = cleaned[:2]
            state_cand = "".join(DIGIT_TO_LETTER.get(c, c) for c in state_part)
            if state_cand in STATE_PREFIX_CORRECTIONS:
                state_cand = STATE_PREFIX_CORRECTIONS[state_cand]

            # RTO code (index 2 to 4: 2 digits)
            rto_part = cleaned[2:4]
            rto_corr = "".join(LETTER_TO_DIGIT.get(c, c) for c in rto_part)

            # Middle series (index 4 to n-4: letters)
            ser_part = cleaned[4:n-4]
            ser_corr = "".join(DIGIT_TO_LETTER.get(c, c) for c in ser_part)

            cand_plate = f"{state_cand}{rto_corr}{ser_corr}{num_corr}"
            ev = cls._evaluate_candidate(cand_plate, cleaned)
            candidates.append(ev)

        # Candidate 2: Single-Digit RTO Format (e.g. DL 8 CAF 1234)
        if len(cleaned) >= 8:
            n = len(cleaned)
            num_part = cleaned[-4:]
            num_corr = "".join(LETTER_TO_DIGIT.get(c, c) for c in num_part)

            state_part = cleaned[:2]
            state_cand = "".join(DIGIT_TO_LETTER.get(c, c) for c in state_part)
            if state_cand in STATE_PREFIX_CORRECTIONS:
                state_cand = STATE_PREFIX_CORRECTIONS[state_cand]

            # Single digit RTO (index 2)
            rto_digit = LETTER_TO_DIGIT.get(cleaned[2], cleaned[2])

            # Series (index 3 to n-4: letters)
            ser_part = cleaned[3:n-4]
            ser_corr = "".join(DIGIT_TO_LETTER.get(c, c) for c in ser_part)

            cand_plate = f"{state_cand}{rto_digit}{ser_corr}{num_corr}"
            ev = cls._evaluate_candidate(cand_plate, cleaned)
            candidates.append(ev)

        # Candidate 3: Bharat Series (BH) Format (e.g. 22 BH 1234 AA)
        if "BH" in cleaned or (len(cleaned) >= 9 and cleaned[2:4] in ("8H", "B#", "8#")):
            try:
                yr_part = "".join(LETTER_TO_DIGIT.get(c, c) for c in cleaned[:2])
                num_part = "".join(LETTER_TO_DIGIT.get(c, c) for c in cleaned[4:8])
                ser_part = "".join(DIGIT_TO_LETTER.get(c, c) for c in cleaned[8:])
                bh_cand = f"{yr_part}BH{num_part}{ser_part}"
                ev = cls._evaluate_candidate(bh_cand, cleaned)
                candidates.append(ev)
            except Exception:
                pass

        # Sort candidates by grammatical confidence score descending
        if candidates:
            candidates.sort(key=lambda c: c["score"], reverse=True)
            best = candidates[0]
            return best["plate"], best

        return cleaned, {"valid": False, "score": 0.30, "pattern": "unmatched"}

    @classmethod
    def _evaluate_candidate(cls, candidate: str, original_raw: str) -> Dict[str, Any]:
        """Validates and scores a candidate plate string against Indian statutory patterns."""
        # Pattern 1: Standard Indian Plate (2 letters State, 1-2 digits RTO, 0-3 letters Series, 4 digits Number)
        m_std = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$", candidate)
        if m_std:
            state, rto, series, number = m_std.groups()
            is_valid_state = state in INDIAN_STATES
            
            # Base score: valid structure = 0.85; verified Indian state code = 0.98
            score = 0.98 if is_valid_state else 0.82

            # Small penalty if characters were modified from raw OCR (prevents over-correction)
            diffs = sum(1 for a, b in zip(candidate, original_raw) if a != b) if len(candidate) == len(original_raw) else 1
            score = max(0.60, score - (diffs * 0.02))

            return {
                "valid": is_valid_state,
                "plate": candidate,
                "score": round(score, 3),
                "state_code": state,
                "rto_code": rto.zfill(2),
                "series": series,
                "number": number,
                "pattern": "Standard Indian ANPR",
                "is_indian_format": True
            }

        # Pattern 2: Bharat Series
        m_bh = re.match(r"^(\d{2})(BH)(\d{4})([A-Z]{1,2})$", candidate)
        if m_bh:
            year, bh, number, series = m_bh.groups()
            return {
                "valid": True,
                "plate": candidate,
                "score": 0.95,
                "state_code": "BH",
                "rto_code": year,
                "series": series,
                "number": number,
                "pattern": "Bharat Series (BH)",
                "is_indian_format": True
            }

        # Pattern 3: Old format / 3-digit number (e.g., DL1C123)
        m_old = re.match(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,2})(\d{3,4})$", candidate)
        if m_old:
            state, rto, series, number = m_old.groups()
            is_valid_state = state in INDIAN_STATES
            return {
                "valid": is_valid_state,
                "plate": candidate,
                "score": 0.85 if is_valid_state else 0.65,
                "state_code": state,
                "rto_code": rto,
                "series": series,
                "number": number,
                "pattern": "Old/Short Format",
                "is_indian_format": True
            }

        # Generic Alphanumeric Fallback (6 to 12 chars)
        if re.match(r"^[A-Z0-9]{6,12}$", candidate):
            state_sub = candidate[:2]
            is_valid_state = state_sub in INDIAN_STATES
            return {
                "valid": is_valid_state and len(candidate) >= 8,
                "plate": candidate,
                "score": 0.70 if is_valid_state else 0.45,
                "state_code": state_sub if is_valid_state else None,
                "rto_code": None,
                "series": None,
                "number": None,
                "pattern": "Generic Alphanumeric",
                "is_indian_format": is_valid_state
            }

        return {
            "valid": False,
            "plate": candidate,
            "score": 0.20,
            "state_code": None,
            "rto_code": None,
            "series": None,
            "number": None,
            "pattern": "Invalid",
            "is_indian_format": False
        }

    @classmethod
    def validate_and_format(cls, raw_text: str) -> Dict[str, Any]:
        """Public API returning full normalization, validation breakdown, and confidence score."""
        cleaned_input = cls.clean_raw_text(raw_text)
        if not cleaned_input:
            return {
                "valid": False,
                "raw_text": raw_text,
                "cleaned_plate": "",
                "state_code": None,
                "rto_code": None,
                "series": None,
                "number": None,
                "confidence_score": 0.0,
                "is_indian_format": False
            }

        resolved_plate, details = cls.disambiguate_indian_plate(cleaned_input)

        return {
            "valid": details.get("valid", False),
            "raw_text": raw_text,
            "cleaned_plate": resolved_plate,
            "state_code": details.get("state_code"),
            "rto_code": details.get("rto_code"),
            "series": details.get("series"),
            "number": details.get("number"),
            "confidence_score": details.get("score", 0.0),
            "is_indian_format": details.get("is_indian_format", False),
            "pattern": details.get("pattern", "Unknown")
        }
