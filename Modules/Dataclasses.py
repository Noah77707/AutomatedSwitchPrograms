from dataclasses import dataclass
from typing import Tuple
import numpy as np
import cv2 as cv

ROI = Tuple[int, int, int, int]

@dataclass
class TemplateLandmark:
    template_gray: np.ndarray
    roi: ROI
    thresh: float = 0.85
    hits_required: int = 3
    method: int = cv.TM_CCOEFF_NORMED

