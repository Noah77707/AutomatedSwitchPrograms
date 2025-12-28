import os
import sys
from time import time, monotonic, sleep
from typing import TYPE_CHECKING, Tuple, List, Any, Dict
import Constants as const
import numpy as np

from .Dataclasses import *
from .Window_Capture import *

from .Image_Processing import Image_Processing

state_timer = 0

# state checks are where the checked states are stored.
# checked states are states that contain information to colors and pixels for a wanted state
# the porgram willl uses these to check if the pixels specified are withing 7 unit so color to the specified color
# I.E. if the color is 56, 56, 56. then 59, 50, 54 will pass, and 67, 12, 255 will fail
STATE_CHECKS = {
    'GENERIC': {
        'pairing_screen': {
            'color': (209, 209, 209),
            'positions': [
                (64, 485),
                (1213, 485)
            ]
        },
        'home_screen': {
            'color': (45, 45, 45),
            'positions': [
                (41, 562),
                (1233, 626),
                (665, 164)
            ]
        },
        'controller_screen': {
            'color': (69, 69, 69),
            'positions': [
                (142, 303),
                (722, 206),
                (694, 502)
            ]
        },
        'controller_connected': {
            'color': (254, 254, 254),
            'positions': [
                (73, 694),
                (108, 693)
            ]
        },
        'black_screen': {
            'color': (0, 0, 0),
            'positions': [
                (263, 401),
                (1076, 258),
                (93, 677)
            ]
        },
        'white_screen': {
            'color': (255, 255, 255),
            'positions': [
                (263, 401),
                (1076, 258),
                (93, 677)
            ]
        },
        'change_user': {
            'color': (243, 200, 42),
            'positions': {
                (163, 484),
                (173, 484)
            }
        }

    },
    'SWSH': {
        'title_screen': {
            'color': (255, 255, 254),
            'positions': [
                (717, 78),
                (557, 79),
            ],

        },
        'in_game': {
            'color': (254, 254, 254),
            'positions': [
                (54, 690),
                (8, 690),
            ],
        },
        'in_box': {
            'color': (249, 254, 233),
            'positions': [
                (802, 87),
                (868, 665)
            ]
        },
        'pokemon_in_box': {
            'color': (217, 218, 219),
            'positions': [
                (979, 158),
                (972, 345),
                (904, 386)
            ]
        },
        'egg_in_box': {
            'color': (251, 255, 242),
            'positions': [
                (979, 158),
                (972, 345),
                (904, 386)
            ]
        },
        'shiny_symbol': {
            'color': (102, 102, 102),
            'positions': [
                (1253, 122),
                (1263, 113)
            ]
        },
        'encounter_text': {
            'color': (51, 51, 51),
            'positions': [
                (854, 663),
                (366, 655),
                (1138, 670),
            ],
        },
    },
    'BDSP': {
        'loading_title': {
            'color': (224, 225, 225),
            'positions': [
                (509, 432),
                (830, 443),
            ],
        },
        'title_screen': {
            'color': (17, 210, 245),
            'positions': [
                (364, 205),
                (542, 225)
            ],
        },
        'box_open': {
            'color': (238, 230, 158),
            'positions': [
                (837, 84),
                (358, 87),
            ],
        },
        'multi_select':{
            'color': (80, 164, 76),
            'positions': [
                (258, 8),
                (257, 59)
            ]
        },
        'pokemon_in_box': {
            'color': (182, 162, 100),
            'positions': [
                (983, 166),
                (997, 195),
            ],
        },
        'egg_in_box': {
            'color': (234, 234, 234),
            'positions': [
                (986, 166),
                (995, 166),
            ],
        },
        'shiny_symbol': {
            'color': (70, 53, 230),
            'positions': [
                (1258, 115),
                (1248, 125),
            ],
        },
        'text_box': {
            'color': (250, 251, 251),
            'positions': [
                (781, 595),
                (273, 611),
                (1019, 593),
                (1021, 695),
            ],
        },
        'hatchery_pokecenter': {
            'color': (255, 255, 254),
            'positions': [
                (1108, 580),
                (1251, 600),
                (1253, 638)
            ]
        },
        'egg_acquired': {
            'color': (101, 234, 243),
            'positions': [
                (943, 141),
                (941, 253),
                (339, 270),
                (338, 142)
            ]
        },
        'poketch': {
            'color': (48, 0, 144),
            'positions': [
                (1257, 190),
                (1257, 129)
            ]
        }
    },
}

