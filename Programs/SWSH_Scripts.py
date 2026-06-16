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
        image.state = "PAIRING"

    elif image.state  == "PAIRING":
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state  == "START_SCREEN":
        image.state = swsh_start_screens_macro(ctrl, image, image.state)
        return image.state
    
    return image.state

def Menu_Navigation(ctrl: Controller, image: Image_Processing, target: str) -> None:
    def get_menu_cursor_index(image: Image_Processing, game: str = "SWSH") -> int | None:
        menu = const.GAME_STATES[game]["menu"]

        for name, cfg in menu.items():
            if not isinstance(cfg, dict) or "index" not in cfg:
                continue
            if check_state(image, game, "menu", name):
                return int(cfg["index"])
        return None

    menu = const.SWSH_STATES["menu"]
    
    target_position = menu[target]["index"]
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
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_SWSH(image, ctrl, image.state))

    elif image.state == "IN_GAME":
        if check_state(image, "SWSH", "in_game", "in_game") and number == 0:
            ctrl.stick("l", 128, 255, 0.016, True)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A, 0.05, 0.7)
            ctrl.tap(BTN_A)
            return return_states(image, "CHECK_SHINY")
        elif check_state(image, "SWSH", "in_game", "in_game") and number == 1:
            return return_states(image, "CHECK_SHINY")
    
    elif image.state == "CHECK_SHINY": 
        # times
        # not shiny: ~2.69
        # shiny: Registeel = 4.577999999979511 
        image.debugger.set_rois_for_state("CHECK_SHINY", [const.SWSH_STATES["text"]["encounter_text"]["rois"]], (0, 0, 0))
        image.state = shiny_wait_checker(image,
                                    "SWSH",
                                    const.SWSH_STATES["text"]["encounter_text"]["rois"],
                                    0, 
                                    3.2,
                                    3)
        return return_states(image, image.state)
    
    elif image.state == "FOUND_SHINY":
        image.debugger.clear()
        image.state = "PROGRAM_FINISHED"

    elif image.state == "NOT_SHINY":
        image.debugger.clear()
        if number == 0:
            ctrl.tap(BTN_HOME, 0.05, 0.45)
            ctrl.tap(BTN_X, 0.05, 0.25)
            ctrl.tap(BTN_A, 0.05, 2.95)
            return return_states(image, "PAIRING")
        elif number == 1:
            if check_state(image, "SWSH", "screens" "battle_screen"):
                ctrl.dpad(0, 0.05); sleep(0.33)
                ctrl.tap(BTN_A)
                return return_states(image, "BATTLE_FLEE")
            
    elif image.state == "BATTLE_FLEE":
        if check_state(image, "SWSH", "in_game", "in_game"):
            return return_states(image, "MENU")
    
    elif image.state == "MENU":
        menu = const.SWSH_STATES["menu"]

        all_rois = [roi for item in menu.values() for roi in item["rois"]]
        image.debugger.set_rois_for_state("MENU", all_rois, (0, 0, 0))

        if not check_state(image, "SWSH", "screens", "menu_screen"):
            ctrl.tap(BTN_X, 0.05, 1)
            return image.state
        sleep(2)
        Menu_Navigation(ctrl, image, "pokemon_camp")
        ctrl.tap(BTN_A)
        image.debugger.clear()
        return return_states(image, "IN_CAMP")
    
    elif image.state == "IN_CAMP":
        if check_state(image, "GENERIC", "black_screen"):
            sleep(1)
        else:
            if not check_state(image, "SWSH", "text", "dark_text_box"):
                ctrl.tap(BTN_B, 0.05, 1)
            else:
                ctrl.tap(BTN_A)
                return return_states(image, "IN_GAME")
    
    return image.state

