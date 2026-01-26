import os
import sys
from time import time, monotonic
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Start_SV(image: Image_Processing, ctrl: Controller, state: str | None):
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
    def get_menu_cursor_index(image: Image_Processing, game: str = "SV", attempts:int = 12, required_hits: int = 2) -> int | None:
        menu = const.GAME_STATES[game]["menu"]

        hits: dict[int, int] = {}
        for _ in range(attempts):
            try:
                image.wait_new_frame(timeout_s=0.25)
            except Exception:
                pass
            
            for name, cfg in menu.items():
                if check_state(image, game, "menu", name):
                    idx = int(cfg["index"])
                    hits[idx] = hits.get(idx, 0) + 1
                    if hits[idx] >= required_hits:
                        return idx
                    break
            
            sleep(0.002)
        return None
    menu = const.GAME_STATES["SV"]["menu"]
    if target not in menu:
        image.debugger.log(f"Menu_Navigation: unknown target {target}")
        ctrl.dpad(0, 0.05); sleep(0.33)
    
    if not wait_state(image, "SV", False, 2.0, "screens", "menu_screen"):
        image.debugger.log("Menu_Navigation: menu_screen never appeared")
        return

    menu = const.SV_STATES["menu"]
    
    target_position = menu[target]['index']
    cur = get_menu_cursor_index(image, "SV")
    image.debugger.log("menu cursor:", cur, "target:", target_position)

    if cur is None:
        return
    
    def col(i: int) -> int: return 0 if i < 7 else 1
    def row(i: int) -> int: return i % 7

    if col(cur) != col(target_position):
        ctrl.dpad(2 if col(cur) < col(target_position) else 6, 0.05)
        sleep(0.12)
        cur = get_menu_cursor_index(image, "SV")
        if cur is None:
            return
        
    while row(cur) != row(target_position):
        if row(cur) < row(target_position):
            ctrl.dpad(0, 0.05)
        else:
            ctrl.dpad(4, 0.05)
        sleep(0.4)
        nxt = get_menu_cursor_index(image, "SV")
        if nxt is None:
            return
        cur = nxt

def Pokemon_Releaser_SV(image: Image_Processing, ctrl: Controller, state: str | None, number: int | None) -> str:
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        return return_states(image, Start_SV(image, ctrl, image.state))

    elif image.state == 'IN_GAME':
        sleep(1)
        ctrl.tap(BTN_X, 0.05, 0.5)
        return return_states(image, "IN_MENU")
    
    elif image.state == "IN_MENU":
        menu = const.SV_STATES["menu"]

        all_rois = [roi for item in menu.values() for roi in item["rois"]]

        image.debugger.set_rois_for_state("IN_MENU", all_rois, (0, 0, 0))
        sleep(2)
        Menu_Navigation(ctrl, image, "boxes")
        ctrl.tap(BTN_A); sleep(1.75)
        image.debugger.clear()
        return return_states(image, "IN_BOX")
    
    elif image.state == "IN_BOX":
        return release_pokemon(ctrl, image, "SV", image.cfg["inputs"][0])
        
