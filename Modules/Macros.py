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


def release_pokemon(ctrl: Controller, image: Image_Processing, game: str, Box_Amount: int) -> str:
    amount_released = 0
    for box in range(int(Box_Amount)): 
        for row in range(5):
            for column in range(6):
                sleep(1)
                if check_state(image, game, 'pokemon_in_box') and not check_state(image, game, 'shiny_symbol') and not check_state(image, game, 'egg_in_box'):
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
        for _ in range(5):
            sleep(0.17)
            ctrl.dpad(6, 0.05)
        sleep(0.15)
        ctrl.tap(BTN_R, 0.10, 0.15)
    return "PROGRAM_FINISHED"

def home_screen_checker_macro(ctrl: Controller, image: Image_Processing) -> str:
    if check_state(image, 'GENERIC', 'pairing_screen'):
        ctrl.tap(BTN_L)
        ctrl.tap(BTN_R)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_HOME)
        return 'HOME_SCREEN'
    elif check_state(image, 'GENERIC', 'home_screen'):
        if check_state(image, 'GENERIC', 'controller_connected'):
            ctrl.tap(BTN_A, 0.10, 1.20)
            ctrl.tap(BTN_A, 0.10, 0.95)
            return 'START_SCREEN'
        else:
            ctrl.tap(BTN_B, 0.05, 0.95)
            ctrl.tap(BTN_B, 0.05, 1.05)
            return 'PAIRING'
                
    elif not check_state(image, 'GENERIC', 'pairing_screen') and not check_state(image, 'GENERIC', 'home_screen'):
        ctrl.tap(BTN_B, 0.05, 0.4)
        ctrl.tap(BTN_B, 0.05, 0.3)
        ctrl.tap(BTN_HOME, 0.1, 1.2)
        ctrl.dpad(4, 0.2)
        for _ in range(5):
           sleep(0.07)
           ctrl.dpad(2, 0.05)
        ctrl.tap(BTN_A, 0.05, 1)
        sleep(1)
        if not check_state(image, 'GENERIC', 'controller_screen'):
            ctrl.tap(BTN_HOME)
            ctrl.tap(BTN_HOME)
            return 'PAIRING'
        else:
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_L)
            ctrl.tap(BTN_R)
            ctrl.tap(BTN_A, 0.05, 0.7)
            sleep(0.07)
            ctrl.tap(BTN_HOME, 0.05, 1.25)
            ctrl.tap(BTN_HOME)
            return 'IN_GAME'
    
def swsh_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if state == 'START_SCREEN':
        if check_state(image, 'SWSH', 'title_screen'):
            ctrl.btn(BTN_A, 0.1, 0.2)
            return 'IN_GAME'

def bdsp_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if state == 'HOME_SCREEN':
        if check_state(image, 'GENERIC', 'home_screen'):
            ctrl.tap(BTN_A, 0.05, 1.20)
            ctrl.tap(BTN_A, 0.05, 0.20)
            return 'START_SCREEN'

    elif state == 'START_SCREEN':
        if not check_state(image, 'GENERIC', 'black_screen') and not check_state(image, 'BDSP', 'title_screen'):
            ctrl.tap(BTN_A, 0.05, 0.95)
            return 'START_SCREEN'
        if check_state(image, 'BDSP', 'title_screen'):
            sleep(1)
            ctrl.tap(BTN_A)
            return 'IN_GAME'
        
    return state

def mash_a_while_textbox(ctrl, image, game= str, max_seconds=15.0, press_interval=0.20, gone_confirm=30):

    t0 = time()
    last_press = 0.0
    gone_streak = 0

    while time() - t0 < max_seconds:
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
            sleep(0.05)

    return False
