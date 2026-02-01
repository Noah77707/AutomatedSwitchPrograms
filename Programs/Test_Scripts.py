import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Connect_Controller_Test(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if state == None:
        state = "PAIRING"

    if state == "PAIRING":
        state == home_screen_checker_macro(ctrl, image)

def Return_Home_Test(image: Image_Processing, ctrl: Controller):
    ctrl.tap(BTN_HOME, 0.20, 0.45)
    ctrl.tap(BTN_X, 0.05, 0.20)
    ctrl.tap(BTN_A, 0.05, 2.45)

def Press_A_Repeatadly(image: Image_Processing, ctrl: Controller, state: str | None, number: int | None) -> None:
    ctrl.tap(BTN_A)