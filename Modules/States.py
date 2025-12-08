import os
import sys
from time import time, monotonic, sleep
from typing import TYPE_CHECKING, Tuple, List, Any, Dict
import Constants as const
import numpy as np

from .Window_Capture import *

from .Image_Processing import Image_Processing

state_timer = 0

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

def pairing_screen_visible(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (209, 209, 209),
        [
        (64, 485),
        (1213, 485)
        ]
    )

def home_screen_visibile(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (45, 45, 45),
        [
            (41, 562),
            (1233, 626),
            (665, 164)
        ]
        
    )

def black_screen(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (0, 0, 0),
        [
            (263, 401),
            (1076, 258),
            (93, 677)
        ]
    )

def controller_already_connected(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (254, 255, 255),
        [
            (73, 694),
            (108, 693)
        ]
    )

def SWSH_title_screen(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (251, 251, 251),
        [
            (485, 346),
            (717, 378),
            (689, 303)
        ]
    )

def SWSH_in_game(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (254, 254, 254),
        [
            (54, 690),
            (8, 690)
        ]
    )

def SWSH_encounter_text(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (51, 51, 51),
        [
            (854, 663),
            (366, 655),
            (1138, 670)
        ]
    )

def BDSP_loading_title_screen(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (224, 225, 225),
        [
            (509, 432),
            (830, 443)
        ]
    )

def BDSP_title_screen(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (17, 210, 245),
        [
            (364, 205),
            (5442, 225),
        ]
    )

def BDSP_box_check(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (238, 230, 158),
        [
            (837, 84),
            (358, 87)
        ]
    )

def BDSP_pokemon_in_box_check(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (182, 162, 100),
        [
            (983, 166),
            (997, 195),
        ]
    )

def BDSP_egg_in_box_check(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (234, 234, 234),
        [
            (986, 166),
            (995, 166),
        ]
    )

def BDSP_shiny_symbol(image: Image_Processing) -> bool:
    return check_image_position_colors(
        image,
        (70, 53, 230),
        [
            (1258, 115),
            (1248, 125)
        ]
    )