import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *
from Modules.Dataclasses import *
from Modules.Image_Processing import *
from Modules.Database import *

def Start_BDSP(image: Image_Processing, ctrl: Controller, state: str | None):
    if image.state is None:
        return return_states(image, "PAIRING")

    elif image.state  == "PAIRING":
        return return_states(image, home_screen_checker_macro(ctrl, image, image.state))
    
    elif image.state in ("HOME_SCREEN", "START_SCREEN"):
        return return_states(image, bdsp_start_screens_macro(ctrl, image, image.state))

    return image.state

def Menu_Navigation(ctrl: Controller, image: Image_Processing, target: str) -> None:
    def get_menu_cursor_index(image: Image_Processing, game: str = "BDSP") -> int | None:
        menu = const.GAME_STATES[game]["menu"]
        for name, cfg in menu.items():
            if check_state(image, game, "menu", name):
                return int(cfg["index"])
        return None

    menu = const.BDSP_STATES["menu"]
    
    target_position = menu[target]["index"]
    cur = get_menu_cursor_index(image, "BDSP")
    image.debugger.log("menu cursor:", cur, "target:", target_position)

    if cur is None:
        return
    
    def row(i: int) -> int: return 0 if i < 4 else 1
    def col(i: int) -> int: return i % 4

    if row(cur) != row(target_position):
        ctrl.dpad(0 if row(cur) < row(target_position) else 4, 0.05)
        sleep(0.12)
        cur = get_menu_cursor_index(image, "BDSP")
        if cur is None:
            return
        
    while col(cur) != col(target_position):
        if col(cur) < col(target_position):
            ctrl.dpad(2, 0.05)
        else:
            ctrl.dpad(6, 0.05)
        sleep(0.4)
        nxt = get_menu_cursor_index(image, "BDSP")
        if nxt is None:
            return
        cur = nxt

def Static_Encounter_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    return None

def Egg_Collector_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    # Debug material. this lets the user see the debug information and variables that will be used later on.
    roi = const.BDSP_STATES["Egg"]["nursery_man"]
    if not hasattr(image, "daycare_tpl"):
        image.daycare_tpl = cv.imread("Media/BDSP_Images/Day_Care_Sign.png", cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl
    landmark = TemplateLandmark(
        template_gray= tpl,
        roi= (240, 160, 180, 180),
        threshold= 0.65,
        hits_required= 3
    )


    try:
        boxes = int(image.cfg['inputs'][0])
    except (TypeError, ValueError):
        boxes = 0
    
    amount = boxes

    # Start of the state program
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_BDSP(image, ctrl, image.state))

    elif image.state == "PROGRAM":
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(2)
            if not check_state(image, "BDSP", "in_game", "poketch"):
                ctrl.tap(BTN_R, 0.05, 0.5)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return return_states(image, "IN_BOX")
    
    elif image.state == "IN_BOX":
        if check_state(image, "BDSP", "screens", "box_screen"):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            ctrl.tap(BTN_Y, 0.1, 0.1)
            if image.generic_bool == False:
                return return_states(image, "IN_BOX1")
            else:
                return return_states(image, "IN_BOX2")

    elif image.state == "IN_BOX1":
        ctrl.tap(BTN_L, 0.05, 1)
        ctrl.tap(BTN_A)
        for _ in range(5):
            sleep(0.17)
            ctrl.dpad(4, 0.2)
        sleep(0.17)
        ctrl.tap(BTN_A)
        ctrl.dpad(6, 0.05); sleep(0.17)
        ctrl.dpad(4, 0.05); sleep(0.17)
        ctrl.tap(BTN_A, 0.05, 0.45)
        ctrl.tap(BTN_R)
        image.generic_bool = True
        return return_states(image, "IN_BOX3")

    elif image.state == "IN_BOX2":
        ctrl.tap(BTN_L, 0.05, 1)
        ctrl.dpad(6, 0.05); sleep(0.17)
        ctrl.dpad(4, 0.05); sleep(0.17)
        ctrl.tap(BTN_A)
        for _ in range(5):
            sleep(0.17)
            ctrl.dpad(4, 0.2)
        sleep(0.17)
        ctrl.tap(BTN_A)
        ctrl.dpad(0, 0.05); sleep(0.17)
        ctrl.dpad(2, 0.05); sleep(0.17)
        ctrl.tap(BTN_A)
        ctrl.tap(BTN_R, 0.05, 1)
        image.generic_bool = False
        return return_states(image, "IN_BOX3")

    elif image.state == "IN_BOX3":
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_B)
        else:
            return return_states(image, "IN_GAME")
        
    elif image.state == "IN_GAME":
        image.debugger.clear()
        if not hasattr(image, "egg_count"):
            image.egg_count = 0
        if not hasattr(image, "egg_phase"):
            image.egg_phase = 0
        # if this is true, then it will first put the pokemon away, and then it will finish up the collector
        if int(image.egg_count) >= int(amount):
            if image.generic_bool == True:
                return return_states(image, "PROGRAM_FINISHED")
            else:
                image.egg_count = 0
                image.egg_phase = 0
                return return_states(image, "COLLECTOR_FINISHED")
        else:
            return return_states(image, "CHECK_EGG")

    elif image.state == "CHECK_EGG":
        image.debugger.clear()
        image.debugger.set_rois_for_state("CHECK_EGG", [const.BDSP_STATES["Egg"]["nursery_man"]], (0, 0, 0))
        sleep(1.5)
        ctrl.down(BTN_B)
        
        vmax1 = is_in_area(image, "Media/BDSP_Images/Egg_Man_Arms.png", roi = roi, threshold= 0.65)
        vmax2 = is_in_area(image, "Media/BDSP_Images/Egg_Man_Arms2.png", roi = roi, threshold= 0.65)
        if vmax1 > 0.67 or vmax2 > 0.67 and image.egg_phase == 0:
            for _ in range(4):
                ctrl.stick_left("L", 0.17); sleep(0.17)
            sleep(0.2)
            ctrl.tap(BTN_A)
            text = Text.string_from_roi(image, const.BDSP_STATES['text']['text_box']['rois'][0], key= "get_egg", psm=6)
            image.debugger.log(text)
            if text.find("care") != -1:
                image.egg_count += 1
                image.database_component.eggs_collected += 1
            mash_a_while_textbox(ctrl, image, "BDSP", press_interval= 0.35, gone_confirm= 15, watch_state= "egg_acquired")

            ctrl.up(BTN_B)
            walk_until_landmark_dpad(ctrl, image, dpad_dir= 2, lm= landmark, pause_s= 0.4)
            ctrl.down(BTN_B)

        return return_states(image, "WALKING")

    elif image.state == "WALKING":
        image.debugger.set_rois_for_state("WALKING", [(240, 160, 180, 180)], (0, 0, 0))
        ctrl.down(BTN_B)
        for _ in range(15):
            ctrl.dpad(0, 0.13)
        image.egg_phase = 1
        return return_states(image, "WALKING1")

    elif image.state == "WALKING1":
        image.debugger.set_rois_for_state("WALKING1", [(240, 160, 180, 180)], (0, 0, 0))
        walk_until_landmark_dpad(ctrl, image, dpad_dir= 4, lm= landmark)
        image.egg_phase = 0
        ctrl.up(BTN_B)
        return return_states(image, "IN_GAME")
    
    return image.state

