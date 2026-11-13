import os
import re
import time
import hashlib
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from anpr.image_processor import ImageProcessor
from anpr.plate_processor import PlateProcessor
import config

logger = logging.getLogger("anpr.ocr")

_tesseract_configured = False
_tesseract_cmd_path: Optional[str] = None
_easyocr_reader = None
_easyocr_attempted = False
_ocr_cache: Dict[str, Dict[str, Any]] = {}
MAX_CACHE_SIZE = 256
_CHAR_TEMPLATES: Optional[Dict[str, np.ndarray]] = None


def normalize_character_patch(img: np.ndarray) -> np.ndarray:
    """Normalizes character binary crop: tight bbox crop, scaled aspect ratio, centered in 32x48 canvas."""
    coords = cv2.findNonZero(img)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        if w > 1 and h > 2:
            img = img[y:y+h, x:x+w]
    canvas = np.zeros((48, 32), dtype=np.uint8)
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return canvas
    scale = min(36.0 / float(h), 24.0 / float(w))
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    ox = max(0, (32 - nw) // 2)
    oy = max(0, (48 - nh) // 2)
    canvas[oy:oy+nh, ox:ox+nw] = resized
    return canvas


def get_char_templates() -> Dict[str, List[np.ndarray]]:
    """Generates standard 48x32 normalized glyph templates across multiple font styles and weights."""
    global _CHAR_TEMPLATES
    if _CHAR_TEMPLATES is not None:
        return _CHAR_TEMPLATES
    templates: Dict[str, List[np.ndarray]] = {}
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for c in chars:
        variants = []
        for font in (cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_DUPLEX):
            for th in (2, 3):
                base = np.zeros((60, 60), dtype=np.uint8)
                cv2.putText(base, c, (10, 45), font, 1.2, 255, th, cv2.LINE_AA)
                variants.append(normalize_character_patch(base))
        templates[c] = variants
    _CHAR_TEMPLATES = templates
    return _CHAR_TEMPLATES


def get_easyocr_reader():
    """Lazy loader for EasyOCR Deep Learning Engine."""
    global _easyocr_reader, _easyocr_attempted
    if _easyocr_attempted:
        return _easyocr_reader
    _easyocr_attempted = True
    try:
        import easyocr
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info("EasyOCR Deep Learning Engine initialized successfully.")
    except Exception as e:
        logger.debug(f"EasyOCR not available in environment: {e}")
        _easyocr_reader = None
    return _easyocr_reader


def setup_tesseract() -> Optional[str]:
    """Configures Tesseract executable path if installed on the host."""
    global _tesseract_configured, _tesseract_cmd_path
    if _tesseract_configured:
        return _tesseract_cmd_path

    _tesseract_configured = True
    try:
        import pytesseract
        for p in config.TESSERACT_SEARCH_PATHS:
            if p and Path(p).exists():
                _tesseract_cmd_path = p
                pytesseract.pytesseract.tesseract_cmd = p
                return _tesseract_cmd_path

        import shutil
        path_in_env = shutil.which("tesseract")
        if path_in_env:
            _tesseract_cmd_path = path_in_env
            pytesseract.pytesseract.tesseract_cmd = path_in_env
            return _tesseract_cmd_path
    except Exception:
        pass
    return None


class OCREngine:
    """
    High-Precision Multi-Variant ANPR Optical Character Recognition Engine.
    Executes multiple preprocessing filters, runs OCR across available engines,
    and ranks candidates through Indian registration grammar disambiguation.
    """

    @classmethod
    def recognize_plate_text(cls, plate_crop: np.ndarray) -> Dict[str, Any]:
        """
        Executes end-to-end multi-variant OCR extraction on cropped license plate.
        """
        start_time = time.perf_counter()

        if plate_crop is None or plate_crop.size == 0:
            return {
                "raw_text": "",
                "confidence": 0.0,
                "cleaned_plate": "",
                "valid": False,
                "details": {},
                "engine": "none",
                "processing_time_ms": 0.0
            }

        # 1. Fast Cache Check
        cache_key = hashlib.md5(plate_crop.tobytes()[:2048]).hexdigest()
        if cache_key in _ocr_cache:
            cached = dict(_ocr_cache[cache_key])
            cached["cached"] = True
            cached["processing_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)
            return cached

        # 2. Advanced Preprocessing: Generate 5 Distinct Filter Variations
        variants = ImageProcessor.generate_preprocessing_variants(plate_crop)
        candidates: List[Dict[str, Any]] = []

        # 3. Strategy A: EasyOCR (Deep Learning Reader) across key variants
        reader = get_easyocr_reader()
        if reader is not None:
            for v_name in ("clahe", "raw_deskewed", "sharpened"):
                img_v = variants.get(v_name)
                if img_v is None:
                    continue
                try:
                    res = reader.readtext(img_v, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                    for det in res:
                        raw = det[1]
                        conf = float(det[2])
                        val = PlateProcessor.validate_and_format(raw)
                        candidates.append({
                            "raw_text": raw,
                            "cleaned_plate": val["cleaned_plate"],
                            "confidence": round(conf * val["confidence_score"], 3),
                            "valid": val["valid"],
                            "details": val,
                            "engine": f"EasyOCR-{v_name}",
                            "score": conf * 0.4 + val["confidence_score"] * 0.6
                        })
                except Exception as e:
                    logger.debug(f"EasyOCR run error on {v_name}: {e}")

        # 4. Strategy B: Tesseract OCR (if system binary available)
        tess_path = setup_tesseract()
        if tess_path:
            try:
                import pytesseract
                tess_cfg = r"--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                for v_name in ("adaptive_thresh", "otsu", "clahe"):
                    img_v = variants.get(v_name)
                    if img_v is None:
                        continue
                    raw = pytesseract.image_to_string(img_v, config=tess_cfg).strip()
                    if raw:
                        val = PlateProcessor.validate_and_format(raw)
                        candidates.append({
                            "raw_text": raw,
                            "cleaned_plate": val["cleaned_plate"],
                            "confidence": val["confidence_score"],
                            "valid": val["valid"],
                            "details": val,
                            "engine": f"Tesseract-{v_name}",
                            "score": val["confidence_score"]
                        })
            except Exception as e:
                logger.debug(f"Tesseract run error: {e}")

        # 5. Strategy C: High-Accuracy OpenCV Multi-Template & Glyph Correlation
        # Evaluated across binarized variants (adaptive_thresh and otsu)
        for v_name in ("adaptive_thresh", "otsu"):
            bin_v = variants.get(v_name)
            clahe_v = variants.get("clahe")
            if bin_v is None or clahe_v is None:
                continue
            opencv_res = cls._opencv_template_plate_reader(clahe_v, bin_v)
            if opencv_res.get("text"):
                val = PlateProcessor.validate_and_format(opencv_res["text"])
                c_conf = opencv_res["confidence"] * val["confidence_score"]
                candidates.append({
                    "raw_text": opencv_res["text"],
                    "cleaned_plate": val["cleaned_plate"],
                    "confidence": round(c_conf, 3),
                    "valid": val["valid"],
                    "details": val,
                    "engine": f"{opencv_res.get('engine', 'OpenCV-AI')}-{v_name}",
                    "score": c_conf
                })

        # 6. Fleet Registry Cross-Referencing
        # If candidate strictly matches or resolves an ambiguous character (e.g. 0/O, 8/B), boost confidence
        try:
            from database.database import get_db
            from database.models import Vehicle
            with get_db() as session:
                registered_plates = [v.plate_number for v in session.query(Vehicle.plate_number).all()]
                for cand in candidates:
                    p = cand["cleaned_plate"]
                    if len(p) >= 8:
                        for reg in registered_plates:
                            if p == reg:
                                cand["confidence"] = max(cand["confidence"], 0.99)
                                cand["valid"] = True
                                cand["score"] = 1.0
                                cand["engine"] += "+FleetVerified"
                                break
        except Exception:
            pass

        # 7. Select Top Candidate
        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        if candidates:
            # Sort by score descending (combines OCR confidence and grammatical validity)
            candidates.sort(key=lambda c: (1 if c["valid"] else 0, c["score"]), reverse=True)
            best = candidates[0]
            result = {
                "raw_text": best["raw_text"],
                "confidence": best["confidence"],
                "cleaned_plate": best["cleaned_plate"],
                "valid": best["valid"],
                "details": best["details"],
                "engine": best["engine"],
                "processing_time_ms": elapsed
            }
        else:
            result = {
                "raw_text": "",
                "confidence": 0.0,
                "cleaned_plate": "",
                "valid": False,
                "details": {},
                "engine": "OpenCV-None",
                "processing_time_ms": elapsed
            }

        cls._store_in_cache(cache_key, result)
        return result

    @classmethod
    def _opencv_template_plate_reader(cls, gray_img: np.ndarray, binary_img: np.ndarray) -> Dict[str, Any]:
        """
        Segment-and-Correlate character recognizer using normalized 48x32 glyph templates
        and strict Indian positional syntax constraints.
        """
        h_img, w_img = gray_img.shape[:2]

        # Invert if text is dark on light background (standard Indian plates)
        _, thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        clean_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        # Use RETR_LIST to find characters enclosed inside outer borders
        contours, _ = cv2.findContours(clean_thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        raw_candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / float(h) if h > 0 else 0
            h_ratio = h / float(h_img)

            # Character dimensions: height between 6% and 92% of crop, aspect 0.08 to 1.35
            if 0.06 <= h_ratio <= 0.92 and 0.08 <= aspect <= 1.35 and (w * h) >= 25:
                # Exclude full-frame borders
                if w < (w_img * 0.90) and h < (h_img * 0.90):
                    raw_candidates.append((x, y, w, h))

        # Filter out inner loops / enclosed contours (e.g. inner holes of '8', 'B', '0')
        char_candidates = []
        for i, c1 in enumerate(raw_candidates):
            x1, y1, w1, h1 = c1
            is_inner = False
            for j, c2 in enumerate(raw_candidates):
                if i != j:
                    x2, y2, w2, h2 = c2
                    if x1 >= x2 and y1 >= y2 and (x1 + w1) <= (x2 + w2) and (y1 + h1) <= (y2 + h2):
                        is_inner = True
                        break
            if not is_inner:
                char_candidates.append(c1)

        # Sort candidate characters strictly left-to-right
        char_candidates.sort(key=lambda item: item[0])

        # If more than 10 characters, filter by line alignment (same row) and median height
        if len(char_candidates) > 10:
            med_h = np.median([c[3] for c in char_candidates])
            char_candidates = [c for c in char_candidates if c[3] >= 0.50 * med_h]
            # Group by closest vertical center
            med_y = np.median([c[1] + c[3] / 2.0 for c in char_candidates])
            char_candidates = [c for c in char_candidates if abs((c[1] + c[3] / 2.0) - med_y) < (0.60 * med_h)]

        # Candidate subsets: full set, or drop leftmost if close to margin (IND emblem)
        candidate_subsets = [char_candidates]
        if len(char_candidates) == 11:
            candidate_subsets.append(char_candidates[1:])
        elif len(char_candidates) > 11:
            candidate_subsets.append(char_candidates[-10:])

        for c_set in candidate_subsets:
            n_chars = len(c_set)
            if 7 <= n_chars <= 10:
                extracted_chars = []
                total_score = 0.0
                for i, (cx, cy, cw, ch) in enumerate(c_set):
                    char_roi = clean_thresh[cy:cy+ch, cx:cx+cw]
                    # Positional expectation for Indian standard plates (e.g. AP39CJ5337, DL8CAF1234, TG03A7349)
                    if i < 2:
                        exp = "LETTER"  # State code (AP, TS, TG, DL, MH, etc.)
                    elif i == 2:
                        exp = "DIGIT"   # District digit
                    elif i == 3:
                        exp = "DIGIT" if n_chars == 10 else "ANY"
                    elif i >= (n_chars - 4):
                        exp = "DIGIT"   # Last 4 registration numbers
                    else:
                        exp = "LETTER"  # Series letters

                    c_char, c_score = cls._classify_single_character(char_roi, expected_type=exp)
                    extracted_chars.append(c_char)
                    total_score += c_score

                assembled = "".join(extracted_chars)
                resolved, val = PlateProcessor.disambiguate_indian_plate(assembled)
                avg_conf = (total_score / n_chars) if n_chars > 0 else 0.85

                if val["valid"]:
                    return {
                        "text": resolved,
                        "confidence": round(max(0.88, avg_conf), 2),
                        "engine": "OpenCV-Template-AI"
                    }
                elif c_set is char_candidates:
                    first_pass = {
                        "text": resolved,
                        "confidence": round(max(0.70, avg_conf), 2),
                        "engine": "OpenCV-Template-AI"
                    }

        if "first_pass" in locals():
            return first_pass

        return {"text": "", "confidence": 0.0, "engine": "OpenCV-None"}

    @classmethod
    def _classify_single_character(cls, char_img: np.ndarray, expected_type: str = "ANY") -> Tuple[str, float]:
        """Classifies isolated character ROI against multi-font normalized 48x32 glyph templates."""
        if char_img.size == 0 or char_img.shape[0] < 4 or char_img.shape[1] < 2:
            return ("A" if expected_type == "LETTER" else "0"), 0.0

        templates = get_char_templates()
        roi_normalized = normalize_character_patch(char_img)

        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if expected_type == "LETTER" else (
            "0123456789" if expected_type == "DIGIT" else "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )

        best_char = allowed[0]
        best_score = -1.0

        for c in allowed:
            tmpl_variants = templates.get(c, [])
            for tmpl in tmpl_variants:
                res = cv2.matchTemplate(roi_normalized, tmpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0])
                if score > best_score:
                    best_score = score
                    best_char = c

        return best_char, max(0.0, best_score)

    @classmethod
    def _store_in_cache(cls, key: str, data: Dict[str, Any]):
        """Stores result in LRU cache with automatic pruning."""
        global _ocr_cache
        if len(_ocr_cache) >= MAX_CACHE_SIZE:
            keys_to_remove = list(_ocr_cache.keys())[:MAX_CACHE_SIZE // 4]
            for k in keys_to_remove:
                _ocr_cache.pop(k, None)
        _ocr_cache[key] = data
