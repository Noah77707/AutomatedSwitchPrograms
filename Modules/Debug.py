import cv2 as cv
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class DebugROI:
    roi: tuple[int, int, int, int]          # (x,y,w,h)
    color: tuple[int, int, int] = (0, 0, 255)  # BGR

class Debug:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)

        self._state: str | None = None
        self._rois: list[DebugROI] = []
        self._focus: DebugROI | None = None

    def set_enabled(self, on: bool) -> None:
        self.enabled = bool(on)

    def clear(self) -> None:
        self._state = None
        self._rois.clear()
        self._focus = None

    def set_rois_for_state(
        self,
        state: str,
        rois: Iterable[tuple[int, int, int, int]],
        color: tuple[int, int, int] = (0, 0, 255),
    ) -> None:
        self._state = state
        self._rois = [DebugROI(tuple(map(int, r)), color) for r in rois]
        self._focus = None

    def add_roi(self, roi: tuple[int, int, int, int], color: tuple[int, int, int] = (0, 0, 255)) -> None:
        self._rois.append(DebugROI(tuple(map(int, roi)), color))

    def set_focus_roi(self, roi: tuple[int, int, int, int], color: tuple[int, int, int] = (255, 0, 0)) -> None:
        self._focus = DebugROI(tuple(map(int, roi)), color)

    def draw(self, frame, current_state: str | None):
        if not self.enabled:
            return frame

        if self._state is not None and current_state != self._state:
            # auto-clear overlays when we leave the state
            self.clear()
            return frame

        for item in self._rois:
            x, y, w, h = item.roi
            cv.rectangle(frame, (x, y), (x + w, y + h), item.color, 2)

        if self._focus is not None:
            x, y, w, h = self._focus.roi
            cv.rectangle(frame, (x, y), (x + w, y + h), self._focus.color, 2)

        return frame


    def log(self, *parts) -> None:
        if self.enabled:
            print(f"[DEBUG] {' '.join(map(str, parts))}")