def Fossil_Reviver_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, number: int) -> str:
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_SWSH(image, ctrl, image.state))
    
    elif image.state == "IN_GAME":
        if check_state(image, "SWSH", "in_game", "in_game"):
            return return_states(image, "TALKING")
        
    elif image.state == "TALKING":
        if check_state(image, "SWSH", "text", "text_box"):
            return return_states(image, "TALKING1")
        ctrl.tap(BTN_A, 0.05, 0.5)

    elif image.state == "TALKING1":
        if check_state(image, "SWSH", "text", "reply"):
            ctrl.tap(BTN_A)
            return return_states(image, "FOSSIL1")
        
    elif image.state == "FOSSIL1":
        if check_state(image, "SWSH", "text", "reply"):
            image.debugger.log(image.cfg)
            if image.cfg["fossil1"] == "Fossilized Bird":
               ctrl.tap(BTN_A)
            elif image.cfg["fossil1"] == "Fossilized Fish":
               ctrl.dpad(4, 0.13); sleep(0.33)
               ctrl.tap(BTN_A)
            return return_states(image, "FOSSIL2")
        
    elif image.state == "FOSSIL2":
        if check_state(image, "SWSH", "text", "reply"):
            if image.cfg["fossil2"] == "Fossilized Drake":
               ctrl.tap(BTN_A)
            elif image.cfg["fossil2"] == "Fossilized Dino":
               ctrl.dpad(4, 0.13); sleep(0.33)
               ctrl.tap(BTN_A)
            return return_states(image, "RESTORING")
        
    elif image.state == "RESTORING":
        if check_state(image, "SWSH", "text", "reply"):
            ctrl.tap(BTN_A)
            return return_states(image, "TEXT_BOXES")
        
    elif image.state == "TEXT_BOXES":
        if not check_state(image, "SWSH", "text", "dark_text_box"):
            ctrl.tap(BTN_A, 0.05, 0.5)
        else:
            return return_states(image, "TEMP_TEXT_BOX")
    
    elif state == "TEMP_TEXT_BOX":
        if check_state(image, "SWSH", "text", "dark_text_box"):
            ctrl.tap(BTN_A)
            return image.state
        return return_states(image, "GET_NAME")
        
    elif image.state == "GET_NAME":
        image.debugger.set_rois_for_state("GET_NAME", const.SWSH_STATES["text"]["sent_to_box"]["rois"], (0, 0, 0))
        raw = Text.recognize_pokemon(image, const.SWSH_STATES["text"]["sent_to_box"]["rois"][0])
        raw = (raw or "").strip()
        if raw:
            image.database_component.pokemon_name = raw
            image.database_component.pokemon_encountered += 1
            image.database_component.actions += 1
            ctrl.tap(BTN_A)
            image.debugger.clear()
            if image.database_component.pokemon_encountered % image.cfg["count"] == 0:
                sleep(1)
                return return_states(image, "TO_MENU")
            sleep(1)
            return return_states(image, "IN_GAME")
    
    elif image.state == "TO_MENU":
        if not check_state(image, "SWSH", "screens", "menu_screen") and check_state(image, "SWSH", "text", "text_box"):
            ctrl.tap(BTN_B)
            return image.state
        if not check_state(image, "SWSH", "screens", "menu_screen") and not check_state(image, "SWSH", "text", "text_box"):
            ctrl.tap(BTN_X, 0.05, 1)
            return return_states(image, "MENU")
        
    elif image.state == "MENU":
        menu = const.SWSH_STATES["menu"]

        all_rois = [
            roi
            for cfg in menu.values()
            if isinstance(cfg, dict) and "rois" in cfg
            for roi in cfg["rois"]
        ]
        image.debugger.set_rois_for_state("MENU", all_rois, (0, 0, 0))

        Menu_Navigation(ctrl, image, "pokemon")
        ctrl.tap(BTN_A); sleep(1.75)
        image.debugger.clear()
        return return_states(image, "PARTY_SCREEN")

    elif image.state == "PARTY_SCREEN":
        if check_state(image, "SWSH", "screens", "party_screen"):
            ctrl.tap(BTN_R)
            return return_states(image, "IN_BOX")
        
    elif image.state == "IN_BOX":
        if check_state(image, "SWSH", "screens", "box_screen"):
            return return_states(image, "IN_BOX2")
        return image.state
        
    elif image.state == "IN_BOX2":
        if not hasattr(image, "box_row"):
            image.box_row = 0
            image.box_col = 0

        cfg = getattr(image, "cfg", None) or {}
        target_count = int(cfg.get("count", 0))

        if check_state(image, "SWSH", "pokemon", "shiny_symbol"):
            image.database_component.shinies += 1
            return return_states(image, "PROGRAM_FINISHED")
        else:
            image.debugger.log("NOT SHINY")

        image.generic_count = (int(image.box_row) * 6) + int(image.box_col) + 1
        image.debugger.log("box_count:", image.generic_count, "row:", image.box_row, "col:", image.box_col)

        if target_count > 0 and image.generic_count >= target_count:
            return return_states(image, "RESET_GAME")

        image.box_row, image.box_col = Pokemon_Boxes.box_grid_advance(
            ctrl, image.box_row, image.box_col, sleep_time=0.33
        )
        
        return image.state

    elif image.state == "RESET_GAME":
        image.generic_count = 0
        image.box_row = 0
        image.box_col = 0
        if not check_state(image, "GENERIC", "home_screen"):
            ctrl.tap(BTN_HOME, 0.05,0.75)
            return return_states(image, "RESET2")
        
    elif image.state == "RESET2":
            if check_state(image, "GENERIC", "home_screen"):
                ctrl.tap(BTN_X, 0.05, 1.5)
                ctrl.tap(BTN_A, 0.05, 1.5)
                image.database_component.resets += 1
                return return_states(image, "PAIRING")

    return return_states(image, image.state)

