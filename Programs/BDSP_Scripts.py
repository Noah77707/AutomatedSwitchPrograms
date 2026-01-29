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
        image.state = "PAIRING"

    elif image.state in ("PAIRING"):
        image.state = home_screen_checker_macro(ctrl, image, image.state)
    
    elif image.state in ("HOME_SCREEN", "START_SCREEN"):
        image.state = bdsp_start_screens_macro(ctrl, image, image.state)

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
        boxes = int(image.run)
    except (TypeError, ValueError):
        boxes = 0

    amount = boxes * 30

    # Start of the state program
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        image.state = Start_BDSP(image, ctrl, image.state)
        return image.state
            
    elif image.state == "PROGRAM":
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(2)
            if not check_state(image, "BDSP", "in_game", "poketch"):
                ctrl.tap(BTN_R, 0.05, 0.5)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            image.state = "IN_BOX"
    
    elif image.state == "IN_BOX":
        if check_state(image, "BDSP", "screens", "box_screen"):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            ctrl.tap(BTN_Y, 0.1, 0.1)
            if image.generic_bool == False:
                image.state = "IN_BOX1"
            else:
                image.state = "IN_BOX2"

    # puts the extra pokemon in the party so eggs dont enter the party and lock the program up
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
        image.state = "IN_BOX3"
    # end function, puts the extra pokemon away befor going on to the egg hatcher program.
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
        image.state = "IN_BOX3"

    elif image.state == "IN_BOX3":
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_B)
        else:
            image.state = "IN_GAME"
    # sees that its ingame, starts the egg collecting program
    elif image.state == "IN_GAME":
        if not hasattr(image, "egg_count"):
            image.egg_count = 0
        if not hasattr(image, "egg_phase"):
            image.egg_phase = 0
        # if this is true, then it will first put the pokemon away, and then it will finish up the collector
        if int(image.egg_count) >= int(amount):
            if image.generic_bool == True:
                image.state = "PROGRAM"
                return image.state
            else:
                image.egg_count = 0
                image.egg_phase = 0
                image.state = "COLLECTOR_FINISHED"
                return image.state
        else:
            image.state = "CHECK_EGG"
    # Uses template matching to see if the daycare man is facing towards the left, which means he has an egg
    elif image.state == "CHECK_EGG":
        sleep(1.5)
        debugRois = [
            roi,
            const.BDSP_STATES['text']['text_box']['roi']
        ]
        image.debugger.set_rois_for_state("CHECK_EGG", debugRois, (0, 0, 0))
        ctrl.down(BTN_B)
        
        vmax1 = is_in_area(image, "Media/BDSP_Images/Egg_Man_Arms.png", roi = roi, threshold= 0.65)
        vmax2 = is_in_area(image, "Media/BDSP_Images/Egg_Man_Arms2.png", roi = roi, threshold= 0.65)
        if vmax1 > 0.67 or vmax2 > 0.67 and image.egg_phase == 0:
            for _ in range(4):
                ctrl.dpad(6, 0.14); sleep(0.17)
            sleep(0.2)
            ctrl.tap(BTN_A)
            # mashes the text box until the egg screen appears. if it does, then it increments the egg counter
            saw_egg = mash_a_while_textbox(ctrl, image, "BDSP", press_interval= 0.35, gone_confirm= 15, watch_state= "egg_acquired")
            if saw_egg:
                image.egg_count += 1
                image.database_component.eggs_collected += 1
            # this will walk until the daycare sign is in a certian area, which means you are able to run up and down.
            # importantly, it will always return to walking instead of check egg
            # this is due to the daycare man facing left until he is off screen
            # if it returned to the egg checking state, it would be an infinite loop
            ctrl.up(BTN_B)
            walk_until_landmark_dpad(ctrl, image, dpad_dir= 2, lm= landmark, pause_s= 0.4)
            ctrl.down(BTN_B)

        image.state = "WALKING"
    # walks up for a random amount of spaces. Due to the controller being able to drop input or hold them longer than intended, its not that reliable
    elif image.state == "WALKING":
        image.debugger.clear()
        image.debugger.set_rois_for_state("WALKING", [(240, 160, 180, 180)], (0, 0, 0))
        ctrl.down(BTN_B)
        for _ in range(15):
            ctrl.dpad(0, 0.13)
        image.egg_phase = 1
        image.state = "WALKING1" 
    # walks down. uses template matching to see if the daycare sign is in the correct place to position the character correctly.
    elif image.state == "WALKING1":
        image.debugger.set_rois_for_state("WALKING1", [(240, 160, 180, 180)], (0, 0, 0))
        walk_until_landmark_dpad(ctrl, image, dpad_dir= 4, lm= landmark)
        image.egg_phase = 0
        ctrl.up(BTN_B)
        image.state = "IN_GAME"
        return image.state
    
    return image.state

