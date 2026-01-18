import os
import sys
import cv2 as cv
import numpy as np
import PyQt6.QtGui as pyqt_g
from pytesseract import pytesseract as pt
from typing import Tuple, Union, Dict, Optional, Sequence
from time import time, sleep
import re, json

import Constants as const
from .Dataclasses import *
from .Debug import Debug

pt.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class Image_Processing():
    def __init__(self, image: Union[str, np.ndarray] = ''):
        self.frame_id = 0
        self.original_image = None
        self.resized_image = None
        self.pyqt_image = None
        self.state = None
        self.phase = None
        self.playing = False
        self.run = 0
        self.profile = 0
        self.profile_set = False
        self.game = None
        self.program = None

        self.debugger = Debug(enabled=False)

        self.shiny_frames_checked = 0
        self.shiny_hits = 0
        self.egg_count = 0
        self.egg_phase = 0
        self.shiny = 0
        self.name = 0
        self.donut_cfg = []
        
        self.generic_state = None
        self.generic_count = 0
        self.start_time = 0
        self.end_time = 0
        self.generic_bool = False

        self.last_check_t = 0.0
        self.last_score = 0.0
        self.last_frame_id = 0

        self.ocr_last_t = 0.0
        self.ocr_last_roi = (0, 0, 0, 0)
        self.ocr_last_txt = None

        if isinstance(image, str):
            self.original_image = cv.imread(image, cv.IMREAD_UNCHANGED)
        else:
            self.original_image = image

    def resize_image(self, desired_size = const.MAIN_FRAME_SIZE):
        if self.original_image is None:
            return
        width, height = self.original_image.shape[1::-1]
        aspect_ratio = width / height
        max_size_index = np.argmax((width, height))

        if max_size_index == 0:
            new_size = [
                desired_size[max_size_index],
                int(desired_size[max_size_index] / aspect_ratio)
            ]
        else:
            new_size = [
                int(desired_size[max_size_index] * aspect_ratio),
                desired_size[max_size_index]
            ]
        self.resized_image = cv.resize(self.original_image, new_size)

    def get_pyqt_image(self, image: np.ndarray) -> None:
        if len(image.shape) == 3:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            aux_image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
            qt_format = pyqt_g.QImage.Format.Format_RGB888
        else:
            height, width = image.shape
            bytes_per_line = width
            aux_image = image
            qt_format = pyqt_g.QImage.Format.Format_Grayscale8

        qt_image = pyqt_g.QImage(aux_image, width, height, bytes_per_line, qt_format)
        self.pyqt_image = pyqt_g.QPixmap.fromImage(qt_image)
    
    def check_pixel_colors(
            self,
            position: Tuple[int, int],
            color: Tuple[int, int, int],
            threshold: int = 10,
            frame: Optional[np.ndarray] = None
    ) -> bool:
        
        if frame is None:
            frame = getattr(self, 'original_image', None)
        if frame is None:
            return False
        
        height, width = frame.shape[:2]        
        x, y = position
        if not (0 <= x < width and 0 <= y < height):
            return False
        
        pixel = frame[y, x]
        diffs = [abs(int(pixel[c]) - color[c]) for c in range(3)]
        return not any(d > threshold for d in diffs)

    def debug_pixel(image, pos, expected):
        frame = image.original_image
        if frame is None:
            print("No frame")
            return
        x, y = pos
        b, g, r = frame[y, x]
        eb, eg, er = expected
        print(
            f"pos={pos} pixel=({b},{g},{r}) expected=({eb},{eg},{er}) "
            f"diff=({b-eb},{g-eg},{r-er})"
    )

    def is_sparkle_visible(self, roi, v_thres, s_max, min_bright_ratio: float) -> bool:
        frame = getattr(self, 'original_image', None)
        x, y, w, h = roi
        h_img, w_img = frame.shape[:2]
        if w <= 0 or h <= 0:
            return False
        if not (0 <= x < w_img and 0 <= y < h_img):
            return False

        x2 = min(x + w, w_img)
        y2 = min(y + h, h_img)
        if x2 <= x or y2 <= y:
            return False

        crop = frame[y:y2, x:x2]
        hsv = cv.cvtColor(crop, cv.COLOR_BGR2HSV)

        mask = cv.inRange(hsv, (0, 0, v_thres), (180, s_max, 255))

        bright = cv.countNonZero(mask)
        ratio = bright / mask.size
        return ratio >= min_bright_ratio

