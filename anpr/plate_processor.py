import re
from typing import Dict, Any, Tuple

# Valid Indian State & Union Territory Codes (Including Telangana TG & TS)
INDIAN_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "TG", "UK", "UP",
    "WB"
}

# Standard Indian License Plate Regex Patterns
# 1. Standard: 2 letters, 2 digits, 1-3 letters, 4 digits (e.g., TN09AB1234, TG03A7349, DL4CAA1234)
STD_PATTERN = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$")
# 2. Bharat Series: 2 digits (year), BH, 4 digits, 1-2 letters (e.g., 22BH1234AA)
BH_PATTERN = re.compile(r"^(\d{2})(BH)(\d{4})([A-Z]{1,2})$")
# 3. Flexible Fallback Pattern: alphanumeric 6 to 12 chars
GENERIC_PATTERN = re.compile(r"^[A-Z0-9]{6,12}$")

# OCR character confusion maps
DIGIT_TO_LETTER = {
    '0': 'O', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '7': 'T', '8': 'B'
}
LETTER_TO_DIGIT = {
    'O': '0', 'I': '1', 'Z': '2', 'A': '4', 'S': '5', 'B': '8', 'G': '6', 'D': '0', 'Q': '0'
}

# Common OCR confusion for Indian State Prefixes
STATE_CONFUSIONS = {
    'IG': 'TG', '1G': 'TG', 'IC': 'TG', 'TC': 'TG', 'TO': 'TG', '1C': 'TG', 'T6': 'TG', 'T5': 'TS', 'T9': 'TG',
    'LG': 'TG', 'LC': 'TG', 'D1': 'DL', 'K4': 'KA', 'M1': 'MH', 'T1': 'TN', 'U1': 'UP', 'H1': 'HR', 'A1': 'AP'
}


class PlateProcessor:
    """Normalizes, cleans, and validates Indian license plate numbers with OCR error correction."""

    @staticmethod
    def clean_raw_text(raw_text: str) -> str:
        """Removes spaces, punctuation, special symbols, and converts to uppercase."""
        if not raw_text:
            return ""
        # Remove anything except alphanumeric characters
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        return cleaned

    @classmethod
    def correct_ocr_characters(cls, text: str) -> str:
        """
        Applies smart character heuristics based on positional Indian plate structure:
        Positions 0-1: State Code (Letters)
        Positions 2-3: RTO Code (Digits)
        Positions 4 to (len-4): Series Code (Letters)
        Last 4 positions: Registration Number (Digits)
        """
        if len(text) < 7:
            return text

        chars = list(text)
        n = len(chars)

        # 0. Check state prefix confusions (e.g. IC -> TG, TC -> TG)
        if n >= 2:
            st = chars[0] + chars[1]
            if st in STATE_CONFUSIONS:
                chars[0] = STATE_CONFUSIONS[st][0]
                chars[1] = STATE_CONFUSIONS[st][1]

        # 1. Check if first two are letters (State Code)
        for i in range(min(2, n)):
            if chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]

        # 2. Check positions 2 and 3 (RTO Digits)
        for i in range(2, min(4, n)):
            if chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]

        # 3. Check last 4 characters (Digits)
        for i in range(max(4, n - 4), n):
            if chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]

        # 4. Check intermediate series (Letters)
        for i in range(4, max(4, n - 4)):
            if chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]

        return "".join(chars)

    @classmethod
    def validate_and_format(cls, raw_text: str) -> Dict[str, Any]:
        """
        Validates the plate string, scores confidence, and returns formatted result.
        """
        cleaned = cls.clean_raw_text(raw_text)
        if not cleaned:
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

        # Check direct match on cleaned string first
        candidate = cleaned
        std_match = STD_PATTERN.match(candidate)
        bh_match = BH_PATTERN.match(candidate)

        # If not matching directly, try applying OCR character confusion corrections
        if not std_match and not bh_match:
            candidate = cls.correct_ocr_characters(cleaned)
            std_match = STD_PATTERN.match(candidate)
            bh_match = BH_PATTERN.match(candidate)

        # Match against Standard Pattern
        if std_match:
            state, rto, series, number = std_match.groups()
            is_valid_state = state in INDIAN_STATES
            score = 0.95 if is_valid_state else 0.80

            # Pad RTO code to 2 digits if single digit
            rto_formatted = rto.zfill(2)
            formatted_plate = f"{state}{rto_formatted}{series}{number}"

            return {
                "valid": True,
                "raw_text": raw_text,
                "cleaned_plate": formatted_plate,
                "state_code": state,
                "rto_code": rto_formatted,
                "series": series,
                "number": number,
                "confidence_score": score,
                "is_indian_format": True,
                "is_valid_state": is_valid_state
            }

        # Match against BH Pattern
        if bh_match:
            year, bh, number, series = bh_match.groups()
            return {
                "valid": True,
                "raw_text": raw_text,
                "cleaned_plate": f"{year}{bh}{number}{series}",
                "state_code": "BH",
                "rto_code": year,
                "series": series,
                "number": number,
                "confidence_score": 0.92,
                "is_indian_format": True,
                "is_valid_state": True
            }

        # Generic Alphanumeric Fallback
        if GENERIC_PATTERN.match(candidate):
            # Soft match for imperfect OCR
            state_candidate = candidate[:2]
            is_valid_state = state_candidate in INDIAN_STATES
            return {
                "valid": len(candidate) >= 6,
                "raw_text": raw_text,
                "cleaned_plate": candidate,
                "state_code": state_candidate if is_valid_state else None,
                "rto_code": None,
                "series": None,
                "number": None,
                "confidence_score": 0.65 if is_valid_state else 0.50,
                "is_indian_format": is_valid_state,
                "is_valid_state": is_valid_state
            }

        return {
            "valid": False,
            "raw_text": raw_text,
            "cleaned_plate": candidate,
            "state_code": None,
            "rto_code": None,
            "series": None,
            "number": None,
            "confidence_score": 0.20,
            "is_indian_format": False,
            "is_valid_state": False
        }
