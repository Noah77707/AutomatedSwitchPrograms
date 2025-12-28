from dataclasses import dataclass
from typing import Tuple
import numpy as np
import cv2 as cv

ROI = Tuple[int, int, int, int]

@dataclass
class TemplateLandmark:
    template_gray: np.ndarray
    roi: ROI
    threshold: float = 0.85
    hits_required: int = 3
    method: int = cv.TM_CCOEFF_NORMED

class RunStats:
    runs: int = 0
    resets: int = 0
    encounters: int = 0
    action: int = 0
    
    eggs_collected: int = 0
    eggs_hatched: int = 0

    shinies: int = 0

    pokemon_encountered: int = 0
    pokemon_caught:int = 0
    pokemon_released: int = 0
    pokemon_skipped: int = 0

    playtime_seconds: int = 0

def ensure_stats(image):
    if not hasattr(image, 'database_component'):
        image.database_component = RunStats()
