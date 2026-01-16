import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *

def Start_SV(image: Image_Processing, ctrl: Controller, state: str | None):
    ensure_stats(image)
    if image.state is None:
        image.state = 'PAIRING'
        return image.state

    elif image.state in ('PAIRING'):
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state  == 'START_SCREEN':
        image.state = sv_start_screens_macro(ctrl, image, image.state)
        return image.state
    return return_states(image, image.state)

def Pokemon_Releaser_SV(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        return return_states(image, Start_SV(image, ctrl, image.state))

    elif image.state == 'IN_GAME':
        if check_state(image, "GENERIC", "black_screen"):
            return return_states(image, "LOADING_SCREEN")
        
    elif image.state == "LOADING_SCREEN":
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(1)
            return return_states(image, "IN_GAME1")
        
    elif image.state == "IN_GAME1":
        ctrl.tap(BTN_X, 0.05, 0.5)
        return return_states(image, "IN_MENU")
    
    elif image.state == "IN_MENU":
        ctrl.dpad(2, 0.05); sleep(0.33)
        ctrl.dpad(4, 0.05); sleep(0.33)
        ctrl.tap(BTN_A)
        if check_state(image, "SV", "box_screen"):
            return return_states(image, "IN_BOX")
        
    elif image.state == "IN_BOX":
        release_pokemon(ctrl, image, "SV", 0)
        return return_states(image, "PROGRAM_FINISHED")
