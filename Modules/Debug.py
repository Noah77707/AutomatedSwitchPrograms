import cv2 as cv
from dataclasses import dataclass
from typing import Iterable
from time import monotonic
import threading
from .Dataclasses import *

@dataclass(frozen=True)
class DebugROI:
    roi: tuple[int, int, int, int]          # (x,y,w,h)
    color: tuple[int, int, int] = (0, 0, 255)  # BGR
    thickness: int = 2

class Debug:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
        self._lock = threading.Lock()
        self._state: str | None = None
        self._items: list[DebugROI] = []
        self._focus: DebugROI | None = None

    def set_enabled(self, on: bool) -> None:
        self.enabled = bool(on)

    def clear(self) -> None:
        with self._lock:
            self._state = None
            self._items.clear()
            self._focus = None

    def set_rois_for_state(
        self,
        state: str,
        rois: Iterable[tuple[int, int, int, int]],
        color: tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
    ) -> None:
        with self._lock:
            self._state = state
            self._items = [DebugROI(tuple(map(int, r)), color, int(thickness)) for r in rois]
            self._focus = None

    def add_roi(self, roi, color = (0, 0, 255), thickness: int = 2) -> None:
        with self._lock:
            self._items.append(DebugROI(tuple(map(int, roi)), color, int(thickness)))

    def set_focus_roi(self, roi, color = (255, 0, 0),  thickness: int = 3) -> None:
        with self._lock:
            self._focus = DebugROI(tuple(map(int, roi)), color, int(thickness))

    def draw(self, frame, current_state: str | None):
        if not self.enabled:
            return frame

        with self._lock:
            state = self._state
            items = list(self._items)
            focus = self._focus

        if state is not None and current_state != state:
            self.clear()
            return frame

        for item in items:
            x, y, w, h = item.roi
            cv.rectangle(frame, (x, y), (x + w, y + h), item.color, item.thickness)

        if focus is not None:
            x, y, w, h = focus.roi
            cv.rectangle(frame, (x, y), (x + w, y + h), focus.color, focus.thickness)

        return frame

    def log(self, *parts) -> None:
        if self.enabled:
            print(f"[DEBUG] {' '.join(map(str, parts))}")
    