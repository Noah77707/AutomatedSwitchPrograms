import os
import sys
import time
from time import monotonic
import serial
from .Controller import Controller
from .Image_Processing import Image_Processing
from .States import *

# controller_buttons.py
BTN_Y = 0
BTN_B = 1
BTN_A = 2
BTN_X = 3
BTN_L = 4
BTN_R = 5
BTN_ZL = 6
BTN_ZR = 7
BTN_MINUS = 8
BTN_PLUS = 9
BTN_LSTICK = 10
BTN_RSTICK = 11
BTN_HOME = 12
BTN_CAPTURE = 13

def return_phase(image: Image_Processing, phase: str) -> str:
    if image.phase != phase:
        image.phase = phase
    return phase

def return_states(image: Image_Processing, state: str) -> str:
    if image.state != state:
        image.state = state
        image.debug_rois_state = state
    return state

def release_pokemon(ctrl: Controller, image: Image_Processing, game: str, box_amount: int) -> str:
    for box in range(int(box_amount)): 
        for row in range(5):
            for column in range(6):
                sleep(1)
                if check_state(image, game, 'pokemon_in_box') and not check_state(image, game, 'shiny_symbol') and not check_state(image, game, 'egg_in_box'):
                    ctrl.tap(BTN_A, 0.05, 0.5)
                    ctrl.dpad(0, 0.05)
                    sleep(0.15)
                    ctrl.dpad(0, 0.05)
                    ctrl.tap(BTN_A, 0.05, 0.2)
                    ctrl.dpad(0, 0.1)
                    ctrl.tap(BTN_A, 0.05, 0.7)
                    ctrl.tap(BTN_A, 0.05, 0.2)
                    image.database_component.pokemon_released += 1
                else:
                    image.database_component.pokemon_skipped += 1
                if column < 5:
                    ctrl.dpad(2, 0.05)
            if row < 4:
                ctrl.dpad(4, 0.05)
                for _ in range(5):
                    sleep(0.17)
                    ctrl.dpad(6, 0.05)
        ctrl.dpad(4, 0.05)
        sleep(0.15)
        ctrl.dpad(4, 0.05)
        sleep(0.15)
        ctrl.dpad(4, 0.05)
        sleep(0.30)
        for _ in range(5):
            sleep(0.17)
            ctrl.dpad(6, 0.05)
        sleep(0.15)
        ctrl.tap(BTN_R, 0.10, 0.15)
    return "PROGRAM_FINISHED"
    
def home_screen_checker_macro(ctrl: Controller, image: Image_Processing, state: str | None) -> str:
    image.set_debug_rois_for_state('PAIRING', [(194, 400, 136, 35)], (0, 255, 0))

    if not hasattr(image, "_playing_lm"):
        image._playing_lm = get_landmark("GENERIC", "playing", 0.7)
    lm = image._playing_lm

    if check_state(image, 'GENERIC', 'pairing_screen'):
        ctrl.tap(BTN_L)
        ctrl.tap(BTN_R)
        sleep(1)
        ctrl.tap(BTN_A, 0.1, 1.5)
        ctrl.tap(BTN_HOME, 0.05, 0.5)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'controller_screen') and check_state(image, 'GENERIC', 'player_1'):
        ctrl.tap(BTN_A, 0.05, 1.5)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'local_communication'):
        ctrl.tap(BTN_A, 0.05, 1.5)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'home_screen') and check_state(image, 'GENERIC', 'controller_connected'):
        if not hasattr(image, "playing_last_check_t"):
            image.playing_last_check_t = 0.0
        if not hasattr(image, "playing_last_score"):
            image.playing_last_score = 0.0

        now = monotonic()
        if now - image.playing_last_check_t >= 0.15:
            image.playing_last_check_t = now
            image.playing_last_score = detect_template(image.original_image, lm)

        score = image.playing_last_score
        if score >= lm.threshold:
            ctrl.tap(BTN_A)
            image.playing = True
            image.state= 'IN_GAME'
        else:
            ctrl.tap(BTN_A, 0.05, 0.75)
            if image.profile_set == False:
                for _ in range(image.profile - 1):
                    ctrl.dpad(2, 0.05); sleep(0.3)
                image.profile_set = True
            ctrl.tap(BTN_A, 0.05, 0.75)
            image.state= 'START_SCREEN'
        return image.state

    elif check_state(image, 'GENERIC', 'home_screen') and not check_state(image, 'GENERIC', 'controller_connected'):
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_B)
        image.state= 'PAIRING'

    elif image.state == 'PAIRING' and not check_state(image, 'GENERIC', 'home_screen') and not check_state(image, 'GENERIC', 'pairing_screen'):
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_HOME, 0.05, 0.4)
        ctrl.dpad(4, 0.2)
        for _ in range(5):
           sleep(0.07)
           ctrl.dpad(2, 0.05)
        ctrl.tap(BTN_A, 0.05, 1)
        image.state= 'PAIRING'
    
    else:
        if hasattr(image, "playing_checked"):
            image.playing_checked = False


    return image.state

        # ctrl.tap(BTN_B, 0.05, 0.3)
        # ctrl.tap(BTN_HOME, 0.1, 1.2)
        # ctrl.dpad(4, 0.2)
        # for _ in range(5):
        #    sleep(0.07)
        #    ctrl.dpad(2, 0.05)
        # ctrl.tap(BTN_A, 0.05, 1)
        # sleep(1)
        # if not check_state(image, 'GENERIC', 'controller_screen'):
        #     ctrl.tap(BTN_HOME)
        #     ctrl.tap(BTN_HOME)
        #     return 'PAIRING'
        # else:
        #     if check_state(image, 'GENERIC', 'local_communication'):
        #         ctrl.tap(BTN_A)
            
        #     ctrl.tap(BTN_A, 0.05, 0.7)
        #     ctrl.tap(BTN_L)
        #     ctrl.tap(BTN_R, 0.05, 1)
        #     ctrl.tap(BTN_A, 0.1, 1)
        #     sleep(1)
        #     if check_state(image, 'GENERIC', 'player_1'):
        #         ctrl.tap(BTN_HOME, 0.1, 1.75)
        #         ctrl.tap(BTN_HOME)
        #     return 'IN_GAME'
    
