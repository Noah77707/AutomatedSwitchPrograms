import os
import sys
import time
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


def release_pokemon(ctrl: Controller, image: Image_Processing, Box_Amount: int) -> str:
    amount_released = 0
    box = 1
    for box in range(int(Box_Amount)): 
        for row in range(5):
            for column in range(6):
                sleep(1)
                if BDSP_pokemon_in_box_check(image) and not BDSP_shiny_symbol(image) and not BDSP_egg_in_box_check(image):
                    print('Debug2')
                    ctrl.tap(BTN_A, 0.05, 0.5)
                    ctrl.dpad(0, 0.05)
                    sleep(0.15)
                    ctrl.dpad(0, 0.05)
                    ctrl.tap(BTN_A, 0.05, 0.2)
                    ctrl.dpad(0, 0.1)
                    ctrl.tap(BTN_A, 0.05, 0.7)
                    ctrl.tap(BTN_A, 0.05, 0.2)
                    amount_released += 1
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
        ctrl.dpad(2, 0.05)
        sleep(0.15)
        ctrl.dpad(2, 0.05)
        sleep(0.15)
        ctrl.tap(BTN_R, 0.10, 0.15)


    return "PROGRAM_FINISHED"

def home_screen_checker_macro(ctrl: Controller, image: Image_Processing) -> str:
    if pairing_screen_visible(image):
        ctrl.tap(BTN_A)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_HOME)
        return 'HOME_SCREEN'
    elif home_screen_visibile(image):
        if controller_already_connected(image):
            ctrl.tap(BTN_A, 0.10, 1.20)
            ctrl.tap(BTN_A, 0.10, 0.95)
            return 'START_SCREEN'
        else:
            ctrl.tap(BTN_A, 0.05, 0.95)
            ctrl.tap(BTN_A, 0.05, 1.05)
            return 'PAIRING'
    elif not pairing_screen_visible(image) and not home_screen_visibile(image):
        ctrl.tap(BTN_A, 0.05, 0.4)
        ctrl.tap(BTN_A, 0.05, 0.3)
        ctrl.tap(BTN_HOME, 0.1, 1.2)
        ctrl.dpad(4, 0.1)
        for _ in range(5):
           sleep(0.07)
           ctrl.dpad(2, 0.05)
        ctrl.tap(BTN_A, 0.05, 1)
        ctrl.tap(BTN_A, 0.05, 0.7)
        ctrl.tap(BTN_L)
        ctrl.tap(BTN_R)
        ctrl.tap(BTN_A, 0.05, 0.7)
        sleep(0.07)
        ctrl.tap(BTN_HOME, 0.05, 0.70)
        ctrl.tap(BTN_HOME)
        return 'IN_GAME'

def bdsp_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if state == 'HOME_SCREEN':
        if home_screen_visibile(image):
            ctrl.tap(BTN_A, 0.05, 1.20)
            ctrl.tap(BTN_A, 0.05, 0.20)
            return 'START_SCREEN'

    elif state == 'START_SCREEN':
        if not black_screen(image) and not BDSP_title_screen(image):
            ctrl.tap(BTN_A, 0.05, 0.95)
            return 'START_SCREEN'
        if BDSP_title_screen(image):
            sleep(1)
            ctrl.tap(BTN_A)
            return 'IN_GAME'
        
    return state

