import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *

def Pokemon_Releaser_BDSP(self):
    return None

def Egg_Hatcher_BDSP(ctrl: Controller, image: Image_Processing, state: str | None) -> str:
    if state == None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        state = home_screen_checker(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN':
        if home_screen_visibile(image):
            ctrl.tap(BTN_A, 0.05, 0.95)
            ctrl.tap(BTN_A)
            return 'START_SCREEN'
    
    elif state == 'START_SCREEN':
        if BDSP_title_screen(image):
            ctrl.tap(BTN_A)
            return 'IN_GAME'

    return state