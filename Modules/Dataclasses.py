from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Any
import numpy as np
import cv2 as cv
import threading

ROI = Tuple[int, int, int, int]
COORD = Tuple[int, int]

@dataclass
class TemplateLandmark:
    template_gray: np.ndarray
    roi: ROI
    threshold: float = 0.75
    hits_required: int = 3
    method: int = cv.TM_CCOEFF_NORMED

@dataclass
class FramePacket:
    fid: int
    t: float
    frame: np.ndarray               # canonical 1280x720 BGR
    ox: float = 0.0                 # raw->canonical crop origin
    oy: float = 0.0
    sx: float = 1.0                 # raw/canonical scale factors
    sy: float = 1.0
    capture_epoch: int = 0

@dataclass
class Calibration:
    canon_w: int = 1280
    canon_h: int = 720

    dx: int = 0
    dy: int = 0

    sx: float = 1.0
    sy: float = 1.0

    # Debug / quality
    score: float = 0.0
    valid: bool = False

@dataclass
class MotionStats:
    mean_diff: float          # mean abs diff (0..255)
    frac_active: float        # fraction of pixels with diff >= diff_thresh (0..1)

@dataclass
class CaptureState:
    lock: threading.Lock = field(default_factory=threading.Lock)

    cap: Optional[object] = None

    capture_index: int = -1
    pending_index: Optional[int] = None
    capture_epoch: int = 0

    status: str = "idle"     # idle | pending | ok | fail
    status_msg: str = ""

    calib: Calibration = field(default_factory=Calibration)

    ox: float = 0.0
    oy: float = 0.0
    sx: float = 1.0
    sy: float = 1.0

    requested_index: int = -1
    request_epoch: int = 0

    active_index: int = -1
    active_epoch: int = 0

    pending_index: Optional[int] = None
    pending_epoch: int = 0

    status: str = ""
    status_msg: str = ""

    last_cap_fid: int = -1
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

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
class Box:
    """
    offsetx: amount of pixels between the box spaces on the x axis
    offsety: amount of pixels between the box spaces on the y axis
    """
    box_amount: int = 1
    box_i: int = 0
    box_start: int = 0
    row: int = 0
    col: int = 0
    rows: int = 5
    cols: int = 6
    offsetx: int = 0
    offsety: int = 0
    cfg: List[COORD] = field(default_factory=list)
    
@dataclass(frozen=True)
class Slot:
    box: int
    row: int
    col: int

@dataclass
class Mon:
    uid: int                 # unique per encountered slot (scan order)
    name: str                # species/forme display name
    dex: int                 # national dex #
    is_shiny: bool
    slot: Slot               # current slot (updates as you move it)
  
@dataclass
class Egg:
    egg_count: int = 0
    egg_phase: int = 0
  
@dataclass 
class SparkleDetectorCfg:
    roi_rel: Tuple[float, float, float, float] = (0.20, 0.18, 0.6, 0.62)
    
    roi_size: Tuple[int, int] = (320, 180)
    
    bright_percentile: float = 99.3
    bright_floor: int = 190  # never go below this

    open_iters: int = 1
    close_iters: int = 1
    kernel_size: int = 3
    
    min_area: int = 6
    max_area: int = 1800

    window_frames: int = 10
    hits_required: int = 3
    cooldown_frames: int = 25
    
    abs_score_min: float = 0.0008
    mad_k: float = 7.0