def Egg_Collector_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, number: int) -> str:
    if not hasattr(image, "daycare_tpl"):
        image.daycare_tpl = cv.imread("Media/SWSH_Images/Nursery_Sign.png", cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl
    landmark = TemplateLandmark(
        template_gray=tpl, roi= const.SWSH_STATES["egg"]["nursery_sign"]["rois"], threshold=0.65, hits_required= 2)
   
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_SWSH(image, ctrl, image.state))
    
    elif image.state == "IN_GAME":
        if check_state(image, "SWSH", "in_game", "in_game"):
            sleep(1)
            return return_states(image, "WALKING")
    
    elif image.state == "WALKING":
        image.debugger.clear()
        ctrl.stick_up("L", 0.5); sleep(0.33)
        ctrl.stick_right("L", 8)
        return return_states(image, "WALKING1")
    
    elif image.state == "WALKING1":
        image.debugger.set_rois_for_state("WALKING1", [const.SWSH_STATES["egg"]["nursery_sign"]["rois"]], (0, 0, 0))
        walk_until_landmark_dpad(ctrl, image, dir=6, lm=landmark, stick_or_dpad= 1, hold_s= 0.17, pause_s= 0)
        return return_states(image, "CHECK_EGG")
    
    elif image.state == "CHECK_EGG":
        """
        This is to ask the lady and then check her text box to tell if its an egg or not.
        """
        image.debugger.set_rois_for_state("CHECK_EGG", [const.SWSH_STATES["text"]["text_box"]["rois"]], (0, 0, 0))
        image.debugger.set_rois_for_state("CHECK_EGG", const.SWSH_STATES["egg"]["nursery_lady"]["rois"], (0, 0, 0))
        ctrl.stick("L", 255, 0, 0.1); sleep(0.17)
        ctrl.tap(BTN_A, 0.05, 0.5); sleep(2)
        text = Text.string_from_roi(image, const.SWSH_STATES["text"]["text_box"]["rois"], key= "check_egg", psm=6)
        image.debugger.log("Nursery lady text:", text)
        if text and ("egg" in text.lower() and "found" in text.lower() and "holding" in text.lower()):
            image.debugger.log("Egg found!")
            image.database_component.eggs_collected += 1
            return return_states(image, "TALKING")
        else:
            image.debugger.log("No egg found, keep walking.")
            mash_b_while_textbox(ctrl, image, "SWSH", press_interval= 0.35, gone_confirm= 25, watch_state= "egg_acquired")
            return return_states(image, "WALKING")
        
    elif image.state == "TALKING":
        text = Text.string_from_roi(image, const.SWSH_STATES["text"]["text_box"]["rois"], key= "egg_talking", psm=6)
        if text and not ("welcome" in text.lower() and "help" in text.lower() and "nursery" in text.lower()):
            ctrl.tap(BTN_A, 0.05, 0.5)
        else:
            mash_b_while_textbox(ctrl, image, "SWSH", press_interval= 0.5, gone_confirm= 45, watch_state= "egg_acquired")
            if image.egg_count == image.cfg['inputs'][0]:
                return return_states(image, "PROGRAM_FINISHED")
            return return_states(image, "WALKING")
        return return_states(image, image.state)
        
    return image.state

