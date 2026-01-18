import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *
import os
import sys
from time import time, monotonic
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Start_SWSH(image: Image_Processing, ctrl: Controller, state: str | None) -> str:
    if image.state == None:
        image.state = 'PAIRING'

    elif image.state  == 'PAIRING':
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state  == 'START_SCREEN':
        image.state = swsh_start_screens_macro(ctrl, image, image.state)
        return image.state
    
    return image.state

def Menu_Navigation(ctrl: Controller, image: Image_Processing, target: str) -> None:
    def get_menu_cursor_index(image: Image_Processing, game: str = "SWSH") -> int | None:
        menu = const.GAME_STATES[game]["menu"]
        for name, cfg in menu.items():
            if check_state(image, game, "menu", name):
                return int(cfg["index"])
        return None

    menu = const.SWSH_STATES["menu"]
    
    target_position = menu[target]['index']
    cur = get_menu_cursor_index(image, "SWSH")
    image.debugger.log("menu cursor:", cur, "target:", target_position)

    if cur is None:
        return
    
    def row(i: int) -> int: return 0 if i < 5 else 1
    def col(i: int) -> int: return i % 5

    if row(cur) != row(target_position):
        ctrl.dpad(0 if row(cur) < row(target_position) else 4, 0.05)
        sleep(0.12)
        cur = get_menu_cursor_index(image, "SWSH")
        if cur is None:
            return
        
    while col(cur) != col(target_position):
        if col(cur) < col(target_position):
            ctrl.dpad(2, 0.05)
        else:
            ctrl.dpad(6, 0.05)
        sleep(0.4)
        nxt = get_menu_cursor_index(image, "SWSH")
        if nxt is None:
            return
        cur = nxt

def Bag_Navigation(ctrl: Controller, image: Image_Processing, pouch: str, target: str) -> None:
    bag = const.SWSH_STATES["bag"]
    
    pouch_name = Text.string_from_roi(image, bag["pouch_name"], stable=True, key="bag_pouch_name")
    image.debugger.log(f"Current pouch: '{pouch_name}', Target pouch: '{pouch}'")
    
    if pouch_name.lower() != pouch.lower():
        ctrl.dpad(2, 0.05); sleep(1)

    target_index = None
    for idx, item_roi in enumerate(bag["items"]):
        item_name = Text.string_from_roi(image, item_roi, stable=True, key=f"bag_item_{idx}")
        image.debugger.log(f"Bag item {idx}: '{item_name}'")
        if item_name.lower() == target.lower():
            target_index = idx
            break   

def Static_Encounter_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, number: int) -> str:    
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        return return_states(image, Start_SWSH(image, ctrl, image.state))

    elif image.state == 'IN_GAME':
        if check_state(image, 'SWSH', 'in_game') and number == 0:
            ctrl.stick('l', 128, 255, 0.016, True)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A)
            return return_states(image, "CHECK_SHINY")
        elif check_state(image, 'SWSH', 'in_game') and number == 1:
            return return_states(image, "CHECK_SHINY")
    
    elif image.state == 'CHECK_SHINY': 
        # times
        # not shiny: ~2.69
        # shiny: Registeel = 4.577999999979511 
        image.debugger.set_rois_for_state('CHECK_SHINY', [const.SWSH_STATES['encounter_name']], (0, 0, 0))
        image.state = shiny_wait_checker(image,
                                    "SWSH",
                                    const.SWSH_STATES['encounter_name'],
                                    0, 
                                    3.2,
                                    3)
        return return_states(image, image.state)
    
    elif image.state == 'FOUND_SHINY':
        image.state = "PROGRAM_FINISHED"

    elif image.state == 'NOT_SHINY':
        if number == 0:
            ctrl.tap(BTN_HOME, 0.05, 0.45)
            ctrl.tap(BTN_X, 0.05, 0.25)
            ctrl.tap(BTN_A, 0.05, 2.95)
            return return_states(image, 'PAIRING')
        elif number == 1:
            if check_state(image, 'SWSH', 'battle_screen'):
                ctrl.dpad(0, 0.05); sleep(0.33)
                ctrl.tap(BTN_A)
                return return_states(image, 'BATTLE_FLEE')
            
    elif image.state == 'BATTLE_FLEE':
        if check_state(image, 'SWSH', 'in_game'):
            return return_states(image, 'MENU')
    
    elif image.state == 'MENU':
        menu = const.SWSH_STATES["menu"]

        all_rois = [roi for item in menu.values() for roi in item["rois"]]
        image.debugger.set_rois_for_state("MENU", all_rois, (0, 0, 0))

        if not check_state(image, 'SWSH', 'menu_screen'):
            ctrl.tap(BTN_X, 0.05, 1)
            return image.state
        sleep(2)
        Menu_Navigation(ctrl, image, 'pokemon_camp')
        ctrl.tap(BTN_A)
        return return_states(image, 'IN_CAMP')
    
    elif image.state == 'IN_CAMP':
        if check_state(image, 'GENERIC', 'black_screen'):
            sleep(1)
        else:
            if not check_state(image, 'SWSH', 'dark_text_box'):
                ctrl.tap(BTN_B, 0.05, 1)
            else:
                ctrl.tap(BTN_A)
                return return_states(image, 'IN_GAME')
    
    return image.state

def Fossil_Reviver_SWSH(ctrl: Controller, image: Image_Processing, state: str | None, input: int) -> str:
    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        return return_states(image, Start_SWSH(image, ctrl, image.state))
    
    elif image.state == 'IN_GAME':
        return None
    
    return return_states(image, image.state)

def Egg_Hatcher_SWSH(ctrl: Controller, image: Image_Processing, state: str | None, input: int) -> str:
    return None

def Pokemon_Releaser_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if image.state == None:
        image.state = 'PAIRING'

    elif image.state == 'PAIRING':
        image.state = home_screen_checker_macro(ctrl, image)
        return image.state
    
    elif image.state == 'HOME_SCREEN' or image.state == 'START_SCREEN':
        image.state = swsh_start_screens_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state == 'IN_GAME':
        if not check_state(image, 'GENERIC', 'black_screen'):
            sleep(2)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
        
    elif image.state == 'IN_BOX':
        if check_state(image, 'SWSH', 'box_open'):
            release_pokemon(ctrl, image, 'SWSH', input)
            image.state = "PROGRAM_FINISHED"
            
    return image.state