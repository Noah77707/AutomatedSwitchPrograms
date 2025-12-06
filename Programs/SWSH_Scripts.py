import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *

#Tested with registeel. Haven't encountered a shiny yet
def Static_Encounter_SWSH(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    image.debug_draw = False
    if state == None:
        state = "PAIRING"

    if state == "PAIRING":
        state = home_screen_checker(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN':
        if home_screen_visibile(image):
            ctrl.tap(BTN_A, 0.05, 0.95)
            ctrl.tap(BTN_A)
            return 'START_SCREEN'
        
    elif state == 'START_SCREEN':
        if SWSH_title_screen(image):
            ctrl.tap(BTN_A)
            return 'IN_GAME'
        
    elif state == 'IN_GAME':
        if SWSH_in_game(image):
            ctrl.stick('l', 128, 255, 0.016, True)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A)
            return 'IN_BATTLE'
        
    elif state == 'IN_BATTLE':
        if SWSH_encounter_text(image):
            return 'CHECK_SHINY'
        return 'IN_BATTLE'
    
    elif state == 'CHECK_SHINY':
        roi = const.SWSH_CONSTANTS['Static_Roi']

        image.debug_draw = True
        image.clear_debug()
        image.add_debug_roi(roi, (0, 255, 0))

        frame = image.original_image
        if frame is None:
            return 'CHECK_SHINY'

        frame = image.draw_debug(frame)
            
        shiny_check = image.is_sparkle_visible(
            frame,
            roi,
            v_thres= const.SWSH_CONSTANTS['Static_V_Threshold'],
            s_max = const.SWSH_CONSTANTS['Static_S_Max'],
            min_bright_particles = const.SWSH_CONSTANTS['Static_Brightness_Threshold']
        )

        image.shiny_frames_checked += 1
        if shiny_check:
            image.shiny_hits += 1

        if image.shiny_hits >= 3: # How many rames are shiny
            return 'FOUND_SHINY'
            
        if image.shiny_frames_checked >= 360:
            image.shiny_frames_checked = 0
            return 'NOT_SHINY'
        print(image.shiny_frames_checked)
        sleep(0.01)
        return 'CHECK_SHINY'
    
    elif state == 'FOUND_SHINY':
        state == "SHINY"

    elif state == 'NOT_SHINY':
        print("Not Shiny")
        ctrl.tap(BTN_HOME, 0.05, 0.45)
        ctrl.tap(BTN_X, 0.05, 0.25)
        ctrl.tap(BTN_A, 0.05, 02.95)
        return 'PAIRING'
    return state