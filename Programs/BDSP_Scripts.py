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
    if state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        state = Start_BDSP
            
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
    
    elif state == 'IN_GAME':
        if not hasattr(image, 'egg_count'):
            image.egg_count = 0
        if not hasattr(image, 'egg_phase'):
            image.egg_phase = 0

        if int(image.egg_count) >= int(amount):
            if image.generic_bool == True:
                return 'PROGRAM'
            else:
                image.egg_count = 0
                image.egg_phase = 0
                return 'COLLECTOR_FINISHED'
        else:
            return 'CHECK_EGG'

    elif state == 'CHECK_EGG':
        sleep(1.5)

        ctrl.down(BTN_B)
        if is_in_area(image, 'Media/BDSP_Images/Egg_Man_Arms.png', roi = roi, threshold= 0.65) > 0.67 and image.egg_phase == 0:
            for _ in range(4):
                ctrl.dpad(6, 0.14)
            sleep(0.2)
            ctrl.tap(BTN_A)
            
            saw_egg = mash_a_while_textbox(ctrl, image, 'BDSP', press_interval= 0.35, gone_confirm= 15, watch_state= 'egg_acquired')
            if saw_egg:
                image.egg_count += 1
                image.database_component.eggs_collected += 1

            ctrl.up(BTN_B)
            walk_until_landmark_dpad(ctrl, image, dpad_dir= 2, lm= landmark, pause_s= 0.4)
            ctrl.down(BTN_B)

        return 'WALKING'
    
    elif state == 'WALKING':
        ctrl.down(BTN_B)
        for _ in range(15):
            ctrl.dpad(0, 0.13)
        image.egg_phase = 1
        return 'WALKING1'
    
    elif state == 'WALKING1':
        walk_until_landmark_dpad(ctrl, image, dpad_dir= 4, lm= landmark)
        image.egg_phase = 0
        ctrl.up(BTN_B)
        return 'IN_GAME'
    return state

def Egg_Hatcher_BDSP(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
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
    if state == None:
        state = 'PAIRING'

    elif state == 'PAIRING':
        state = home_screen_checker_macro(ctrl, image)
        return state
    
    elif state == 'HOME_SCREEN' or state == 'START_SCREEN':
        state = bdsp_start_screens_macro(ctrl, image, state)
        sleep(1)
        return state
    
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
        
    elif state == 'IN_BOX1':
        sleep(0.17)
        if not image.generic_count == 0:
            put_egg(ctrl, image, 'BDSP')
        image.generic_count = 0
        return 'IN_BOX2'

    elif state == 'IN_BOX2':
        if image.egg_phase == 6:
            ctrl.tap(BTN_R)
            image.egg_phase = 0
        sleep(0.25)
        return 'IN_BOX3'
    
    elif state == 'IN_BOX3':
        grab_egg(ctrl, image, 'BDSP')
        image.egg_phase += 1
        sleep(0.75)
        return 'IN_BOX4'
    
    elif state == 'IN_BOX4':
        if not check_state(image, 'BDSP', 'poketch'):
            ctrl.tap(BTN_B)
            return 'IN_BOX4'
        return 'WALKING'

    elif state == 'WALKING':
        ctrl.down(BTN_B)
        for _ in range(20):
            if check_state(image, 'BDSP', 'text_box'):
                return 'HATCHING'
            else:
                ctrl.dpad(4, 0.13)
        return 'WALKING1'
    
    elif state == 'WALKING1':
        if check_state(image, 'BDSP', 'text_box'):
            return 'HATCHING'
        back_to_start = walk_until_landmark_dpad(ctrl, image, landmark, dpad_dir=0, max_steps=1)
        if back_to_start:
            return 'WALKING'

    elif state == 'HATCHING':
        if not hasattr(image, 'generic_bool'):
            image.generic_bool = False
        if not hasattr(image, 'egg_count'):
            image.egg_count = 0
        
        hit = False
        score = 1.0
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
        
        if check_state(image, 'BDSP', 'poketch'):
            if image.egg_count == count or image.shiny >= 1:
                return 'HATCHING_FINISHED'
            elif image.generic_count != 0 and image.generic_count == 5:
                image.generic_bool = False
                return 'IN_GAME'
            return 'WALKING1'
            
    return state

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