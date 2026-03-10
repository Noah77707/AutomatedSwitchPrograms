# Window_Capture.py
import cv2 as cv
import threading
from typing import Optional
import numpy as np

class WindowCapture:
    """
    Latest-frame capture.
    - Background thread reads as fast as the camera delivers.
    - Stores only the newest frame.
    - Provides (frame, frame_id) atomically.
    """
    def __init__(
        self,
        switch_capture_index: int,
        *,
        w: int = 1280,
        h: int = 720,
        fps: int = 60,
        backend: int = cv.CAP_DSHOW,
        buffer_size: int = 1,
    ):

        self._lock = threading.Lock()
        self._running = True

        self._frame: Optional[np.ndarray] = None
        self._frame_id: int = 0

        cap = cv.VideoCapture(switch_capture_index, backend)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open capture device {switch_capture_index}")

        cap.set(cv.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv.CAP_PROP_FRAME_HEIGHT, int(h))
        cap.set(cv.CAP_PROP_FPS, int(fps))
        try:
            cap.set(cv.CAP_PROP_BUFFERSIZE, int(buffer_size))
        except Exception:
            pass
        self.video_capture = cap
        
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ok, frame = self.video_capture.read()
            if not ok or frame is None:
                continue
            
            frame = frame.copy()
            
            with self._lock:
                self._frame = frame
                self._frame_id += 1

    def read_latest(self) -> tuple[Optional[np.ndarray], int]:
        """
        Returns (frame_ref, frame_id).
        frame_ref is the internal numpy array reference. Do NOT mutate it.
        """
        with self._lock:
            return self._frame, self._frame_id

    def stop(self):
        self._running = False
        try:
            if getattr(self, "_thread", None) is not None and self._thread.is_alive():
                self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.video_capture.release()
        except Exception:
            pass