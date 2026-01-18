import os
import sys
from time import time, monotonic
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Start_SV(image: Image_Processing, ctrl: Controller, state: str | None):
    ensure_stats(image)
    if image.state == None:
        image.state = 'PAIRING'
        return image.state

    elif image.state == 'PAIRING':
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state

    elif image.state == 'START_SCREEN':
        image.state = sv_start_screens_macro(ctrl, image, image.state)
        return image.state
    return return_states(image, image.state)

def Menu_Navigation(ctrl: Controller, image: Image_Processing, target: str) -> None:
    def get_menu_cursor_index(image: Image_Processing, game: str = "SV") -> int | None:
        menu = const.GAME_STATES[game]["menu"]
        for name, cfg in menu.items():
            if check_state(image, game, "menu", name):
                return int(cfg["index"])
        return None

    menu = const.SV_STATES["menu"]
    
    target_position = menu[target]['index']
    cur = get_menu_cursor_index(image, "SV")
    image.debugger.log("menu cursor:", cur, "target:", target_position)

    if cur is None:
        return
    
    def row(i: int) -> int: return 0 if i < 5 else 1
    def col(i: int) -> int: return i % 5

    if row(cur) != row(target_position):
        ctrl.dpad(0 if row(cur) < row(target_position) else 4, 0.05)
        sleep(0.12)
        cur = get_menu_cursor_index(image, "SV")
        if cur is None:
            return
        
    while col(cur) != col(target_position):
        if col(cur) < col(target_position):
            ctrl.dpad(2, 0.05)
        else:
            ctrl.dpad(6, 0.05)
        sleep(0.4)
        nxt = get_menu_cursor_index(image, "SV")
        if nxt is None:
            return
        cur = nxt

def Pokemon_Releaser_SV(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        return return_states(image, Start_SV(image, ctrl, image.state))

    elif image.state == 'IN_GAME':
        if check_state(image, "GENERIC", "black_screen"):
            return return_states(image, "LOADING_SCREEN")
        
    elif image.state == "LOADING_SCREEN":
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(1)
            return return_states(image, "IN_GAME1")
        
    elif image.state == "IN_GAME1":
        ctrl.tap(BTN_X, 0.05, 0.5)
        return return_states(image, "IN_MENU")
    
    elif image.state == "IN_MENU":
        ctrl.dpad(2, 0.05); sleep(0.33)
        ctrl.dpad(4, 0.05); sleep(0.33)
        ctrl.tap(BTN_A)
        if check_state(image, "SV", "box_screen"):
            return return_states(image, "IN_BOX")
        
    elif image.state == "IN_BOX":
        release_pokemon(ctrl, image, "SV", 0)
        return return_states(image, "PROGRAM_FINISHED")
