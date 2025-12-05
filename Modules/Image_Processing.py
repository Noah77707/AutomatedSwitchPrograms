import os
import sys
import cv2 as cv
import numpy as np
import pytesseract
import PyQt6.QtGui as pyqt_g
from typing import Tuple, Union, Dict, Optional, Sequence

import Constants as const

class Image_Processing():
    def __init__(self, image: Union[str, np.ndarray] = ''):
        self.original_image = None
        self.resized_image = None
        self.pyqt_image = None
        self.shiny_detection_time = 0

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
            threshold: int = 7,
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

    
    def is_sparkle_visible(
            self,
            frame: np.ndarray,
            roi: Tuple[int, int, int, int],
            v_thres: int = 230,
            s_max: int = 70,
            min_bright_particles: int = 150,
            ) -> bool:
        x, y, w, h = roi
        h_img, w_img = frame.shape[:2]
        if w <= 0 or h <= 0:
            return False
        if not (0 <= x < w_img or 0 <= y < h_img):
            return False
        
        x2 = min(x + w, w_img)
        y2 = min(y + h, h_img)
        if x2 <= x or y2 <= y:
            return False
        
        crop = frame[y:y2, x:x2]

        hsv = cv.cvtColor(crop, cv.COLOR_BGR2HSV)

        lower = (0, 0, v_thres)
        upper = (180, s_max, 255)
        mask = cv.inRange(hsv, lower, upper)
        bright_pixels = cv.countNonZero(mask)
        return bright_pixels >= min_bright_particles

