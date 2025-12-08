import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *

def Static_Encounter_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    return None

def Egg_Hatcher_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if state == None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        state = home_screen_checker_macro(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN' or state == 'START_SCREEN' or state == 'TITLE_SCREEN':
        state = bdsp_start_screens_macro(ctrl, image, state)
        return state
    
    elif state == 'IN_GAME':
        if not black_screen(image):
            sleep(2)
            ctrl.tap(BTN_X, 0.05, 0.2)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
            

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
        if not black_screen(image):
            sleep(2)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
        
    elif state == 'IN_BOX':
        image.debug_draw = True
        image.clear_debug()

        image.add_debug_pixel(837, 84, ((0,0,0)))
        image.add_debug_pixel(358, 87, (0, 0, 0))

        frame = image.original_image
        if frame is None:
            return 'CHECK_SHINY'

        frame = image.draw_debug(frame)

        if BDSP_box_check(image):
            release_pokemon(ctrl, image, input)
            
    return state