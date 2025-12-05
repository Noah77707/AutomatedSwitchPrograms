import os
import sys
import time
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *

def Static_Encounter_SWSH(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if state == None:
        state = "PAIRING"

    if state == "PAIRING":
        if pairing_screen_visible(image):
            ctrl.tap(BTN_A)
            ctrl.tap(BTN_A)
            sleep(0.5)
            ctrl.tap(BTN_A)
            sleep(0.5)
            ctrl.tap(BTN_HOME)
            return 'HOME_SCREEN'
        elif home_screen_visibile(image):
            ctrl.tap(BTN_A)
            sleep(1)
            ctrl.tap(BTN_A)
            return 'START_SCREEN'
    elif state == 'HOME_SCREEN':
        if home_screen_visibile(image):
            print('debug')
            ctrl.tap(BTN_A)
            sleep(1)
            ctrl.tap(BTN_A)
            return 'START_SCREEN'
    elif state == 'START_SCREEN':
        if SWSH_title_screen(image):
            ctrl.tap(BTN_A)
            return 'IN_GAME'
    elif state == 'IN_GAME':
        if SWSH_in_game(image):
            ctrl.stick('l', 128, 255, 0.016, True)
            sleep(0.5)
            ctrl.tap(BTN_A)
            sleep(0.75)
            ctrl.tap(BTN_A)
            sleep(0.75)
            ctrl.tap(BTN_A)
            sleep(0.75)
            ctrl.tap(BTN_A)
            return 'IN_BATTLE'
    elif state == 'IN_BATTLE':
        if SWSH_encounter_text(image):
            return shiny_sparkles_visible(image, [1016, 154, 799, 670], 5, 7, state)
    elif state == 'FOUND_SHINY':
        state = 'FOUND_SHINY'
    elif state == 'NOT_SHINY':
        ctrl.tap(BTN_HOME)
        sleep(0.5)
        ctrl.tap(BTN_X)
        sleep(0.3)
        ctrl.tap(BTN_A)
        sleep(3)
        return 'PAIRING'
    return state