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

def check_image_position_colors(image: Image_Processing, color: Tuple[int, int, int], positions: List[Tuple[int, int]]) -> bool:
    for position in positions:
        if not image.check_pixel_colors(position, color):
            return False
    return True

def check_state(image: Image_Processing, game: str, name: str) -> bool:
    cfg = STATE_CHECKS[game][name]
    color = cfg['color']
    positions = cfg['positions']
    return check_image_position_colors(image, color, positions)

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

def walk_until_landmark_dpad(ctrl, image, dpad_dir: int, lm: TemplateLandmark,
                             timeout=5.0, poll_s=0.01) -> bool:
    # press and hold
    ctrl.dpad_down(dpad_dir)

    hits = 0
    t0 = time()

    while time() - t0 < timeout:
        frame = image.original_image
        if frame is None:
            sleep(poll_s)
            continue

        score = detect_template(frame, lm)
        if score >= lm.thresh:
            hits += 1
            if hits >= lm.hits_required:
                ctrl.dpad_up()
                return True
        else:
            hits = 0

        sleep(poll_s)

    ctrl.dpad_up()
    return False