def Egg_Hatcher_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    # debug info and information that is best called once
    if not hasattr(image, "daycare_tpl"):
        image.daycare_tpl = cv.imread("Media/BDSP_Images/Day_Care_Sign.png", cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl
    landmark = TemplateLandmark(
        template_gray= tpl,
        roi= (200, 120, 200, 200),
        threshold= 0.65,
        hits_required= 3
    )
    if not hasattr(image, "bike"):
        image.bike = cv.imread("Media/BDSP_Images/Bicycle.png", cv.IMREAD_GRAYSCALE)
        image.bike_riding = False
    image.debugger.clear()
    count = image.cfg['inputs'][0]

    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        return return_states(image, Start_BDSP(image, ctrl, image.state))
    
    elif image.state in ("IN_GAME", "PROGRAM"):
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(2)
            if not check_state(image, "BDSP", "in_game", "poketch"):
                ctrl.tap(BTN_R, 0.05, 0.5)
            else:
                return return_states(image, "TO_MENU")
    
    elif image.state == "TO_MENU":
        if not check_state(image, "BDSP", "screens", "menu_screen"):
            ctrl.tap(BTN_X, 0.05, 1)
        else:
            return return_states(image, "MENU")
        
    elif image.state == "MENU":
        menu = const.BDSP_STATES["menu"]

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
        if check_state(image, "BDSP", "screens", "party_screen"):
            ctrl.tap(BTN_R, 0.05, 1.5)
        else:
            return return_states(image, "IN_BOX")

    elif image.state == "IN_BOX":
        if check_state(image, "BDSP", "screens", "box_screen"):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            return return_states(image, "IN_BOX1")
        
    elif image.state == "IN_BOX1":
        sleep(0.17)
        image.debugger.log(image.box.cfg)
        if image.box.cfg:
            put_pokemon(ctrl, image)
            return image.state
        return return_states(image, "IN_BOX2")
    
    elif image.state == "IN_BOX2":
        if image.egg_phase == 6:
            ctrl.tap(BTN_R)
            image.egg_phase = 0
        sleep(0.25)
        if image.database_component.eggs_hatched == image.cfg['inputs'][0]:
            return return_states(image, "PROGRAM_FINISHED")
        return return_states(image, "IN_BOX3")
    
    elif image.state == "IN_BOX3":
        kind, name = get_box_slot_kind(image, image.game)
        image.debugger.log(kind, name)
        if kind == "egg":
            grab_pokemon(ctrl, image)
            image.debugger.log(image.box.cfg)
        if len(image.box.cfg) != 5:
            if not (image.box.current_row == image.box.rows - 1 and image.box.current_col == image.box.cols - 1):
                image.box.current_row, image.box.current_col = box_grid_advance(
                    ctrl, image.box.current_row, image.box.current_col, sleep_time=0.33
                )
            else:
                image.box.current_col = image.box.current_row = 0
                next_box(ctrl); sleep(1)
            image.debugger.log(image.box.current_row, image.box.current_col)
            return image.state
        return return_states(image, "IN_BOX4")
    
    elif image.state == "IN_BOX4":
        image.box.current_col = image.box.current_row = 0
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_B)
            return image.state
        return return_states(image, "WALKING")
    
    # elif image.state == "CHECK_BIKE":
    #     if not image.bike_riding == True:
    #         ctrl.tap(BTN_PLUS, 0.05, 1)
    #         statement, index = match_any_slot(image.original_image, const.BDSP_STATES['quick_select'], image.bike)
    #         if statement:
    #             image.bike_riding = True
    #             match index:
    #                 case 1:
    #                     ctrl.stick_up("L", 0.13)
    #                 case 2:
    #                     ctrl.stick_right("L", 0.13)
    #                 case 3:
    #                     ctrl.stick_down("L", 0.13)
    #                 case 4:
    #                     ctrl.stick_left("L", 0.13)    
    #         image.debugger.log(statement)
    #     else:
    #         return return_states(image, "WALKING")

    elif image.state == "WALKING":
        ctrl.down(BTN_B)
        for _ in range(20):
            if check_state(image, "BDSP", "text", "text_box"):
                return return_states(image, "TEXT")
            else:
                ctrl.dpad(4, 0.13)
        return return_states(image, "WALKING1")
    
    elif image.state == "WALKING1":
        image.debugger.set_rois_for_state(image.state, [(200, 120, 200, 200)], (0, 0, 255))
        ctrl.down(BTN_B)
        if check_state(image, "BDSP", "text", "text_box"):
                return return_states(image, "TEXT")
        back_to_start = walk_until_landmark_dpad(ctrl, image, landmark, dpad_dir=0, max_steps=1)
        if back_to_start:
            return return_states(image, "WALKING")
        
    elif image.state == "TEXT":
        mash_a_while_textbox(ctrl, image, image.game)
        wait_state(image, image.game, True, 0.2, "text", "text_box")
        return return_states(image, "HATCHING")
        
    elif image.state == "HATCHING":
        image.debugger.set_rois_for_state("HATCHING", const.BDSP_STATES["text"]["text_box"]["rois"], (255, 0, 0))
            
        if check_state(image, "BDSP", "text", "text_box"):
            raw = Text.recognize_pokemon(image, const.BDSP_STATES["text"]["text_box"]["rois"][0])
            raw = (raw or "").strip()
            if raw:
                image.generic_bool = True
                image.database_component.pokemon_name = raw
                image.database_component.eggs_hatched += 1
                image.egg_count += 1
                image.generic_count += 1
                sleep(1); ctrl.tap(BTN_A, 0.05, 5)
                
        if image.generic_bool == True:
            image.generic_bool = False
            if check_state(image, "BDSP", "in_game", "poketch"):
                if image.egg_count == count:
                    return return_states(image, "HATCHING_FINISHED")
                elif image.generic_count == 5 and image.egg_count > 0:
                    image.generic_count = 0
                    return return_states(image, "IN_GAME")
                return return_states(image, "WALKING1")
            if check_state(image, "BDSP", "text", "text_box"):
                return return_states(image, "TEXT")  
    
    return image.state

