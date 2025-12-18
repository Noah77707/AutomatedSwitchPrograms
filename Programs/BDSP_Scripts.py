import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *
from Modules.Dataclasses import *

def Static_Encounter_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    return None

def Egg_Collector_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if state == None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        state = home_screen_checker_macro(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN' or state == 'START_SCREEN':
        state = bdsp_start_screens_macro(ctrl, image, state)
        sleep(1)
        return state
    
    elif state == 'IN_GAME':
        if not hasattr(image, 'egg_count'):
            image.egg_count = 0
        if not hasattr(image, 'egg_phase'):
            image.egg_phase = 0

        if input != 0 and image.egg_count >= int(input):
            return 'PROGRAM_FINISHED'

        roi = const.BDSP_CONSTANTS['nursery_man']
        tpl = cv.imread('Media/BDSP_Images/Day_Care_Sign.png', cv.IMREAD_GRAYSCALE)
        landmark = TemplateLandmark(
            template_gray= tpl,
            roi= (200, 120, 360, 360),
            thresh= 0.88,
            hits_required= 3
        )

        image.debug_draw = True
        image.clear_debug()
        image.add_debug_roi(roi, (0, 255, 0))
        image.add_debug_roi((180, 120, 360, 360), (0, 0, 255))

        frame = image.original_image
        if frame is None:
            return 'CHECK_SHINY'

        frame = image.draw_debug(frame)
        sleep(1.5)

        ctrl.down(BTN_B)
        if is_in_area(image, 'Media/BDSP_Images/Egg_Man_Arms.png', roi = roi, threshold= 0.88) > 0.80 and image.egg_phase == 0:
            for _ in range(4):
                ctrl.dpad(6, 0.14)
            sleep(0.2)
            ctrl.tap(BTN_A)
            
            mash_a_while_textbox(ctrl, image, 'BDSP')

            for _ in range(4):
                ctrl.dpad(2, 0.14)
            sleep(0.2)
            
        if image.egg_phase == 0:
            for _ in range(12):
                ctrl.dpad(0, 0.13)
            image.egg_phase = 1
        elif image.egg_phase == 1:
            walk_until_landmark_dpad(ctrl, image, dpad_dir= 4, lm= landmark, timeout= 6.0)
            image.egg_phase = 2
        else: 
            sleep(0.1)
            ctrl.dpad(0, 0.15)
            image.egg_phase = 0
        ctrl.up(BTN_B)
        return 'IN_GAME'
    return state

def Pokemon_Releaser_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if state == None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        state = home_screen_checker_macro(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN' or state == 'START_SCREEN':
        state = bdsp_start_screens_macro(ctrl, image, state)
        return state
    
    elif state == 'IN_GAME':
        if not check_state(image, 'GENERIC', 'black_screen'):
            sleep(2)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
        
    elif state == 'IN_BOX':
        if check_state(image, 'BDSP', 'box_open'):
            release_pokemon(ctrl, image, 'BDSP', input)
            state = "PROGRAM_FINISHED"
            
    return state