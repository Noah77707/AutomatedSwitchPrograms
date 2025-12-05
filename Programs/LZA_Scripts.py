import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *

def Bench_reset(self, ctrl: Controller) -> None:
    ctrl.stick('L', 128, 0, 0.05, True)
    ctrl.tap(BTN_A)
    time.sleep(0.5)
    ctrl.tap(BTN_A)