def Egg_Hatcher_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, number: int) -> str:
    image.walking = 10
    image.walking_dir = 0
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_SWSH(image, ctrl, image.state))

    elif image.state == "IN_GAME":
        if not check_state(image, "SWSH", "screens", "menu_screen") and check_state(image, "SWSH", "text", "text_box"):
            ctrl.tap(BTN_B, 0.05, 0.33)
            return image.state
        elif not check_state(image, "SWSH", "screens", "menu_screen") and not check_state(image, "SWSH", "text", "text_box"):
            ctrl.tap(BTN_X, 0.05, 1)
            return image.state
        else:
            return return_states(image, "MENU")
        
    elif image.state == "MENU":
        menu = const.SWSH_STATES["menu"]

        all_rois = [
            roi
            for cfg in menu.values()
            if isinstance(cfg, dict) and "rois" in cfg
            for roi in cfg["rois"]
        ]
        image.debugger.set_rois_for_state("MENU", all_rois, (0, 0, 0))

        Menu_Navigation(ctrl, image, "pokemon")
        ctrl.tap(BTN_A); sleep(1.75)
        image.debugger.clear()
        return return_states(image, "PARTY_SCREEN")

    elif image.state == "PARTY_SCREEN":
        if check_state(image, "SWSH", "screens", "party_screen"):
            ctrl.tap(BTN_R)
            return return_states(image, "IN_BOX")
        
    elif image.state == "IN_BOX":
        if check_state(image, "SWSH", "screens", "box_screen"):
            ctrl.tap(BTN_Y, 0.05, 0.5)
            return return_states(image, "IN_BOX1")
        return image.state
        
    elif image.state == "IN_BOX1":
        sleep(0.17)
        image.debugger.log(image.box.cfg)
        if image.box.cfg:
            Pokemon_Boxes.put_pokemon(ctrl, image)
            return image.state
        return return_states(image, "IN_BOX2")

    elif image.state == "IN_BOX2":
        if image.egg_phase == 6:
            ctrl.tap(BTN_R)
            image.egg_phase = 0
        sleep(0.25)
        if image.database_component.eggs_hatched >= image.cfg['inputs'][0]:
            return return_states(image, "PROGRAM_FINISHED")
        return return_states(image, "IN_BOX3")
    
    elif image.state == "IN_BOX3":
        image.debugger.set_rois_for_state(image.state, [const.SWSH_STATES["box"]["grid"]["grid_roi"]], (0, 0, 0))
        end_of_box = (image.box.row == image.box.rows - 1 and
                    image.box.col == image.box.cols - 1)

        if len(image.box.cfg) < 5:
            kind, name = get_box_slot_kind(image, image.game)
            image.debugger.log(kind, name, image.box.row, image.box.col, image.box.cfg)

            if kind == "egg":
                Pokemon_Boxes.grab_pokemon(ctrl, image)
        if len(image.box.cfg) >= 5:
            return return_states(image, "IN_BOX4")

        if end_of_box:
            if len(image.box.cfg) == 0:
                Pokemon_Boxes.box_grid_final(ctrl, image, image.game, 0, 0, sleep_time= 0.5, verify=True)
                Pokemon_Boxes.next_box(ctrl, image)
                image.debugger.log(image.box.row, image.box.col)
                return image.state
            return return_states(image, "IN_BOX4")

        image.box.row, image.box.col = Pokemon_Boxes.box_grid_advance(
            ctrl, image.box.row, image.box.col, sleep_time=0.33
        )
        image.gate.wait_stable(image, roi= [891, 14, 389, 42] , timeout_s= 0.07)
        return image.state
    
    elif image.state == "IN_BOX4":
        image.box.col = image.box.row = 0
        if not check_state(image, "SWSH", "screens", "party_screen"):
            ctrl.tap(BTN_B)
            sleep(0.5)
            return image.state
        image.debugger.clear()
        return return_states(image, "TO_GAME")

    elif image.state == "TO_GAME":
        if not check_state(image, "SWSH", "screens", "menu_screen"):
            ctrl.tap(BTN_B)
            sleep(0.5)
            return image.state
        return return_states(image, "TO_GAME1")
    
    elif image.state == "TO_GAME1":
        if not check_state(image, "SWSH", "in_game", "in_game"):
            ctrl.tap(BTN_B)
            sleep(0.5)
            return image.state
        return return_states(image, "WALKING")

    elif image.state == "WALKING":
        while image.walking > 0:
            image.walking -= 1
            if check_state(image, "SWSH", "text", "dark_text_box"):
                return return_states(image, "TEXT")
            else:
                ctrl.stick_right("L", 1); sleep(0.17)
        image.walking = 10
        image.walking_dir = 1
        return return_states(image, "WALKING1")
    
    elif image.state == "WALKING1":
        while image.walking > 0:
            image.walking -= 1
            if check_state(image, "SWSH", "text", "dark_text_box"):
                return return_states(image, "TEXT")
            else:
                ctrl.stick_left("L", 1); sleep(0.17)
        image.walking = 10
        image.walking_dir = 0
        return return_states(image, "WALKING")
    
    elif image.state == "TEXT":
        ctrl.tap(BTN_A, 0.05, 0.5); sleep(2)
        return return_states(image, "HATCHING")
    
    elif image.state == "HATCHING":
        image.debugger.set_rois_for_state(image.state, const.SWSH_STATES["egg"]["hatching_text"]["rois"], (0, 0, 0))
        
        raw = Text.recognize_pokemon(image, const.SWSH_STATES["egg"]["hatching_text"]["rois"][0])
        raw = (raw or "").strip()
        image.debugger.log("Hatching text:", raw)
        if raw and image.generic_bool == False:
            image.database_component.pokemon_name = raw
            image.database_component.eggs_hatched += 1
            image.egg_count += 1
            image.generic_count += 1
            image.generic_bool = True
            sleep(1); ctrl.tap(BTN_A, 0.05, 0.5)
        
        if image.generic_bool == True:
            sleep(2.75)
            image.generic_bool = False
            if check_state(image, "SWSH", "in_game", "in_game"):
                if image.egg_count >= image.cfg['inputs'][0]:
                    return return_states(image, "PROGRAM_FINISHED")
                elif image.generic_count == len(image.box.cfg) and image.egg_count > 0:
                    image.generic_count = 0
                    return return_states(image, "IN_GAME")
                if image.walking_dir == 0:
                    return return_states(image, "WALKING")
                else:
                    return return_states(image, "WALKING1")