class Text:
    @staticmethod
    def load_pokemon_name_set(path: str) -> set[str]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data["names"])

    @staticmethod
    def normalize_ocr_name(s: str) -> str:
        s = (s or "").strip().lower()
        s = s.replace("’", "'")
        s = re.sub(r"[^a-z0-9\s\-']", "", s)
        s = s.replace("'", "")
        s = re.sub(r"\s+", "-", s)
        s = re.sub(r"-+", "-", s)
        return s.strip("-")

    @staticmethod
    def canonicalize_with_set(raw: str, name_set: set[str]) -> str:
        slug = Text.normalize_ocr_name(raw)
        if slug in name_set:
            return slug
        compact = slug.replace("-", "")
        if compact in name_set:
            return compact
        return slug

    @staticmethod
    def ocr_line(image, roi, *, psm: int = 7) -> str:
        frame = getattr(image, "original_image", None)
        if frame is None:
            return ""

        x, y, w, h = map(int, roi)
        crop = frame[y : y + h, x : x + w]
        if crop.size == 0:
            return ""

        gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)
        gray = cv.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv.INTER_CUBIC)
        gray = cv.GaussianBlur(gray, (3, 3), 0)
        bw = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]

        txt = pt.image_to_string(bw, config=f"--oem 1 --psm {psm}")
        return re.sub(r"\s+", " ", (txt or "")).strip()

    @staticmethod
    def stable_ocr_line(image, roi, *, key: str, stable_frames: int = 2, min_len: int = 4) -> str:
        prev_key = f"_ocr_prev_{key}"
        streak_key = f"_ocr_streak_{key}"
        stable_key = f"_ocr_stable_{key}"

        raw = Text.ocr_line(image, roi, psm=7).strip()

        if len(raw) < min_len:
            setattr(image, prev_key, "")
            setattr(image, streak_key, 0)
            setattr(image, stable_key, "")
            return ""

        prev = getattr(image, prev_key, "")
        if raw == prev:
            streak = getattr(image, streak_key, 0) + 1
        else:
            streak = 1
            setattr(image, prev_key, raw)

        setattr(image, streak_key, streak)

        if streak >= stable_frames:
            setattr(image, stable_key, raw)
            return raw

        return ""

    @staticmethod
    def _prep_for_matching(s: str) -> str:
        s = (s or "").strip()
        s = s.replace("\n", " ").replace("\r", " ")
        s = re.sub(r"\s+", " ", s)
        return s

    @staticmethod
    def extract_name(line: str, patterns: list[str]) -> str:
        line = Text._prep_for_matching(line)
        if not line:
            return ""

        for pat in patterns:
            m = re.search(pat, line, flags=re.IGNORECASE)
            if not m:
                continue
            raw = (m.group(1) or "").strip(" .,'!¡’")
            return raw

        return ""

    @staticmethod
    def display_capitalize(slug_or_name: str) -> str:
        """
        Converts:
          "mr-mime" -> "Mr Mime"
          "ho-oh"   -> "Ho Oh"
          "type-null" -> "Type Null"
        """
        s = (slug_or_name or "").strip()
        if not s:
            return ""
        s = s.replace("_", "-")
        parts = [p for p in s.split("-") if p]
        return " ".join(p[:1].upper() + p[1:].lower() for p in parts)

    @staticmethod
    def recognize_text(image, roi) -> str:
        # OCR the ROI (single line) and extract candidate name using shared patterns
        line = Text.ocr_line(image, roi, psm=7)
        if not line:
            return ""

        # Expect patterns in constants.TEXT["PATTERNS"]
        patterns = getattr(image, "pokemon_text_patterns", None)
        if not isinstance(patterns, list):
            # fallback: look for module-level TEXT if you imported it
            try:
                patterns = TEXT["PATTERNS"]  # type: ignore[name-defined]
            except Exception:
                patterns = [
                    r"\bwild\s+(.+?)\s+appeared\b",
                    r"\bencountered\s+(?:a\s+)?wild\s+(.+?)(?:[.!]|$)",
                    r"^(.+?)\s+hatched\s+from\s+the\s+egg\b",
                    r"\bgo!?\s+(.+?)(?:[.!]|$)",
                    r"^(.+?)\s+appeared\b",
                ]

        raw_name = Text.extract_name(line, patterns)
        if not raw_name:
            return ""

        name_set = getattr(image, "pokemon_name_set", None)
        if isinstance(name_set, set):
            key = Text.canonicalize_with_set(raw_name, name_set)   # slug or compact
        else:
            key = Text.normalize_ocr_name(raw_name)

        return Text.display_capitalize(key)

    @staticmethod
    def string_from_roi(image, roi, *, psm: int = 7, stable: bool = False, key: str = "roi") -> str:
        if stable:
            return Text.stable_ocr_line(image, roi, key=key, stable_frames=2, min_len=1)
        return Text.ocr_line(image, roi, psm=psm)
