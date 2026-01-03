import os
import sys
import cv2 as cv
import numpy as np
import pytesseract
import PyQt6.QtGui as pyqt_g
from pytesseract import pytesseract as pt
from typing import Tuple, Union, Dict, Optional, Sequence
from time import time, sleep

import Constants as const
from .Dataclasses import *

class Image_Processing():
    def __init__(self, image: Union[str, np.ndarray] = ''):
        self.frame_id = 0
        self.original_image = None
        self.resized_image = None
        self.pyqt_image = None
        self.state = None
        self.playing = False
        self.run = 0
        self.profile = 0
        self.profile_set = False

        self.debug_draw = True
        self.debug_rois = []
        self.debug_pixels = []

        self.shiny_frames_checked = 0
        self.shiny_hits = 0
        self.egg_count = 0
        self.egg_phase = 0
        self.shiny = 0
        
        self.generic_state = None
        self.generic_count = 0
        self.generic_count2 = 0
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

    def ocr_text(self, roi: tuple[int,int,int,int], *, psm: int = 6, timeout_s: int = 1) -> str:
        frame = getattr(self, "original_image", None)
        if frame is None:
            return ""

        x, y, w, h = map(int, roi)
        H, W = frame.shape[:2]

        x1 = max(0, x); y1 = max(0, y)
        x2 = min(W, x + w); y2 = min(H, y + h)
        if x2 <= x1 or y2 <= y1:
            return ""

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""

        gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)
        gray = cv.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv.INTER_CUBIC)
        gray = cv.GaussianBlur(gray, (3, 3), 0)
        bw = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)[1]

        try:
            txt = pytesseract.image_to_string(bw, config=f"--psm {psm}", timeout=timeout_s)
        except pt.TimeoutExpired:
            return ""
        except pytesseract.TesseractNotFoundError:
            return ""
        except Exception:
            return ""

        return " ".join(txt.split()).lower()

    def ocr_text_throttled(self, roi: tuple[int,int,int,int], *, min_interval_s: float = 0.25) -> str:
        now = time.monotonic()
        last_t = getattr(self, "ocr_last_t", 0.0)
        last_roi = getattr(self, "ocr_last_roi", None)

        # cache per ROI
        if last_roi == roi and (now - last_t) < min_interval_s:
            return getattr(self, "ocr_last_txt", "")

        txt = self.ocr_text(roi)
        self.ocr_last_t = now
        self.ocr_last_roi = roi
        self.ocr_last_txt = txt
        return txt

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
        print(f"sparkle ratio: {ratio:.4f}")
        return ratio >= min_bright_ratio

    def clear_debug(self):
        self.debug_rois.clear()
        self.debug_pixels.clear()

    def add_debug_roi(self, roi, color=(0, 0, 255)):
        # roi: (x, y, w, h)
        self.debug_rois.append((roi, color))

    def add_debug_pixel(self, x, y, color=(255, 0, 0)):
        self.debug_pixels.append((x, y, color))

    def draw_debug(self, frame):
        if not self.debug_draw:
            return frame
        
        if not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame
        
        if not self.debug_draw:
            return frame

        debug_frame = frame

        # draw ROIs
        for (roi, color) in self.debug_rois:
            x, y, w, h = roi
            cv.rectangle(debug_frame, (x, y), (x + w, y + h), color, 2)

        # draw pixel markers
        for (x, y, color) in self.debug_pixels:
            cv.rectangle(
                debug_frame,
                (x - 2, y - 2),
                (x + 2, y + 2),
                color,
                1
            )
        return debug_frame
    
