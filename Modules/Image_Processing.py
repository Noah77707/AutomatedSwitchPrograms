import os, sys, threading
import cv2 as cv
import numpy as np
import PyQt6.QtGui as pyqt_g
from pytesseract import pytesseract as pt
from typing import Tuple, Union, Dict, Optional, Sequence
from time import time, sleep, monotonic
import re, json

import Constants as const
from .Dataclasses import *
from .Debug import Debug

pt.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class Image_Processing():
    def __init__(self, image: Union[str, np.ndarray] = ''):
        self.capture_index = 0
        self.capture_status = "idle"   # "idle" | "ok" | "fail"\
        self.capture_status_index = None      # last index tested
        self.capture_status_msg = ""
        self._cap_lock = threading.Lock()
        self._cap = None
        self._pending_capture_index = None
        
        self.original_image = None
        self.state = None
        self.phase = None
        self.playing = False
        self.run = 0
        self.profile = 0
        self.profile_set = False
        self.game = None
        self.program = None

        self.debugger = Debug(enabled=False)

        self.egg_count = 0
        self.egg_phase = 0
        self.cfg = []
        
        self.generic_state = None
        self.generic_count = 0
        self.start_time = 0
        self.end_time = 0
        self.generic_bool = False

        self.last_check_t = 0.0
        self.last_score = 0.0
        self.last_frame_id = 0

        if isinstance(image, str):
            self.original_image = cv.imread(image, cv.IMREAD_UNCHANGED)
        else:
            self.original_image = image

# these three functions are for the capture cards. These allow the user to change the card to whatever they are using
    def request_capture_index(self, idx: int) -> None:
        with self._cap_lock:
            self._pending_capture_index = int(idx)
        self.capture_status = "pending"
        self.capture_status_msg = f"Switching capture to index {int(idx)}..."
        
    def consume_pending_capture_index(self) -> int | None:
        with self._cap_lock:
            idx = self._pending_capture_index
            self._pending_capture_index = None
            return idx

    def _reopen_capture_if_needed(self) -> None:
        with self._cap_lock:
            pending = self._pending_capture_index
            if pending is None or pending == self._capture_index:
                return
            self._pending_capture_index = None
            new_index = pending

        # do IO outside lock
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        cap = cv.VideoCapture(new_index)
        ok, _ = cap.read()
        if not ok:
            cap.release()
            # keep old index unchanged if failed
            return

        self._cap = cap
        self._capture_index = new_index

    def wait_new_frame(self, *, last_id: int | None = None, timeout_s: float = 0.35, sleep_s: float = 0.002) -> int | None:
        start = monotonic()
        if last_id is None:
            last_id = int(getattr(self, "frame_id", 0))

        while monotonic() - start < timeout_s:
            fid = int(getattr(self, "frame_id", 0))
            if fid != last_id:
                return fid
            sleep(sleep_s)

        return None

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
                patterns = const.TEXT["PATTERNS"]  # type: ignore[name-defined]
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

