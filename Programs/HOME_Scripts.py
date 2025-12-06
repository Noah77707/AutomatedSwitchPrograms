import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Image_Processing import Image_Processing

def Connect_Controller_Test(ctrl: Controller, image: Image_Processing, state: str | None) -> str:
    if state == None:
        state = "PAIRING"

    if state == "PAIRING":
        state == home_screen_checker(ctrl, image)

def Return_Home_Test(ctrl: Controller, image: Image_Processing):
    ctrl.tap(BTN_HOME, 0.20, 0.45)
    ctrl.tap(BTN_X, 0.05, 0.20)
    ctrl.tap(BTN_A, 0.05, 2.45)