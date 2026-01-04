import os
import sys
from time import time, monotonic
import serial
from Modules.Controller import Controller
from Modules.Macros import *

def Start_LZA(image: Image_Processing, ctrl: Controller, state: str | None):
    ensure_stats(image)
    if image.state is None:
        image.state = 'PAIRING'
        return image.state

    elif image.state in ('PAIRING'):
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state in ('HOME_SCREEN', 'START_SCREEN'):
        if check_state(image, "LZA", "title_screen"):
            sleep(1)
            if image.generic_bool == True:
                ctrl.down(BTN_B)
                ctrl.down(BTN_X)
                sleep(0.17); ctrl.dpad(0, 0.5)
                image.state = 'BACKUP_SCREEN'
                return image.state
            else:
                ctrl.tap(BTN_A, 0.1, 1)
                image.state = 'IN_GAME'
                return image.state

    elif image.state == 'BACKUP_SCREEN':
        image.generic_bool = False
        ctrl.up(BTN_B)
        ctrl.up(BTN_X)
        if check_state(image, 'LZA', 'backup_screen') and not check_state(image, 'LZA', 'loading_screen'):
            ctrl.tap(BTN_A)
        elif check_state(image, 'LZA', 'loading_screen'):
            image.state = 'IN_GAME'
            return image.state
        return image.state
        
    return state

