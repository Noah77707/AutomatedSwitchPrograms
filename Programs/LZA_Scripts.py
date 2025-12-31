import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *

def Start_LZA(image: Image_Processing, ctrl: Controller, state: str | None):
    ensure_stats(image)
    if state is None:
        state = 'PAIRING'
        return state

    elif state in ('PAIRING'):
        state = home_screen_checker_macro(ctrl, image, state)
        return state
    
    elif state in ('HOME_SCREEN', 'START_SCREEN'):
        if check_state(image, "LZA", "title_screen"):
            ctrl.tap(BTN_A)
            state = 'IN_GAME'
            return state
    
    return_state(image, state)
    image.playing_checked = False

    return state

def Donut_Checker(image: Image_Processing, ctrl: Controller, state: str | None, input: int | None):
    if state in (None, 'PAIRING', 'HOME_SCREEN', 'START_SCREEN'):
        state = Start_LZA(image, ctrl, state)
        return state

    elif state == "IN_GAME":
        if not check_state(image, 'LZA', 'loading_screen'):
            sleep(2)
            state = 'IN_GAME1'
            return state
    
    elif state == 'IN_GAME1':
        ctrl.tap(BTN_PLUS)
        state = 'IN_MAP'
        return state

    elif state == 'IN_MAP':
        if check_state(image, 'LZA', 'map_screen'):
            ctrl.tap(BTN_Y)
            for _ in range(4):
                sleep(0.17); ctrl.dpad(4, 0.05)
            sleep(0.17)
            ctrl.tap(BTN_A)
            state = 'TRAVELING'
            return state
    
    elif state == 'TRAVELING':
        if not check_state(image, 'LZA', 'loading_screen'):
            ctrl.stick('L', 128, 255, 2)
            ctrl.tap(BTN_A)
            state = 'IN_HOTEL'
            return state

    elif state == 'IN_HOTEL':
        if not check_state(image, 'LZA', 'loading_screen'):
            ctrl.stick('L', 128, 255, 4.25)
            ctrl.stick('L', 256, 128, 0.1)
            ctrl.tap(BTN_A)
            state = 'DONUT_SCREEN'
            return state
    
    elif state == 'DOUNT_SCREEN':
        ctrl.tap(BTN_A)
        if check_state(image, 'LZA', 'donut_screen'):
            if input == 1:
                ctrl.dpad(0, 0.1); sleep(0.17)
                for _ in range(4):
                    ctrl.tap(BTN_A)
                for _ in range(5):
                    sleep(0.4); ctrl.dpad(0, 0.1)
                sleep(0.17)
                for _ in range(4):
                    ctrl.tap(BTN_A)
                ctrl.tap(BTN_PLUS)
            elif input == 2:
                for _ in range(5):
                    sleep(0.4); ctrl.dpad(0, 0.1)
                sleep(0.17)
                for _ in range(4):
                    ctrl.tap(BTN_A)
                for _ in range(3):
                    sleep(0.4); ctrl.dpad(0, 0.1)
                sleep(0.17)
                for _ in range(4):
                    ctrl.tap(BTN_A)
                ctrl.tap(BTN_PLUS)
            state = 'DONUT_MAKING'
            return state
    
    elif state == 'DONUT_MAKING':
        if not check_state(image, 'LZA', 'donut_results'):
            ctrl.tap(BTN_A)
        else:
            state = 'DONUT_FINISHED'
            return state
    
    elif state == 'DOUNT_FINISHED':
        if not check_state(image, "LZA", "donut_result"):
            image.generic_bool = False
            return state

        if not hasattr(image, "generic_bool"):
            image.generic_bool = False

        texts = ocr_rois_cached(
            image,
            const.LZA_STATES['donut_powers_rois'],
            cache_key="lza_donut_powers"
        )
        
        if input == 1:
            keywords = ['Berries', 'Big Haul']
        elif input == 2:
            keywords = ['Types', 'Shining', 'Alpha']
        
        hits = find_keywords_in_texts(texts, keywords)
        has_all = all(hits.values())

        if has_all and not image.generic_bool:
            image.generic_bool = True
            image.database_component.action + 1
            state = "DOUNT_OK"
            return state
        
        if not has_all:
            image.generic_bool = False

        return state

    return_state(image, state)
    return state