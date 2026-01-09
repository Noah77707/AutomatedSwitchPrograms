from dataclasses import dataclass
from typing import Tuple
import numpy as np
import cv2 as cv

ROI = Tuple[int, int, int, int]

@dataclass
class TemplateLandmark:
    template_gray: np.ndarray
    roi: ROI
    threshold: float = 0.75
    hits_required: int = 3
    method: int = cv.TM_CCOEFF_NORMED

@dataclass
class ShinyCheckConfig:
    sparkle_roi: ROI
    model_roi: ROI
    
    v_thres: int = 245
    s_max: int = 40
    
    warmup_seconds_after_model: float = 0.35   # ignore right after model appears
    max_window_seconds: float = 2.5            # if no shiny by then, call not shiny
    
    hits_required: int = 8                     # higher than 3
    misses_before_reset: int = 3               # allow brief flicker
    
    min_blob_area: int = 6                     # tune for your resolution
    max_blob_area: int = 220                   # tune for your resolution
    
    max_big_component_ratio: float = 0.60      # reject flashes
    model_edge_density_thres: float = 0.030    # tune


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

def ensure_stats(image):
    if not hasattr(image, 'database_component'):
        image.database_component = RunStats()
