from dataclasses import dataclass, field
from typing import Tuple, Optional, Any
import numpy as np
import cv2 as cv
import threading

ROI = Tuple[int, int, int, int]

@dataclass
class TemplateLandmark:
    template_gray: np.ndarray
    roi: ROI
    threshold: float = 0.75
    hits_required: int = 3
    method: int = cv.TM_CCOEFF_NORMED

@dataclass(frozen=True)
class FramePacket:
    frame: np.ndarray
    fid: int
    cap_index: int
    epoch: int

@dataclass
class CaptureState:
    lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    cap: Any | None = None

    capture_index: int = -1
    capture_status: str = "idle"   # "idle" | "ok" | "fail"\
    capture_status_index: Optional[object] = None      # last index tested
    capture_status_msg: str = ""
    capture_epoch: int = 0

    requested_index: int = -1
    request_epoch: int = 0

    active_index: int = -1
    active_epoch: int = 0

    pending_index: Optional[int] = None
    pending_epoch: int = 0

    status: str = ""
    status_msg: str = ""

    last_cap_fid: int = -1

@dataclass
class RunStats:
    pokemon_name: str = None
    runs: int = 0
    resets: int = 0
    encounters: int = 0
    actions: int = 0
    action_hits: int = 0

    eggs_collected: int = 0
    eggs_hatched: int = 0

    pokemon_encountered: int = 0
    pokemon_caught:int = 0
    pokemon_released: int = 0
    pokemon_skipped: int = 0

    shinies: int = 0
    playtime_seconds: int = 0

@dataclass
class Running:
    running: bool = False
    paused: bool = False
    run_last_t:float = 0.0
    run_seconds:float = 0.0

@dataclass
class ReleasePokemon:
    box_amount: int = 1
    box_i: int = 0
    row: int = 0
    col: int = 0
    