def swsh_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'START_SCREEN':
        if check_state(image, 'SWSH', 'title_screen'):
            ctrl.tap(BTN_A, 0.1, 0.2)
            return 'IN_GAME'
        return "START_SCREEN"
    return image.state

def bdsp_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'HOME_SCREEN':
        if check_state(image, 'GENERIC', 'home_screen'):
            mash_a_while_textbox(ctrl, image, 'BDSP')
            return 'START_SCREEN'

    elif image.state == 'START_SCREEN':
        if not check_state(image, 'GENERIC', 'black_screen') and not check_state(image, 'BDSP', 'title_screen'):
            ctrl.tap(BTN_A, 0.05, 0.95)
            return 'START_SCREEN'
        if check_state(image, 'BDSP', 'title_screen'):
            sleep(1)
            ctrl.tap(BTN_A)
            return 'IN_GAME'
        
    return image.state

def mash_a_while_textbox(
        ctrl,
        image,
        game= str,
        max_seconds=15.0,
        press_interval=0.20,
        gone_confirm=30,
        watch_state: str | None = None
):
    t0 = time()
    last_press = 0.0
    gone_streak = 0

    while time() - t0 < max_seconds:
        if watch_state and check_state(image, game, watch_state):
            saw_watch = True
        
        visible = check_state(image, game, "text_box")

        if visible:
            gone_streak = 0
            now = time()
            if now - last_press >= press_interval:
                ctrl.tap(BTN_A, 0.05, 0.0)
                last_press = now
            sleep(0.05)
        else:
            gone_streak += 1
            if gone_streak >= gone_confirm:
                return True
            sleep(0.1)

    return saw_watch

def box_grid(ctrl, row: int, col:int) -> None:
    if col < 5:
        ctrl.dpad(2, 0.05)
    else:
        if row < 4:
            ctrl.dpad(4, 0.05)
            for _ in range(5):
                sleep(0.17)
                ctrl.dpad(6, 0.05)

def next_box(ctrl) -> None:
    for _ in range(4):
        ctrl.dpad(0, 0.05); sleep(0.17)
    for _ in range(5):
        ctrl.dpad(6, 0.05); sleep(0.17)
    sleep(0.17)
    ctrl.tap(BTN_R)

def grab_egg(ctrl, image, game: str) -> None:
    for _ in range(image.egg_phase):
        ctrl.dpad(2, 0.05); sleep(0.17)
    ctrl.tap(BTN_A, 0.05, 0.17)
    for _ in range(5):
        ctrl.dpad(4, 0.05); sleep(0.17)
    ctrl.tap(BTN_A, 0.05, 0.17)
    for _ in range(image.egg_phase+1):
        ctrl.dpad(6, 0.05); sleep(0.17)
    ctrl.dpad(4, 0.05); sleep(0.17)
    ctrl.tap(BTN_A)

def put_egg(ctrl, image, game: str) -> None:
    ctrl.dpad(6, 0.05); sleep(0.17)
    ctrl.dpad(4, 0.05); sleep(0.17)
    ctrl.tap(BTN_A, 0.05, 0.17)

    for _ in range(5):
        sleep(0.10)  # let highlight + symbol render

        if check_state(image, game, "pokemon_in_box"):  # gate: only if something is there
            # confirm shiny over a few frames so one bad frame doesn't miss
            shiny = wait_for_state(image, game, "shiny_symbol", timeout=0.25, min_frames=2)
            if shiny:
                image.shiny += 1

        ctrl.dpad(4, 0.05); sleep(0.17)

    ctrl.tap(BTN_A, 0.05, 0.17)
    ctrl.dpad(0, 0.05); sleep(0.17)
    for _ in range(image.egg_phase):
        ctrl.dpad(2, 0.05); sleep(0.17)
    ctrl.tap(BTN_A, 0.05, 0.17)
    for _ in range(max(0, image.egg_phase - 1)):
        ctrl.dpad(6, 0.05); sleep(0.17)

def wait_for_state(image, game: str, name: str, *, timeout: float = 0.3, min_frames: int = 2) -> bool:
    t0 = monotonic()
    streak = 0
    while monotonic() - t0 < timeout:
        if check_state(image, game, name):
            streak += 1
            if streak >= min_frames:
                return True
        else:
            streak = 0
        sleep(0.02)
    return False
