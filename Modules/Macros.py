import os
import sys
import time
import serial
from .Controller import Controller

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
def static_restart(ctrl: Controller):
    ctrl.tap(BTN_HOME)
    time.sleep(0.5)
    ctrl.tap(BTN_Y)
    time.sleep(0.5)
    ctrl.tap(BTN_A)
    time.sleep(2) #Make this an actual check to see if the game has closed. Also add a check to see if there is an update.
    ctrl.tap(BTN_A)
    time.sleep(0.5)
    ctrl.tap(BTN_A)

