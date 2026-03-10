import os, sys, threading
import cv2 as cv
import numpy as np
import PyQt6.QtGui as pyqt_g
from skimage import measure
from imutils import contours
from collections import deque
from pytesseract import pytesseract as pt
from typing import Tuple, Union, Dict, Optional, Sequence
from time import time, sleep, monotonic
import re, json

import Constants as const
from Modules.Window_Capture import WindowCapture
from .Dataclasses import *
from .Debug import Debug

pt.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class Image_Processing():
    def __init__(self, image: Union[str, np.ndarray] = ''):
        self._lock = threading.Lock()

        self._frame_lock = threading.Lock()
        self._packet: Optional[FramePacket] = None
        self.frame_id = 0
        self.original_image = None
        self.state = None
        self.phase = None
        self.playing = False
        self.run = 0
        self.profile = 0
        self.profile_set = False
        self.game = None
        self.program = None

        self.debugger = Debug()
        self.gate = FrameGate()
        self.database_component = RunStats()
        self.capture = CaptureState()
        self.box = Box()
        self.egg = Egg()
        self.rois: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self.pokemon_name_set = Text.load_pokemon_name_set("Media/pokemon_names.json")

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
            path = image.strip()
            if path:
                self.publish_frame(cv.imread(path, cv.IMREAD_UNCHANGED))
            else:
                self.original_image = None
        elif image is None:
            self.original_image = None
        else:
            self.original_image = image

    def publish_frame(self, frame_bgr: np.ndarray, *, fid: Optional[int] = None) -> None:
        """Publish a frame into (original_image, frame_id) atomically."""
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            with self._lock:
                self.original_image = None
                self.frame_id += 1 if fid is None else int(fid)
            return

        norm, (ox, oy), (sx, sy) = self.normalize_frame(frame_bgr, out_w=1280, out_h=720)

        with self._lock:
            self.original_image = norm
            self.frame_id = int(fid) if fid is not None else (self.frame_id + 1)

        with self.capture.lock:
            self.capture.norm_offset = (int(ox), int(oy))
            self.capture.norm_scale = (float(sx), float(sy))

    def request_capture_index(self, idx: int) -> None:
        idx = int(idx)
        with self.capture.lock:
            cur = int(getattr(self.capture, "capture_index", -1))
            pend = getattr(self.capture, "pending_index", None)

            # No-op if already active or already pending
            if idx == cur or pend == idx:
                return

            self.capture.pending_index = idx

        self.capture.capture_status = "pending"
        self.capture.capture_status_msg = f"Switching capture to index {idx}..."
        
    def consume_pending_capture_index(self) -> int | None:
        with self.capture.lock:
            idx = self.capture.pending_index
            self.capture.pending_index = None
            return idx

    @staticmethod
    def auto_trim_borders(frame_bgr, thresh=8):
        gray = cv.cvtColor(frame_bgr, cv.COLOR_BGR2GRAY)
        # pixels > thresh are “content”
        mask = gray > thresh
        ys, xs = np.where(mask)
        if len(xs) == 0 or len(ys) == 0:
            return frame_bgr, (0, 0)  # no trim

        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()

        cropped = frame_bgr[y0:y1+1, x0:x1+1]
        return cropped, (x0, y0)

    @staticmethod
    def normalize_frame(frame_bgr, out_w: int = 1280, out_h: int = 720, *, trim_thresh: int = 8):
        """
        Returns:
          norm_frame_bgr, (ox, oy), (sx, sy)

        ox, oy: crop offset in original frame
        sx, sy: scale from cropped -> normalized (pixels multiply by sx/sy)
        """
        cropped, (ox, oy) = Image_Processing.auto_trim_borders(frame_bgr, thresh=trim_thresh)

        if cropped is None or getattr(cropped, "size", 0) == 0:
            return None, (0, 0), (1.0, 1.0)

        ch, cw = cropped.shape[:2]
        if cw <= 0 or ch <= 0:
            return None, (0, 0), (1.0, 1.0)

        sx = float(out_w) / float(cw)
        sy = float(out_h) / float(ch)

        norm = cv.resize(cropped, (int(out_w), int(out_h)), interpolation=cv.INTER_LINEAR)
        return norm, (ox, oy), (sx, sy)

    @staticmethod
    def normalize_to_canon(frame_bgr: np.ndarray, canon_w: int, canon_h: int) -> np.ndarray:
        # Optional: trim near-black borders (letterbox)
        gray = cv.cvtColor(frame_bgr, cv.COLOR_BGR2GRAY)
        mask = gray > 8
        ys, xs = np.where(mask)
        if len(xs) and len(ys):
            x0, x1 = xs.min(), xs.max()
            y0, y1 = ys.min(), ys.max()
            cropped = frame_bgr[y0:y1+1, x0:x1+1]
        else:
            cropped = frame_bgr

        if cropped.shape[1] != canon_w or cropped.shape[0] != canon_h:
            cropped = cv.resize(cropped, (canon_w, canon_h), interpolation=cv.INTER_LINEAR)

        return cropped

    def snapshot(self) -> Tuple[int, Optional[np.ndarray]]:
        with self._frame_lock:
            return int(self.frame_id), self.original_image
        
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
    def recognize_pokemon(image, roi) -> str:
        line = Text.ocr_line(image, roi, psm=7)
        if not line:
            return ""

        patterns = getattr(image, "pokemon_text_patterns", None)
        if not isinstance(patterns, list):
            try:
                patterns = const.TEXT["PATTERNS"]
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

    @staticmethod
    def clean_box_name(raw: str) -> str:
        s = (raw or "").strip()
        # common ocr junk
        s = s.replace("’", "'").replace("`", "'")
        # remove gender symbols
        s = re.sub(r"[♀♂]", "", s)
        s = re.sub(r"[\*\?_¢”\"“´`]", "", s)
        s = re.sub(r"\s+", " ", s).strip()

        s = re.sub(r"\s+\d+$", "", s).strip()

        s = re.sub(r"[^A-Za-z\s\-']", "", s)
        s = re.sub(r"\s+", " ", s).strip()

        if len(s) < 3:
            return ""
        if s.upper() in {"TE", "TV", "TI", "TIE", "THE"}:
            return ""

        return s
        
    @staticmethod
    def _snap_to_name_set(s: str, name_set: set[str]) -> str:
        """
        Try to map OCR string to a valid pokemon in name_set.
        If not found, try trimming trailing tokens like 'S', 'Co', etc,
        but ONLY accept a trim if it becomes a valid name in the set.
        """
        s = (s or "").strip()
        if not s:
            return ""

        slug = Text.normalize_ocr_name(s)
        if slug in name_set:
            return Text.display_capitalize(slug)
        compact = slug.replace("-", "")
        if compact in name_set:
            return Text.display_capitalize(compact)

        parts = s.split()
        if len(parts) >= 2:
            for k in (1, 2):
                trimmed = " ".join(parts[:-k]).strip()
                if not trimmed:
                    continue
                slug2 = Text.normalize_ocr_name(trimmed)
                if slug2 in name_set:
                    return Text.display_capitalize(slug2)
                compact2 = slug2.replace("-", "")
                if compact2 in name_set:
                    return Text.display_capitalize(compact2)

        return ""

    @staticmethod
    def recognize_box_name(image, roi) -> str:
        line = Text.ocr_line(image, roi, psm=7)
        line = Text.clean_box_name(line)
        if not line:
            return ""

        name_set = getattr(image, "pokemon_name_set", None)
        if isinstance(name_set, set):
            snapped = Text._snap_to_name_set(line, name_set)
            if snapped:
                return snapped
            return "" 

        return line

    def read_lines(image, rois, key: str, stable_frames: int = 2, min_len: int = 4) -> list[str] | None:
        lines = []
        for idx, roi in enumerate(rois):
            line = Text.stable_ocr_line(
                image, roi,
                key=f"{key}{idx}",
                stable_frames= stable_frames,
                min_len= min_len
            )
            if not line:
                return None
            
            lines.append(line)
        return lines

