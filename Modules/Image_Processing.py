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
        self.phase = None
        self.playing = False
        self.run = 0
        self.profile = 0
        self.profile_set = False

        self.debug_draw = False
        self.debug_rois = []
        self.debug_focus_roi: tuple[tuple[int,int,int,int], tuple[int,int,int]] | None = None
        self.debug_state = None

        self.shiny_frames_checked = 0
        self.shiny_hits = 0
        self.egg_count = 0
        self.egg_phase = 0
        self.shiny = 0
        
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

    def clear_debug(self):
        self.debug_rois.clear()
        self.debug_focus_roi = None
        self.debug_state = None

    def add_debug_roi(self, roi, color=(0, 0, 255)):
        # roi: (x, y, w, h)
        self.debug_rois.append((roi, color))

    def set_debug_rois_for_state(self, state: str, rois, color=(0, 0, 255)) -> None:
        self.debug_state = state
        out = []
        for r in rois:
            out.append((tuple(map(int, r)), color))
        self.debug_rois = out
        self.debug_focus_roi = None

    def set_debug_focus_roi(self, roi, color=(255, 0, 0)) -> None:
        self.debug_focus_roi = (tuple(map(int, roi)), color)
    
    def draw_debug(self, frame):
        if self.debug_state != self.state:
            return frame
        
        rois = self.debug_rois
        if isinstance(rois, list):
            for item in rois:
                try:
                    roi, color = item  # expected ((x,y,w,h), (b,g,r))
                    x, y, w, h = map(int, roi)
                    cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                except Exception as e:
                    print("BAD debug_rois item (not (roi,color)):", item, e)
                    continue

        if self.debug_focus_roi is not None:
            roi, color = self.debug_focus_roi
            x, y, w, h = map(int, roi)
            cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)

        return frame
        