def Pokemon_Releaser_SWSH(image: Image_Processing, ctrl: Controller, state: str | None, number: int) -> str:
    image.box.box_amount = image.cfg["inputs"][0]
    image.game_pause_time = 0.25
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_SWSH(image, ctrl, image.state))
        
    elif image.state == "IN_GAME":
        if not check_state(image, "SWSH", "screens", "menu_screen"):
            ctrl.tap(BTN_X, 0.1, 1)
        else:
            return return_states(image, "MENU")
        
    elif image.state == "MENU":
        menu = const.SWSH_STATES["menu"]

        all_rois = [
            roi
            for cfg in menu.values()
            if isinstance(cfg, dict) and "rois" in cfg
            for roi in cfg["rois"]
        ]
        image.debugger.set_rois_for_state("MENU", all_rois, (0, 0, 0))

        Menu_Navigation(ctrl, image, "pokemon")
        ctrl.tap(BTN_A); sleep(1.75)
        image.debugger.clear()
        return return_states(image, "PARTY_SCREEN")

    elif image.state == "PARTY_SCREEN":
        if check_state(image, "SWSH", "screens", "party_screen"):
            ctrl.tap(BTN_R)
            return return_states(image, "LOADING_BOXES")

    elif image.state == "LOADING_BOXES":
        if check_state(image, "SWSH", "screens", "box_screen"):
            return return_states(image, "IN_BOX")
        return image.state

    elif image.state in ("IN_BOX", "GO_THROUGH_BOX", "NEXT_BOX"):
        image.debugger.set_rois_for_state(image.state, [const.SWSH_STATES["box"]["grid"]["grid_roi"]], (0, 0, 0))
        return release_pokemon(ctrl, image)

    return image.state