import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *

def Return_Home_Test(ctrl: Controller) -> None:
    home_macro(Controller)

def Connect_Controller_Test(ctrl: Controller) -> None:
    ctrl.tap(4)
    ctrl.tap(5)
    ctrl.tap(2)
    ctrl.tap(12)
    print("HOME: Connect_Controller_Test")