def Automated_Egg_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    state, sub = split_state(image.generic_state)

    if state is None:
        state, sub = "PAIRING", None

    elif state == "PAIRING":
        sub = Start_BDSP(image, ctrl, sub)
        if sub == "IN_GAME":
            state, sub = "COLLECT", "PROGRAM"
    
    elif state == "COLLECT":
        sub = Egg_Collector_BDSP(image, ctrl, sub)
        if sub == "COLLECTOR_FINISHED":
            state, sub = "HATCH", "PROGRAM"

    elif state == "HATCH":
        sub = Egg_Hatcher_BDSP(image, ctrl, sub)
        if sub == "HATCHING_FINISHED":
            state, sub = "RELEASE", "PROGRAM"
    
    elif state == "RELEASE":
        sub = Pokemon_Releaser_BDSP(image, ctrl, sub)
        if sub == "RELEASER_FINISHED":
            state, sub = "FINISHED", "PROGRAM"

    image.state = state
    image.generic_state = join_state(state, sub)
    return state

def Pokemon_Releaser_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    image.box.box_amount = image.cfg["inputs"][0]

    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        image.state = Start_BDSP(image, ctrl, image.state)
    
    elif image.state == "IN_GAME" or image.state == "PROGRAM":
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_R)
        else:
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return_states(image, "IN_BOX_SCREEN")
        
    elif image.state == "IN_BOX_SCREEN":
        if check_state(image, "BDSP", "screens", "box_screen"):
            return return_states(image, "IN_BOX")
 
    elif image.state in ("IN_BOX", "GO_THROUGH_BOX", "NEXT_BOX"):
        return release_pokemon(ctrl, image)
           
    return image.state