class Calibration:
    def calibrate_offset(
        frame_bgr,
        tpl_gray,
        *,
        search_roi: Tuple[int,int,int,int],
        expected_center_xy: Tuple[int,int],
        threshold: float = 0.75,
    ) -> Optional[Tuple[int,int,float]]:
        x, y, w, h = map(int, search_roi)
        crop = frame_bgr[y:y+h, x:x+w]
        if crop.size == 0:
            return None

        gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)
        res = cv.matchTemplate(gray, tpl_gray, cv.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv.minMaxLoc(res)
        if maxv < threshold:
            return None

        th, tw = tpl_gray.shape[:2]
        found_cx = x + maxloc[0] + tw // 2
        found_cy = y + maxloc[1] + th // 2

        exp_cx, exp_cy = expected_center_xy
        dx = int(found_cx - exp_cx)
        dy = int(found_cy - exp_cy)
        return dx, dy, float(maxv)

    def apply_offset_to_roi(roi: Tuple[int,int,int,int], dx: int, dy: int) -> Tuple[int,int,int,int]:
        x, y, w, h = map(int, roi)
        return (x + dx, y + dy, w, h)

    def apply_offset_to_xy(xy: Tuple[int,int], dx: int, dy: int) -> Tuple[int,int]:
        x, y = map(int, xy)
        return (x + dx, y + dy)
   
class FrameGate:
    def __init__(self, downscale_w: int = 320, downscale_h: int = 180):
        self._last_seen_fid: int = -1
        self._prev_small_gray: Optional[np.ndarray] = None
        self._curr_small_gray: Optional[np.ndarray] = None
        self._down_w = int(downscale_w)
        self._down_h = int(downscale_h)

    def seen_fid(self) -> int:
        return self._last_seen_fid

    def update(self, image) -> bool:
        """
        Pulls current published frame from image and updates cached grayscale.
        Returns True only when a NEW frame_id was processed.
        """
        fid = int(getattr(image, "frame_id", 0))
        if fid == self._last_seen_fid:
            return False

        frame = getattr(image, "original_image", None)
        if frame is None or getattr(frame, "size", 0) == 0:
            # still mark as seen so we don't spin on same fid with None
            self._last_seen_fid = fid
            return True

        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        small = cv.resize(gray, (self._down_w, self._down_h), interpolation=cv.INTER_AREA)

        self._prev_small_gray = self._curr_small_gray
        self._curr_small_gray = small
        self._last_seen_fid = fid
        return True

    def _roi_to_small(self, image, roi: ROI) -> ROI:
        frame = getattr(image, "original_image", None)
        h, w = frame.shape[:2]
        x, y, rw, rh = map(int, roi)

        sx = self._down_w / float(w)
        sy = self._down_h / float(h)

        xs = int(x * sx)
        ys = int(y * sy)
        ws = max(1, int(rw * sx))
        hs = max(1, int(rh * sy))
        xs = max(0, min(self._down_w - 1, xs))
        ys = max(0, min(self._down_h - 1, ys))
        ws = min(ws, self._down_w - xs)
        hs = min(hs, self._down_h - ys)
        return xs, ys, ws, hs

    def motion(self, image, roi: Optional[ROI] = None, *, diff_thresh: int = 12) -> MotionStats:
        """
        Computes motion between prev and curr cached frames.
        Needs at least 2 frames to return meaningful values.
        """
        if self._prev_small_gray is None or self._curr_small_gray is None:
            return MotionStats(mean_diff=0.0, frac_active=0.0)

        prev = self._prev_small_gray
        curr = self._curr_small_gray

        if roi is not None:
            xs, ys, ws, hs = self._roi_to_small(image, roi)
            prev = prev[ys:ys+hs, xs:xs+ws]
            curr = curr[ys:ys+hs, xs:xs+ws]

        diff = cv.absdiff(curr, prev)
        mean_diff = float(diff.mean())
        frac_active = float((diff >= int(diff_thresh)).mean())
        return MotionStats(mean_diff=mean_diff, frac_active=frac_active)

    def wait_motion_condition(
        self,
        image,
        *,
        roi: Optional[ROI] = None,
        above: bool,
        threshold: float,
        metric: str = "frac_active",   # "frac_active" or "mean_diff"
        diff_thresh: int = 12,
        stable_frames: int = 3,
        timeout_s: float = 2.0,
        poll_sleep: float = 0.002,
    ) -> bool:
        """
        Wait until motion metric is consistently above/below threshold for stable_frames NEW frames.
        - above=True  -> require metric >= threshold
        - above=False -> require metric <= threshold
        """
        t0 = monotonic()
        streak = 0
        last_id = int(getattr(image, "frame_id", 0))

        while monotonic() - t0 < timeout_s:
            if hasattr(image, "wait_new_frame"):
                image.wait_new_frame(last_id=last_id, timeout_s=min(0.35, timeout_s))
            fid = int(getattr(image, "frame_id", 0))
            if fid == last_id:
                sleep(poll_sleep)
                continue
            last_id = fid

            # update gate cache for this frame
            self.update(image)

            stats = self.motion(image, roi=roi, diff_thresh=diff_thresh)
            value = getattr(stats, metric)

            cond = (value >= threshold) if above else (value <= threshold)
            if cond:
                streak += 1
                if streak >= int(stable_frames):
                    return True
            else:
                streak = 0

            sleep(poll_sleep)

        return False

    def wait_stable(self, image, *, roi: Optional[ROI] = None, frac_thresh: float = 0.01, stable_frames: int = 5, timeout_s: float = 2.0) -> bool:
        # “stable” = little motion
        return self.wait_motion_condition(
            image, roi=roi, above=False, threshold=frac_thresh,
            metric="frac_active", diff_thresh=12,
            stable_frames=stable_frames, timeout_s=timeout_s
        )

    def wait_moving(self, image, *, roi: Optional[ROI] = None, frac_thresh: float = 0.05, stable_frames: int = 2, timeout_s: float = 2.0) -> bool:
        # “moving” = noticeable motion
        return self.wait_motion_condition(
            image, roi=roi, above=True, threshold=frac_thresh,
            metric="frac_active", diff_thresh=12,
            stable_frames=stable_frames, timeout_s=timeout_s
        )
    
class SparkleDetector:
    def __init__(self, cfg: SparkleDetectorCfg | None = None):
        self.cfg = cfg or SparkleDetectorCfg()
        self._scores = deque(maxlen=self.cfg.window_frames)
        self._hits = deque(maxlen=self.cfg.window_frames)
        self._cooldown = 0
        self._last_frame_id: Optional[int] = None
        
        self.last_score = 0.0
        
    def _roi_from_rel(shape, rel):
        H, W = shape[:2]
        rx, ry, rw, rh = rel
        x = int(rx * W); y = int(ry * H)
        w = int(rw * W); h = int(rh * H)
        x = max(0, min(x, W - 1))
        y = max(0, min(y, H - 1))
        w = max(1, min(w, W - x))
        h = max(1, min(h, H - y))
        return x, y, w, h

    def _mad(a: np.ndarray) -> float:
        m = float(np.median(a))
        return float(np.median(np.abs(a - m))) + 1e-9
    # def ImageProcesses(self, image: Image_Processing):
    #     gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    #     blur = cv.GaussianBlur(gray, (11, 11), 0)
    #     thresh = cv.threshold(blur, 200, 255, cv.THRESH_BINARY)[1]
    #     thresh = cv.erode(thresh, None, iterations=2)
    #     thresh = cv.dilate(thresh, None, iterations=4)
    #     labels = measure.label(thresh, neightbors = 8, background=0)
    #     mask = np.zeros(thresh.shape, dtype="uint8")