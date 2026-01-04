import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *

def Start_SWSH(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if image.state == None:
        image.state = 'PAIRING'

    elif image.state  == 'PAIRING':
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state  == 'START_SCREEN':
        image.state = swsh_start_screens_macro(ctrl, image, image.state)
        return image.state
    
    return image.state

def Static_Encounter_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if not hasattr(image, "debug_rois_collector"):
        image.add_debug_roi(const.SWSH_CONSTANTS['static_roi'], (0,255,0))
        image.debug_rois_collector = True
    
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        image.state = Start_SWSH(image, ctrl, image.state)

    elif state == 'IN_GAME':
        if check_state(image, 'SWSH', 'in_game'):
            ctrl.stick('l', 128, 255, 0.016, True)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A)
            return 'IN_BATTLE'
        
    elif image.state == 'IN_BATTLE':
        if check_state(image, 'SWSH', 'encounter_text'):
            return 'CHECK_SHINY'
        return 'IN_BATTLE'
    
    elif image.state == 'CHECK_SHINY':
        fid = getattr(image, 'frame_id', 0)
        last = getattr(image, 'last_frame_id', -1)
        if fid == last:
            return state
        image.last_frame_id = fid
        roi = const.SWSH_CONSTANTS['static_roi']
            
        shiny_check = image.is_sparkle_visible(
            roi,
            v_thres= const.SWSH_CONSTANTS['static_v_threshold'],
            s_max = const.SWSH_CONSTANTS['static_s_max'],
            min_bright_ratio = const.SWSH_CONSTANTS['static_brightness_ratio']
        )

        image.shiny_frames_checked += 1
        if shiny_check:
            image.shiny_hits += 1

        if image.shiny_hits >= 3: # How many rames are shiny
            image.database_component.pokemon_encountered += 1
            image.database_component.shinies += 1
            return 'FOUND_SHINY'
            
        if image.shiny_frames_checked >= 240:
            image.shiny_frames_checked = 0
            image.database_component.pokemon_encountered += 1
            return 'NOT_SHINY'
        return image.state
    
    elif image.state == 'FOUND_SHINY':
        image.state == "SHINY"

    elif image.state == 'NOT_SHINY':
        image.database_component.resets += 1
        print("Not Shiny")
        ctrl.tap(BTN_HOME, 0.05, 0.45)
        ctrl.tap(BTN_X, 0.05, 0.25)
        ctrl.tap(BTN_A, 0.05, 02.95)
        import time
        now = time.monotonic()
        if now - getattr(image, "_perf_t0", 0) > 5:
            image._perf_t0 = now
            print("debug_rois:", len(getattr(image, "debug_rois", [])))
            print("frame_id:", getattr(image, "frame_id", 0))

        return 'PAIRING'
    return image.state

def Egg_Hatcher_SWSH(ctrl: Controller, image: Image_Processing, state: str | None, input: int) -> str:
    return None

def Pokemon_Releaser_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if image.state == None:
        image.state = 'PAIRING'

    elif image.state == 'PAIRING':
        image.state = home_screen_checker_macro(ctrl, image)
        return image.state
    
    elif image.state == 'HOME_SCREEN' or image.state == 'START_SCREEN':
        image.state = swsh_start_screens_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state == 'IN_GAME':
        if not check_state(image, 'GENERIC', 'black_screen'):
            sleep(2)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
        
    elif image.state == 'IN_BOX':
        if check_state(image, 'SWSH', 'box_open'):
            release_pokemon(ctrl, image, 'SWSH', input)
            image.state = "PROGRAM_FINISHED"
            
    return image.state