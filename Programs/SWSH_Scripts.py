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
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        image.state = Start_SWSH(image, ctrl, image.state)

    elif state == 'IN_GAME':
        if check_state(image, 'SWSH', 'in_game'):
            ctrl.stick('l', 128, 255, 0.016, True)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A)
            return return_states(image, "CHECK_SHINY")
    
    elif image.state == 'CHECK_SHINY': 
        # times
        # not shiny: ~2.69
        # shiny: Registeel = 4.577999999979511 
        image.set_debug_rois_for_state('CHECK_SHINY', [const.SWSH_STATES['encounter_name']], (0, 0, 0))
        image.state = shiny_wait_checker(image,
                                    "SWSH",
                                    const.SWSH_STATES['encounter_name'],
                                    0, 
                                    2.8,
                                    3)
        return return_states(image, image.state)
    
    elif image.state == 'FOUND_SHINY':
        image.state == "SHINY"

    elif image.state == 'NOT_SHINY':
        image.database_component.resets += 1
        ctrl.tap(BTN_HOME, 0.05, 0.45)
        ctrl.tap(BTN_X, 0.05, 0.25)
        ctrl.tap(BTN_A, 0.05, 02.95)
        return return_states(image, 'PAIRING')
    
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