def Donut_Checker(image: Image_Processing, ctrl: Controller, state: str | None, number: int | None):
    hotel_tpl   = get_tpl(image, "Media/LZA_Images/Hotel_Z.png")
    roseli_tpl  = get_tpl(image, "Media/LZA_Images/Roseli.png")
    haban_tpl   = get_tpl(image, "Media/LZA_Images/Haban.png")
    tanga_tpl   = get_tpl(image, "Media/LZA_Images/Tanga.png")
    kasib_tpl   = get_tpl(image, "Media/LZA_Images/Kasib.png")
    berries_tpl = get_tpl(image, "Media/LZA_Images/Berries.png")
    big_haul_tpl= get_tpl(image, "Media/LZA_Images/Big_Haul.png")
    shining_tpl = get_tpl(image, "Media/LZA_Images/AllTypes.png")
    alpha_tpl   = get_tpl(image, "Media/LZA_Images/Alpha.png")

    if image.state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN', 'BACKUP_SCREEN'):
        image.state = Start_LZA(image, ctrl, image.state)
        return image.state

    elif image.state == "IN_GAME":
        if check_state(image, 'LZA', 'loading_screen') and image.playing == False:
            image.playing = True
        elif not check_state(image, 'LZA', 'loading_screen') and image.playing == True:
            image.state = 'IN_GAME1'
            return image.state
    
    elif image.state == 'IN_GAME1':
        sleep(3)
        ctrl.tap(BTN_PLUS)
        image.state = 'IN_MAP'
        return image.state

    elif image.state == 'IN_MAP':
        if check_state(image, 'LZA', 'map_screen'):
            ctrl.tap(BTN_Y)
            image.state = 'MAP_SELECTION'
            return image.state
    
    elif image.state == 'MAP_SELECTION':
        now = monotonic()
        image.set_debug_rois_for_state('MAP_SELECTION', const.LZA_STATES['map_screen_rois'], (255, 255, 255))
 
        row = None
        for i, roi in enumerate(const.LZA_STATES['map_screen_rois']):
            if is_row_selected(image, roi):
                row = i
                break

        if row is None:
            return image.state

        roi = const.LZA_STATES['map_screen_rois'][row]
        image.set_debug_focus_roi(roi, (0, 0, 0))
        if now - image.last_check_t >= 0.2:
            image.last_check_t = now
            image.generic_bool = match_label(image.original_image, roi, hotel_tpl)
        
            if image.generic_bool:
                image.state = 'TRAVELING'
                return image.state
            else:
                ctrl.dpad(4, 0.05)
                return image.state
    
    elif image.state == 'TRAVELING':
        image.generic_bool = False
        if not check_state(image, 'LZA', 'loading_screen'):
            ctrl.tap(BTN_A)
            return image.state
        image.state = 'TRAVELING1'
        return image.state

    elif image.state == 'TRAVELING1':
        if check_state(image, 'LZA', 'loading_screen'):
            image.generic_bool = True
        elif not check_state(image, 'LZA', 'loading_screen') and image.generic_bool == True:
            image.generic_bool = False
            ctrl.stick('L', 128, 0, 3)
            ctrl.tap(BTN_A)
            image.state = 'IN_HOTEL'
            return image.state

    elif image.state == 'IN_HOTEL':
        if check_state(image, 'LZA', 'loading_screen'):
            image.generic_bool = True
        elif not check_state(image, 'LZA', 'loading_screen') and image.generic_bool == True:
            image.generic_bool = False
            ctrl.stick('L', 128, 0, 3)
            ctrl.stick('L', 0, 128, 0.3)
            ctrl.tap(BTN_A, 0.05, 0.3)
            image.state = 'DONUT_SCREEN'
            return image.state
    
    elif image.state == 'DONUT_SCREEN':
        if check_state(image, 'LZA', 'text_box'):
            ctrl.tap(BTN_A)
            return image.state
        elif check_state(image, 'LZA', 'donut_screen'):
            image.state = 'FIRST_BERRY'
            return image.state
        
    elif image.state == 'FIRST_BERRY':
        now = monotonic()
        image.set_debug_rois_for_state('FIRST_BERRY', const.LZA_STATES['berry_select_rois'], (255, 255, 255))

        row = None
        if number == 1:
            tpl = roseli_tpl
        elif number == 2:
            tpl = haban_tpl
        for i, roi in enumerate(const.LZA_STATES['berry_select_rois']):
            if is_row_selected(image, roi):
                row = i
                break

        if row is None:
            return image.state

        roi = const.LZA_STATES['berry_select_rois'][row]
        image.set_debug_focus_roi(roi, (0, 0, 0))
        
        if now - image.last_check_t >= 0.2:
            image.last_check_t = now
            image.generic_bool = match_label(image.original_image, roi, tpl)

            if image.generic_bool:
                for _ in range(4):
                    ctrl.tap(BTN_A)
                image.state = 'SECOND_BERRY'
                return image.state
            else:
                ctrl.dpad(0, 0.05)
                return image.state

    elif image.state == 'SECOND_BERRY':
        now = monotonic()
        image.set_debug_rois_for_state('SECOND_BERRY', const.LZA_STATES['berry_select_rois'], (255, 255, 255))

        row = None
        if number == 1:
            tpl = kasib_tpl
        elif number == 2:
            tpl = tanga_tpl
        for i, roi in enumerate(const.LZA_STATES['berry_select_rois']):
            if is_row_selected(image, roi):
                row = i
                break

        if row is None:
            return image.state

        roi = const.LZA_STATES['berry_select_rois'][row]
        image.set_debug_focus_roi(roi, (0, 0, 0))

        if now - image.last_check_t >= 0.2:
            image.last_check_t = now
            image.generic_bool = match_label(image.original_image, roi, tpl)

            if image.generic_bool:
                for _ in range(4):
                    ctrl.tap(BTN_A)
                ctrl.tap(BTN_PLUS)
                image.state = 'DONUT_MAKING'
                return image.state
            else:
                ctrl.dpad(0, 0.05)
                return image.state 

    elif image.state == 'DONUT_MAKING':
        if not check_state(image, 'LZA', 'donut_results'):
            ctrl.tap(BTN_A, 0.05, 0.5)
        else:
            image.state = 'DONUT_FINISHED'
            return image.state
    
    elif image.state == 'DONUT_FINISHED':
        now = monotonic()
        image.set_debug_rois_for_state('DONUT_FINISHED', const.LZA_STATES['donut_powers_rois'], (0, 0, 0))

        if not hasattr(image, "donut_results_processed"):
            image.donut_results_processed = False
        if not hasattr(image, "donut_visible_since_t"):
            image.donut_visible_since_t = None

        visible = check_state(image, "LZA", "donut_results")

        if visible:
            if image.donut_visible_since_t is None:
                image.donut_visible_since_t = now
        else:
            if image.donut_visible_since_t is not None and (now - image.donut_visible_since_t) > 0.2:
                image.donut_visible_since_t = None
            image.donut_results_processed = False
            return image.state

        if image.donut_results_processed:
            return image.state

        if image.donut_visible_since_t is None or (now - image.donut_visible_since_t) < 2:
            return image.state

        rois = const.LZA_STATES['donut_powers_rois']

        if number == 1:
            has_berries  = match_any_slot(image.original_image, rois, berries_tpl, 0.75)
            has_big_haul = match_any_slot(image.original_image, rois, big_haul_tpl, 0.75)
            has_all = has_berries and has_big_haul
        else:
            has_alltypes = match_any_slot(image.original_image, rois, shining_tpl, 0.75)
            has_alpha    = match_any_slot(image.original_image, rois, alpha_tpl, 0.75)
            has_all = has_alltypes and has_alpha

        image.donut_results_processed = True
        image.database_component.actions += 1

        if has_all:
            image.database_component.action_hits += 1
            image.state = 'DONUT_OK'
        else:
            image.state = 'DONUT_BAD'
        return image.state
        
    elif image.state == 'DONUT_BAD':
        image.donut_results_processed = False
        image.donut_visible_since_t = None
        ctrl.tap(BTN_HOME, 0.05, 0.45)
        ctrl.tap(BTN_X, 0.05, 0.25)
        ctrl.tap(BTN_A, 0.05, 02.95)
        image.database_component.resets += 1
        image.generic_bool = True
        image.state = 'PAIRING'
        return image.state
    
    elif image.state == 'DONUT_OK':
        image.donut_results_processed = False
        image.donut_visible_since_t = None
        ctrl.tap(BTN_A, 0.05, 2)
        ctrl.tap(BTN_B, 0.05, 1)
        if image.database_component.action_hits == image.run:
            image.state = "PROGRAM_FINISHED"
            return image.state
        image.state = 'IN_GAME1'
        return image.state
    
    return image.state