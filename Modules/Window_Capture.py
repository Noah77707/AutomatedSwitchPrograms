import os
import sys
import numpy as np
import cv2 as cv
import numpy as np
from time import time, sleep
from typing import Optional, List, Union, Tuple
import threading

cv.setLogLevel(0)

class WindowCapture:
    def __init__(self, switch_capture_index: int):
        self.connection_error_image: Optional[np.ndarray] = None
        self._running = True
        self._frame_lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None

        self.video_capture = cv.VideoCapture(switch_capture_index, cv.CAP_DSHOW)
        if not self.video_capture.isOpened():
            raise RuntimeError(f"Could not open capture device {switch_capture_index}")

        self.video_capture.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
        self.video_capture.set(cv.CAP_PROP_FRAME_HEIGHT, 720)
        self.video_capture.set(cv.CAP_PROP_FPS, 60)
        self.video_capture.set(cv.CAP_PROP_BUFFERSIZE, 1)

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        while self._running:
            success, frame = self.video_capture.read()
            if not success:
                self._get_connection_error_image()
                continue

            with self._frame_lock:
                self._frame = frame
    
    def read_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()
    
    def stop(self) -> None:
        self._running = False
        self._thread.join()
        self.video_capture.release()
        cv.destroyAllWindows()

    def _get_connection_error_image(self) -> None:
        if self.connection_error_image is None:
            self.connection_error_image = np.zeros((1080, 1920, 3), dtype=np.uint8)
        position = tuple(a + b for a, b in zip((2, 15), (0, (1920 * 100) //1920)))

        cv.putText(
            self.connection_error_image,
            "Capture card is disconnected. Please reconnect it.",
            position,
            cv.QT_FONT_NORMAL,
            (1920 * 2) // 1920,
            (1920 * 5) // 1920, 
            cv.LINE_AA
        )