def Egg_Hatcher_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    # debug info and information that is best called once
    if not hasattr(image, "daycare_tpl"):
        image.daycare_tpl = cv.imread("Media/BDSP_Images/Day_Care_Sign.png", cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl

    if not hasattr(image, "hatched_tpl"):
        image.hatched_tpl = cv.imread("Media/BDSP_Images/Hatched.png", cv.IMREAD_GRAYSCALE)
    hatched = image.hatched_tpl
    landmark = TemplateLandmark(
        template_gray= tpl,
        roi= (200, 120, 200, 200),
        threshold= 0.65,
        hits_required= 3
    )
    image.debugger.clear()
    image.debugger.set_rois_for_state((200, 120, 200, 200), (0, 0, 255))
    image.debugger.set_rois_for_state(const.BDSP_STATES["text"]["text_box"]["roi"], (255, 0, 0))
    count = image.run * 30

    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        image.state = Start_BDSP(image, ctrl, image.state)
    
    elif image.state == "IN_GAME" or image.state == "PROGRAM":
        if not check_state(image, "GENERIC", "black_screen"):
            sleep(2)
            if not check_state(image, "BDSP", "in_game", "poketch"):
                ctrl.tap(BTN_R, 0.05, 0.5)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            image.state = "IN_BOX"
    
    elif image.state == "IN_BOX":
        if check_state(image, "BDSP", "screens", "box_screen"):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            ctrl.tap(BTN_Y, 0.1, 0.1)
            image.state = "IN_BOX1"
        
    elif image.state == "IN_BOX1":
        sleep(0.17)
        if not image.generic_count == 0:
            put_egg(ctrl, image, "BDSP")
        image.generic_count = 0
        image.state = "IN_BOX2"
    
    elif image.state == "IN_BOX2":
        if image.egg_phase == 6:
            ctrl.tap(BTN_R)
            image.egg_phase = 0
        sleep(0.25)
        image.state = "IN_BOX3"
    
    elif image.state == "IN_BOX3":
        grab_egg(ctrl, image, "BDSP")
        image.egg_phase += 1
        sleep(0.75)
        image.state = "IN_BOX4"
    
    elif image.state == "IN_BOX4":
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_B)
            return image.state
        image.state = "WALKING1"
    
    elif image.state == "WALKING":
        ctrl.down(BTN_B)
        for _ in range(20):
            if check_state(image, "BDSP", "text", "text_box"):
                image.state = "HATCHING"
                return image.state
            else:
                ctrl.dpad(4, 0.13)
        image.state = "WALKING1"
    
    elif image.state == "WALKING1":
        ctrl.down(BTN_B)
        if check_state(image, "BDSP", "text", "text_box"):
            image.state = "HATCHING"
            return image.state
        back_to_start = walk_until_landmark_dpad(ctrl, image, landmark, dpad_dir=0, max_steps=1)
        if back_to_start:
            image.state = "WALKING"
        
    elif image.state == "HATCHING":
        if not hasattr(image, "generic_bool"):
            image.generic_bool = False
        if not hasattr(image, "egg_count"):
            image.egg_count = 0
        
        hit = False
        score = 1.0
        # looks for the text "hatched from the egg!" to increment the hatched egg
        
        if check_state(image, "BDSP", "text", "text_box"):          
            hit, score = match_text_fragment(image, hatched, const.BDSP_STATES["text"]["text_box"]["roi"], sqdiff_max= 0.2)
            image.debugger.log("sqdiff:", score)
            sleep(0.02); ctrl.tap(BTN_A)

        if hit and not image.generic_bool:
            image.debugger.log("hit")
            
            # commented oout code below will be changed to a name collector.
            
            # image.debugger.set_rois_for_state("GET_NAME", const.SWSH_STATES["text"]["sent_to_box"]["rois"], (0, 0, 0))
            # raw = Text.recognize_text(image, const.SWSH_STATES["text"]["sent_to_box"]["rois"][0])
            # raw = (raw or "").strip()

            image.database_component.eggs_hatched += 1
            image.egg_count += 1
            image.generic_count += 1
            image.generic_bool = True

        if not hit:
            image.generic_bool = False
        # this checks if it has hatched all the eggs in the party by seeing if the poketch comes onscreen.
        # The poketch only comes on screen when control is returned to the player
        if check_state(image, "BDSP", "in_game", "poketch"):
            if image.egg_count == count:
                image.state = "HATCHING_FINISHED"
                return image.state
            elif image.generic_count != 0 and image.generic_count == 5:
                image.generic_bool = False
                image.state = "IN_GAME"
                return image.state
            image.state = "WALKING1"

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
    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN"):
        image.state = Start_BDSP(image, ctrl, image.state)
    
    elif image.state == "IN_GAME" or image.state == "PROGRAM":
        if not check_state(image, "BDSP", "in_game", "poketch"):
            ctrl.tap(BTN_R)
        else:
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            image.state = "IN_BOX_SCREEN"
        
    elif image.state == "IN_BOX_SCREEN":
        if check_state(image, "BDSP", "screens", "box_screen"):
            return return_states(image, "IN_BOX")
 
    elif image.state in ("IN_BOX", "GO_THROUGH_BOX", "NEXT_BOX"):
        return release_pokemon(ctrl, image)
           
    return image.state