def wait_for_roi_condition(
        image: Image_Processing,
        roi: Tuple[int, int, int, int],
        predicate,
        timeout: float = 2.0,
        min_frames: int = 3,
        ) -> bool:
    start = monotonic()
    good = 0

    # runs while time is 
    while monotonic() - start < timeout:
        frame = getattr(image, 'original_image', None)
        if frame is None:
            sleep(0.01)
            continue
        # This sees if consecutive frames are high enough for the shiny sparkle
        if predicate(frame, roi):
            good += 1
            if good >= min_frames:
                return True
        else:
            good = 0
        sleep(0.01)
    return False
# trhe function that checks the colors
def check_image_position_colors(image: Image_Processing, color: Tuple[int, int, int], positions: List[Tuple[int, int]]) -> bool:
    for position in positions:
        if not image.check_pixel_colors(position, color):
            return False
    return True
# this passes everything to the check_iamge_position_colors. It mainly makes everything more readable
def check_state(image: Image_Processing, game: str, name: str) -> bool:
    cfg = STATE_CHECKS[game][name]
    color = cfg['color']
    positions = cfg['positions']
    return check_image_position_colors(image, color, positions)
# The player can split states. This is mainly used to programs that run othjer programs. I.E. automated_egg for BDSP
def split_state(s: str | None) -> tuple[str, str | None]:
    if not s:
        return (None, None)
    if "|" not in s:
        return (s, None)
    phase, sub = s.split("|", 1)
    return (phase, sub if sub != "None" else None)

def join_state(phase: str, sub: str | None) -> str:
    return f"{phase}|{sub if sub is not None else 'None'}"
# checks if a landmark/template is in a specified roi. This is used to make reliable macros due to the inprecise microcontroller 
def is_in_area(image: Image_Processing, compared_to_image_path: str, roi: Tuple[int, int, int, int], threshold: float = 0.90) -> float:
    frame = getattr(image, 'original_image', None)
    if frame is None:
        return 0.0

    ref = cv.imread(compared_to_image_path, cv.IMREAD_GRAYSCALE)
    if ref is None:
        return 0.0

    x, y, w, h = roi
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    crop = gray[y:y+h, x:x+w]

    if crop.shape[0] < ref.shape[0] or crop.shape[1] < ref.shape[1]:
        return 0.0

    crop = cv.GaussianBlur(crop, (3, 3), 0)
    ref  = cv.GaussianBlur(ref,  (3, 3), 0)

    res = cv.matchTemplate(crop, ref, cv.TM_CCOEFF_NORMED)
    _, maxv, _, _ = cv.minMaxLoc(res)
    print(maxv)
    return float(maxv)

def detect_template(frame_bgr: np.ndarray, lm: TemplateLandmark) -> float:
    x,y,w,h = lm.roi
    crop = frame_bgr[y:y+h, x:x+w]
    gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)

    if gray.shape[0] < lm.template_gray.shape[0] or gray.shape[1] < lm.template_gray.shape[1]:
        return 0.0

    res = cv.matchTemplate(gray, lm.template_gray, lm.method)
    _, maxv, _, _ = cv.minMaxLoc(res)
    return float(maxv)

