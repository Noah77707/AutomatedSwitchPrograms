import os
import sys
import serial
import numpy as np
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.States import *
from Modules.Dataclasses import *
from Modules.Image_Processing import *

def Start_BDSP(image: Image_Processing, ctrl: Controller, state: str | None):
    ensure_stats(image)
    if state is None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        return home_screen_checker_macro(ctrl, image)
    
    elif state in ('HOME_SCREEN', 'START_SCREEN'):
        return bdsp_start_screens_macro(ctrl, image, state)
    
    return return_state(image, state)

def Static_Encounter_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    return None

def Egg_Collector_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    # Debug material. this lets the user see the debug information and variables that will be used later on.
    roi = const.BDSP_CONSTANTS['nursery_man']
    if not hasattr(image, 'daycare_tpl'):
        image.daycare_tpl = cv.imread('Media/BDSP_Images/Day_Care_Sign.png', cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl
    landmark = TemplateLandmark(
        template_gray= tpl,
        roi= (240, 160, 180, 180),
        threshold= 0.65,
        hits_required= 3
    )

    if not hasattr(image, "debug_rois_collector"):
        image.add_debug_roi(const.BDSP_CONSTANTS["nursery_man"], (0,255,0))
        image.add_debug_roi((240,160,180,180), (0,0,255))
        image.debug_rois_collector = True

    amount = input * 30
    # Start of the state program
    if state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        state = Start_BDSP(image, ctrl, state)
            
    elif state == 'PROGRAM':
        if not check_state(image, 'GENERIC', 'black_screen'):
            sleep(2)
            if not check_state(image, 'BDSP', 'poketch'):
                ctrl.tap(BTN_R, 0.05, 0.5)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
    
    elif state == 'IN_BOX':
        if check_state(image, 'BDSP', 'box_open'):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            ctrl.tap(BTN_Y, 0.1, 0.1)
            if image.generic_bool == False:
                return 'IN_BOX1'
            else:
                return 'IN_BOX2'
    # puts the extra pokemon in the party so eggs dont enter the party and lock the program up
    elif state == 'IN_BOX1':
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
        return 'IN_BOX3'
    # end function, puts the extra pokemon away befor going on to the egg hatcher program.
    elif state == 'IN_BOX2':
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
        return 'IN_BOX3'

    elif state == 'IN_BOX3':
        if not check_state(image, 'BDSP', 'poketch'):
            ctrl.tap(BTN_B)
        else:
            return 'IN_GAME'
    

    # sees that its ingame, starts the egg collecting program
    elif state == 'IN_GAME':
        if not hasattr(image, 'egg_count'):
            image.egg_count = 0
        if not hasattr(image, 'egg_phase'):
            image.egg_phase = 0
        # if this is true, then it will first put the pokemon away, and then it will finish up the collector
        if int(image.egg_count) >= int(amount):
            if image.generic_bool == True:
                return 'PROGRAM'
            else:
                image.egg_count = 0
                image.egg_phase = 0
                return 'COLLECTOR_FINISHED'
        else:
            return 'CHECK_EGG'
    # Uses template matching to see if the daycare man is facing towards the left, which means he has an egg
    elif state == 'CHECK_EGG':
        sleep(1.5)

        ctrl.down(BTN_B)
        if is_in_area(image, 'Media/BDSP_Images/Egg_Man_Arms.png', roi = roi, threshold= 0.65) > 0.67 and image.egg_phase == 0:
            for _ in range(4):
                ctrl.dpad(6, 0.14)
            sleep(0.2)
            ctrl.tap(BTN_A)
            # mashes the text box until the egg screen appears. if it does, then it increments the egg counter
            saw_egg = mash_a_while_textbox(ctrl, image, 'BDSP', press_interval= 0.35, gone_confirm= 15, watch_state= 'egg_acquired')
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

        return 'WALKING'
    
    # walks up for a random amount of spaces. Due to the controller being able to drop input or hold them longer than intended, its not that reliable
    elif state == 'WALKING':
        ctrl.down(BTN_B)
        for _ in range(15):
            ctrl.dpad(0, 0.13)
        image.egg_phase = 1
        return 'WALKING1'
    
    # walks down. uses template matching to see if the daycare sign is in the correct place to position the character correctly.
    elif state == 'WALKING1':
        walk_until_landmark_dpad(ctrl, image, dpad_dir= 4, lm= landmark)
        image.egg_phase = 0
        ctrl.up(BTN_B)
        return 'IN_GAME'
    return state

def Egg_Hatcher_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    # debug info and information that is best called once
    if not hasattr(image, 'daycare_tpl'):
        image.daycare_tpl = cv.imread('Media/BDSP_Images/Day_Care_Sign.png', cv.IMREAD_GRAYSCALE)
    tpl = image.daycare_tpl

    if not hasattr(image, 'hatched_tpl'):
        image.hatched_tpl = cv.imread('Media/BDSP_Images/Hatched.png', cv.IMREAD_GRAYSCALE)
    hatched = image.hatched_tpl
    landmark = TemplateLandmark(
        template_gray= tpl,
        roi= (200, 120, 200, 200),
        threshold= 0.65,
        hits_required= 3
    )
    image.clear_debug()
    image.add_debug_roi((200, 120, 200, 200), (0, 0, 255))
    image.add_debug_roi(const.BDSP_CONSTANTS['text_box_roi'], (255, 0, 0))
    count = input * 30
    # Start of the state program
    if state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        state = Start_BDSP(image, ctrl, state)
    
    # sees that its ingame, and then will open up the boxes
    elif state == 'IN_GAME' or state == 'PROGRAM':
        if not check_state(image, 'GENERIC', 'black_screen'):
            sleep(2)
            if not check_state(image, 'BDSP', 'poketch'):
                ctrl.tap(BTN_R, 0.05, 0.5)
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
    
    elif state == 'IN_BOX':
        if check_state(image, 'BDSP', 'box_open'):
            ctrl.tap(BTN_Y, 0.1, 0.1)
            ctrl.tap(BTN_Y, 0.1, 0.1)
            return 'IN_BOX1'
    # the generic count counts if you already hatched eggs. if zero, it doesnt have any party pokemon to put in the box
    # if its not zero, it will return the hatched eggs to their correct spot
    elif state == 'IN_BOX1':
        sleep(0.17)
        if not image.generic_count == 0:
            put_egg(ctrl, image, 'BDSP')
        image.generic_count = 0
        return 'IN_BOX2'
    # changes to the next box if all eggs have been hatched
    elif state == 'IN_BOX2':
        if image.egg_phase == 6:
            ctrl.tap(BTN_R)
            image.egg_phase = 0
        sleep(0.25)
        return 'IN_BOX3'
    # grabs the eggs, then increments the counter for how many egg columns have been grabbed
    elif state == 'IN_BOX3':
        grab_egg(ctrl, image, 'BDSP')
        image.egg_phase += 1
        sleep(0.75)
        return 'IN_BOX4'
    # returns to overworld
    elif state == 'IN_BOX4':
        if not check_state(image, 'BDSP', 'poketch'):
            ctrl.tap(BTN_B)
            return 'IN_BOX4'
        return 'WALKING'
    # Walks down, and checks to see if there is a textbox for if the egg is hatching
    elif state == 'WALKING':
        ctrl.down(BTN_B)
        for _ in range(20):
            if check_state(image, 'BDSP', 'text_box'):
                return 'HATCHING'
            else:
                ctrl.dpad(4, 0.13)
        return 'WALKING1'
    # Walks up to a specific landmark, and checks to see if there is a textbox for if the egg is hatching
    elif state == 'WALKING1':
        if check_state(image, 'BDSP', 'text_box'):
            return 'HATCHING'
        back_to_start = walk_until_landmark_dpad(ctrl, image, landmark, dpad_dir=0, max_steps=1)
        if back_to_start:
            return 'WALKING'
    # if the textbox pops up, it starts the egg hatching state
    elif state == 'HATCHING':
        if not hasattr(image, 'generic_bool'):
            image.generic_bool = False
        if not hasattr(image, 'egg_count'):
            image.egg_count = 0
        
        hit = False
        score = 1.0
        # looks for the text 'hatched from the egg!' to increment the hatched egg
        if check_state(image, 'BDSP', 'text_box'):
            hit, score = match_text_fragment(image, hatched, const.BDSP_CONSTANTS['text_box_roi'], sqdiff_max= 0.2)
            print('sqdiff:', score)
            sleep(0.02); ctrl.tap(BTN_A)

        if hit and not image.generic_bool:
            print('hit')
            image.database_component.eggs_hatched += 1
            image.egg_count += 1
            image.generic_count += 1
            image.generic_bool = True

        if not hit:
            image.generic_bool = False
        # thisd checks if it has hatched all the eggs in the party
        if check_state(image, 'BDSP', 'poketch'):
            if image.egg_count == count or image.shiny >= 1:
                return 'HATCHING_FINISHED'
            elif image.generic_count != 0 and image.generic_count == 5:
                image.generic_bool = False
                return 'IN_GAME'
            return 'WALKING1'
            
    return return_state(image, state)

def Automated_Egg_BDSP(image: Image_Processing, ctrl: Controller, phase: str | None, input: int) -> str:
    phase, sub = split_state(image.generic_state)

    if phase is None:
        phase, sub = 'PAIRING', None

    elif phase == 'PAIRING':
        sub = Start_BDSP(image, ctrl, sub)
        if sub == 'IN_GAME':
            phase, sub = 'COLLECT', 'PROGRAM'
    
    elif phase == 'COLLECT':
        sub = Egg_Collector_BDSP(image, ctrl, sub, input)
        if sub == 'COLLECTOR_FINISHED':
            phase, sub = 'HATCH', 'PROGRAM'

    elif phase == 'HATCH':
        sub = Egg_Hatcher_BDSP(image, ctrl, sub, input)
        if sub == 'HATCHING_FINISHED':
            phase, sub = 'RELEASE', 'PROGRAM'
    
    elif phase == 'HATCHING_FINISHED':
        sub = Pokemon_Releaser_BDSP(image, ctrl, sub, input)
        if sub == 'RELEASER_FINISHED':
            phase, sub = 'FINISHED', 'PROGRAM'

    return_state(image, sub)
    image.generic_state = join_state(phase, sub)
    return image.generic_state

def Pokemon_Releaser_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    if state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        state = Start_BDSP(image, ctrl, state)
    
    elif state == 'IN_GAME' or state == 'PROGRAM':
        if not check_state(image, 'BDSP', 'poketch'):
            ctrl.tap(BTN_R)
        else:
            ctrl.tap(BTN_X, 0.05, 0.45)
            ctrl.tap(BTN_A, 0.05, 1.2)
            ctrl.tap(BTN_R, 0.05, 1.2)
            return 'IN_BOX'
        
    elif state == 'IN_BOX':
        if check_state(image, 'BDSP', 'box_open'):
            release_pokemon(ctrl, image, 'BDSP', input)
            state = "PROGRAM_FINISHED"
            
    return return_state(image, state)