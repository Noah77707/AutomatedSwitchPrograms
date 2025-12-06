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


def home_macro(ctrl: Controller):
    ctrl.tap(BTN_HOME)

def connect_controller(ctrl: Controller):
    ctrl.tap(BTN_L)
    ctrl.tap(BTN_R)
    ctrl.tap(BTN_A)

# Hard reset (Rip soft resets)
def home_screen_checker(ctrl: Controller, image: Image_Processing) -> str:
    if pairing_screen_visible(image):
        ctrl.tap(BTN_A)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_HOME)
        return 'HOME_SCREEN'
    elif home_screen_visibile(image):
        if controller_already_connected(image):
            ctrl.tap(BTN_A, 0.05, 1.20)
            ctrl.tap(BTN_A, 0.05, 0.95)
            return 'START_SCREEN'
        else:
            ctrl.tap(BTN_A, 0.05, 0.95)
            ctrl.tap(BTN_A, 0.05, 0.95)
            return 'PAIRING'