def _clahe_gray(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("Image is None")

    # Ensure uint8 for CLAHE
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)

    # Handle channel count safely
    if img.ndim == 2:
        gray = img
    elif img.ndim == 3 and img.shape[2] == 1:
        gray = img[:, :, 0]
    elif img.ndim == 3 and img.shape[2] == 3:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    elif img.ndim == 3 and img.shape[2] == 4:
        gray = cv.cvtColor(img, cv.COLOR_BGRA2GRAY)
    else:
        raise ValueError(f"Unsupported image shape: {img.shape}")

    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def _crop_roi(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = roi
    return frame[y:y+h, x:x+w]
# these functinos make a text fragment more visible to the clahe program
def prep_text(img_bgr_or_gray: np.ndarray) -> np.ndarray:
    if img_bgr_or_gray.ndim == 3:
        gray = cv.cvtColor(img_bgr_or_gray, cv.COLOR_BGR2GRAY)
    else:
        gray = img_bgr_or_gray

    gray = cv.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv.INTER_CUBIC)
    gray = cv.GaussianBlur(gray, (3,3), 0)

    # Invert so text becomes white blobs (usually text is dark)
    bw = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)[1]
    return bw

def has_enough_text(bw: np.ndarray, min_ratio: float = 0.01, max_ratio: float = 0.25) -> bool:
    # ratio of "ink" pixels (white in inverted binary)
    ink = float(np.count_nonzero(bw)) / bw.size
    return (ink >= min_ratio) and (ink <= max_ratio)
# this uses those text fragments to see if they are similar. 
def match_text_fragment(
    image: Image_Processing,
    template_bgr_or_gray: np.ndarray,
    roi: Tuple[int,int,int,int],
    sqdiff_max: float = 0.20,
) -> tuple[bool, float]:
    
    frame = image.original_image
    if frame is None:
        sleep(0.001)

    crop = _crop_roi(frame, roi)
    if crop.size == 0:
        return False, 0.0
    x,y,w,h = roi
    crop = frame[y:y+h, x:x+w]
    if crop.size == 0:
        return False, 1.0

    crop_bw = prep_text(crop)
    if not has_enough_text(crop_bw):
        return False, 1.0

    tmpl_bw = prep_text(template_bgr_or_gray)

    res = cv.matchTemplate(crop_bw, tmpl_bw, cv.TM_SQDIFF_NORMED)
    minv, _, _, _ = cv.minMaxLoc(res)  # for SQDIFF, min is best
    return (minv <= sqdiff_max), float(minv)
# this has the player move until a specified landmark is in sight
def walk_until_landmark_dpad(
    ctrl,
    image,
    lm: TemplateLandmark,   # expects: lm.template_gray (np.ndarray), lm.roi, lm.threshold, lm.method
    dpad_dir: int,
    game: str = None,
    state: str = None,
    hold_s: float = 0.10,
    pause_s: float = 0.05,
    max_steps: int = 500,
    template_cache: Optional[dict[int, np.ndarray]] = None,  # key: id(lm)
) -> bool:
    """
    Uses CLAHE-normalized grayscale template matching to reduce time-of-day sensitivity.
    Returns True if found, False if max_steps reached.
    """

    cache_key = id(lm)

    # Load + preprocess template once (optionally cached)
    if template_cache is not None and cache_key in template_cache:
        tmpl_p = template_cache[cache_key]
    else:
        tmpl = getattr(lm, "template_gray", None)
        if not isinstance(tmpl, np.ndarray):
            raise TypeError("lm.template_gray must be a numpy array (already-loaded template image).")
        tmpl_p = _clahe_gray(tmpl)  # safe for 2D gray or 3D bgr
        if template_cache is not None:
            template_cache[cache_key] = tmpl_p

    for _ in range(max_steps):
        frame = getattr(image, "original_image", None)
        if frame is not None:
            crop = _crop_roi(frame, lm.roi)
            if crop.size:
                crop_p = _clahe_gray(crop)
                res = cv.matchTemplate(crop_p, tmpl_p, lm.method)
                _, maxv, _, _ = cv.minMaxLoc(res)
                if maxv >= lm.threshold:
                    return True

        ctrl.dpad(dpad_dir, hold_s)
        if pause_s:
            sleep(pause_s)

    return False