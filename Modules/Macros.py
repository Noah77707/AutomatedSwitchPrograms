import os
import sys
import time
from time import monotonic, sleep
import serial
from .Controller import Controller
from .Image_Processing import Image_Processing, Text
from .States import *
from .Database import *
from .Debug import *
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

def release_pokemon(ctrl: Controller, image: Image_Processing, game: str, box_amount: int) -> str:
    def _slot_flags(image: Image_Processing, game: str) -> tuple[bool, bool, bool]:
        """All relevant pokemon releaser states."""
        has_pokemon = check_state(image, game, "pokemon", "pokemon_in_box")
        has_shiny = check_state(image, game, "pokemon", "shiny_symbol")
        has_egg = check_state(image, game, "pokemon", "egg_in_box")
        return has_pokemon, has_shiny, has_egg

    def _release_pokemon(ctrl: Controller):
        """
        Releases the selected pokemon
        Should work for SWSH, BDSP, SV
        """
        ctrl.tap(BTN_A, 0.05, 0.3)
        ctrl.dpad(0); sleep(0.1)
        ctrl.dpad(0); sleep(0.1)
        ctrl.tap(BTN_A, 0.05, 0.15)
        ctrl.dpad(0); sleep(0.1)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_A, 0.05, 0.15)

    cols, rows = 6, 5

    for box in range(int(box_amount)):
        row = 0
        col = 0
        
        for _ in range(rows * cols):
            image.wait_new_frame()
            has_pokemon, has_shiny, has_egg = _slot_flags(image, game)

            if has_pokemon and (not has_shiny) and (not has_egg):
                _release_pokemon(ctrl)
                image.database_component.pokemon_released += 1
            else:
                image.database_component.pokemon_skipped += 1

            if not (row == rows - 1 and col == cols - 1):
                row, col = box_grid_advance(ctrl, row, col)
        next_box(ctrl)

    return "PROGRAM_FINISHED"

def home_screen_checker_macro(ctrl: Controller, image: Image_Processing, state: str | None) -> str:
    image.debugger.set_rois_for_state('PAIRING', [const.GENERIC_STATES['playing']['roi']], (0, 255, 0))

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

    elif check_state(image, 'GENERIC', 'controller_screen'):
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
            ctrl.tap(BTN_A, 0.05, 1)
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
 
def swsh_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'START_SCREEN':
        if check_state(image, 'SWSH', "screens", 'title_screen'):
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

def sv_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'START_SCREEN':
        if check_state(image, 'SV', 'title_screen'):
            ctrl.tap(BTN_A, 0.1, 0.2)
            return 'IN_GAME'
        return "START_SCREEN"
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

def box_grid_advance(ctrl, row: int, col: int, cols: int = 6, rows: int = 5, sleep_time: int = 0.05) -> tuple[int, int]:
    if col < cols - 1:
        ctrl.dpad(2, 0.05); sleep(sleep_time)
        return row, col + 1

    if row < rows - 1:
        ctrl.dpad(4, 0.05); sleep(sleep_time)
        for _ in range(cols - 1):
            ctrl.dpad(6, 0.05); sleep(sleep_time)
        return row + 1, 0

    return row, col

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
# time range is the amount of frames between the first battle textbox and the second battle textbox
# this finds the shiny due to the shiny animation adding a lot more frames inbetween both text boxes
def shiny_wait_checker(image, game, roi, frames: int, time_range_max: float, stable_frames: int = 2):
    now = monotonic()
    fid = getattr(image, 'frame_id', 0)
    last = getattr(image, 'last_frame_id', -1)
    if fid == last:
        return image.state
    image.last_frame_id = fid

    if not hasattr(image, "name"):
        image.name = ""
    if not hasattr(image, "name_captured"):
        image.name_captured = False
    if not hasattr(image, "name_prev"):
        image.name_prev = ""
    if not hasattr(image, "name_streak"):
        image.name_streak = 0

    text_visible = check_state(image, game, "text_box")

    # Rising edge: textbox appears
    if text_visible and not image.generic_bool:
        image.generic_bool = True

        if image.generic_count == 0:
            image.start_time = now
            image.generic_count = 1

            # reset name capture state for this encounter
            image.name = ""
            image.name_captured = False
            image.name_prev = ""
            image.name_streak = 0

        elif image.generic_count == 1:
            image.end_time = now
            image.generic_count = 2

    # While first textbox is visible: capture name when stable (no fixed delay)
    if text_visible and image.generic_bool and image.generic_count == 1 and not image.name_captured:
        raw = Text.recognize_text(image, roi)
        raw = (raw or "").strip()

        # ignore trivial garbage
        if len(raw) >= 3:
            if raw == image.name_prev:
                image.name_streak += 1
            else:
                image.name_prev = raw
                image.name_streak = 1

            if image.name_streak >= stable_frames:
                image.database_component.pokemon_name = raw
                image.name_captured = True
                image.debugger.log("Name:", image.database_component.pokemon_name)

    # Falling edge: textbox disappears
    if (not text_visible) and image.generic_bool:
        image.generic_bool = False

    # Decide after second textbox
    if image.generic_count == 2:
        dt = float(image.end_time - image.start_time)
        image.debugger.log("dt_seconds:", dt)

        # reset for next
        image.generic_count = 0
        image.name_prev = ""
        image.name_streak = 0
        image.name_captured = False
        image.database_component.pokemon_encountered += 1

        add_pokemon_delta(image.game, image.program, image.database_component.pokemon_name, encountered_delta=1)
        if dt < time_range_max:
            image.database_component.resets += 1
            add_program_deltas(image.game, image.program, resets_delta=1)
            image.state = "NOT_SHINY"
        else:
            image.database_component.shinies += 1
            add_pokemon_delta(image.game, image.program, image.database_component.pokemon_name, shinies_delta=1)
            image.state = "FOUND_SHINY"

    return image.state

    joined = " | ".join(lines).lower()
    return all(k.lower() in joined for k in keywords)

def read_lines(image, rois, stable_frames: int = 2, min_len: int = 4) -> list[str] | None:
    lines = []
    for idx, roi in enumerate(rois):
        line = Text.stable_ocr_line(
            image, roi,
            key=f"donut_line_{idx}",
            stable_frames= stable_frames,
            min_len= min_len
        )
        if not line:
            return None
        
        lines.append(line)
    return lines
        