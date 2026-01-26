import os
import sys
from time import time, monotonic
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Start_LZA(image: Image_Processing, ctrl: Controller, state: str | None):
    if image.state is None:
        image.state = "PAIRING"
        return image.state

    elif image.state in ("PAIRING"):
        image.state = home_screen_checker_macro(ctrl, image, image.state)
        return image.state
    
    elif image.state in ("HOME_SCREEN", "START_SCREEN"):
        if check_state(image, "LZA", "screens", "title_screen"):
            sleep(1)
            if image.generic_bool == True:
                ctrl.down(BTN_B)
                ctrl.down(BTN_X)
                sleep(0.17); ctrl.dpad(0, 0.5)
                image.state = "BACKUP_SCREEN"
                return image.state
            else:
                ctrl.tap(BTN_A, 0.1, 1)
                image.state = "IN_GAME"
                return image.state

    elif image.state == "BACKUP_SCREEN":
        image.generic_bool = False
        ctrl.up(BTN_B)
        ctrl.up(BTN_X)
        if check_state(image, "LZA", "screens", "backup_screen") and not check_state(image, "LZA", "screens", "loading_screen"):
            ctrl.tap(BTN_A)
        elif check_state(image, "LZA", "screens", "loading_screen"):
            image.state = "IN_GAME"
            return image.state
        return image.state
        
    return state

def Menu_Navigation(ctrl: Controller, image: Image_Processing, target: str) -> None:
    def get_menu_cursor_index(image: Image_Processing, game: str = "LZA") -> int | None:
        menu = const.GAME_STATES[game]["menu"]
        for name, cfg in menu.items():
            if check_state(image, game, "menu", name):
                return int(cfg["index"])
        return None

    menu = const.LZA_STATES["menu"]
    
    target_position = menu[target]["index"]
    cur = get_menu_cursor_index(image, "LZA")
    image.debugger.log("menu cursor:", cur, "target:", target_position)

    if cur is None:
        return
    
    def row(i: int) -> int: return 0 if i < 5 else 1
    def col(i: int) -> int: return i % 5

    if row(cur) != row(target_position):
        ctrl.dpad(0 if row(cur) < row(target_position) else 4, 0.05)
        sleep(0.12)
        cur = get_menu_cursor_index(image, "LZA")
        if cur is None:
            return
        
    while col(cur) != col(target_position):
        if col(cur) < col(target_position):
            ctrl.dpad(2, 0.05)
        else:
            ctrl.dpad(6, 0.05)
        sleep(0.4)
        nxt = get_menu_cursor_index(image, "LZA")
        if nxt is None:
            return
        cur = nxt

def Donut_Checker(image: Image_Processing, ctrl: Controller, state: str | None, number: int | None):
    _lv_fix = re.compile(r"\(\s*lv\s*\.?\s*(\d+)\s*[\)\}]", re.IGNORECASE)
    def norm_line(s: str) -> str:
        s = (s or "").strip()
        s = s.replace("}", ")")             # fix OCR brace bug
        s = re.sub(r"\s+", " ", s)          # collapse spaces
        # normalize "(Lv.2)" / "(Lv. 2}" / "(lv 2)" -> "(Lv. 2)"
        s = _lv_fix.sub(lambda m: f"(Lv. {m.group(1)})", s)
        return s

    def expected_power_lines(power: str, lvl_range: tuple[int, int]) -> list[str]:
        lo, hi = map(int, lvl_range)
        if lo > hi:
            lo, hi = hi, lo
        return [norm_line(f"{power} (Lv. {lv})") for lv in range(lo, hi + 1)]
    
    def has_power(lines: list[str], power: str, lvl_range: tuple[int, int]) -> bool:
        line_set = {norm_line(x) for x in lines}
        expected = expected_power_lines(power, lvl_range)
        return any(e in line_set for e in expected)

    def _norm(s: str) -> str:
        s = (s or "").strip().lower()
        s = s.replace("’", "'")
        s = re.sub(r"[^a-z0-9]+", "", s)
        return s

    hotel_tpl   = get_tpl(image, "Media/LZA_Images/Hotel_Z.png")

    if image.state in (None, "PAIRING", "HOME_SCREEN", "START_SCREEN", "BACKUP_SCREEN"):
        image.state = Start_LZA(image, ctrl, image.state)
        return image.state

    elif image.state == "IN_GAME":
        if check_state(image, "LZA", "screens", "loading_screen") and image.playing == False:
            image.playing = True
        elif not check_state(image, "LZA", "screens", "loading_screen") and image.playing == True:
            image.state = "IN_GAME1"
            return image.state
    
    elif image.state == "IN_GAME1":
        sleep(3)
        ctrl.tap(BTN_PLUS)
        image.state = "IN_MAP"
        return image.state

    elif image.state == "IN_MAP":
        if check_state(image, "LZA", "map", "map_screen"):
            ctrl.tap(BTN_Y)
            image.state = "MAP_SELECTION"
            return image.state
    
    elif image.state == "MAP_SELECTION":
        now = monotonic()
        image.debugger.set_rois_for_state("MAP_SELECTION", const.LZA_STATES["map"]["map_screen_rois"], (255, 255, 255))
 
        row = None
        for i, roi in enumerate(const.LZA_STATES["map"]["map_screen_rois"]):
            if is_row_selected(image, roi):
                row = i
                break

        if row is None:
            return image.state

        roi = const.LZA_STATES["map"]["map_screen_rois"][row]
        image.debugger.set_focus_roi(roi, (0, 0, 0))
        if now - image.last_check_t >= 0.2:
            image.last_check_t = now
            image.generic_bool = match_label(image.original_image, roi, hotel_tpl)
        
            if image.generic_bool:
                image.state = "TRAVELING"
                return image.state
            else:
                ctrl.dpad(4, 0.05)
                return image.state
    
    elif image.state == "TRAVELING":
        image.generic_bool = False
        if not check_state(image, "LZA", "screens", "loading_screen"):
            ctrl.tap(BTN_A)
            return image.state
        image.state = "TRAVELING1"
        return image.state

    elif image.state == "TRAVELING1":
        if check_state(image, "LZA", "screens", "loading_screen"):
            image.generic_bool = True
        elif not check_state(image, "LZA", "screens", "loading_screen") and image.generic_bool == True:
            image.generic_bool = False
            ctrl.stick("L", 128, 0, 3)
            ctrl.tap(BTN_A)
            image.state = "IN_HOTEL"
            return image.state

    elif image.state == "IN_HOTEL":
        if check_state(image, "LZA", "screens", "loading_screen"):
            image.generic_bool = True
        elif not check_state(image, "LZA", "screens", "loading_screen") and image.generic_bool == True:
            image.generic_bool = False
            ctrl.stick("L", 128, 0, 3)
            ctrl.stick("L", 0, 128, 0.3)
            ctrl.tap(BTN_A, 0.05, 0.3)
            image.state = "DONUT_SCREEN"
            return image.state
    
    elif image.state == "DONUT_SCREEN":
        if check_state(image, "LZA", "text", "text_box"):
            ctrl.tap(BTN_A)
            return image.state
        elif check_state(image, "LZA", "screens", "donut_screen"):
            image.state = "FIRST_BERRY"
            return image.state
        
    elif image.state == "FIRST_BERRY":
        now = monotonic()
        image.debugger.set_rois_for_state("FIRST_BERRY", (const.LZA_STATES["donut"]["berry_select_rois"]), (255, 255, 255))

        row = None
        # Sour
        if number == 1:
            target = "roseli"
        # Sweet
        elif number == 2:
            target = "haban"
        # Spicy
        elif number == 3:
            target = "chilan"
        # Bitter
        elif number == 4:
            target = "babiri"
        # Fresh
        else:
            target = "colbur"

        row = None
        for i, roi in enumerate(const.LZA_STATES["donut"]["berry_select_rois"]):
            if is_row_selected(image, roi):
                row = i
                break

        if row is None:
            return image.state

        roi = const.LZA_STATES["donut"]["berry_select_rois"][row]
        image.debugger.set_focus_roi(roi, (0, 0, 0))

        if now - image.last_check_t < 0.25:
            return image.state
        image.last_check_t = now

        line = Text.ocr_line(image, roi, psm=7)
        line_n = re.sub(r"[^a-z0-9]+", "", (line or "").lower())

        if target in line_n:
            for _ in range(4):
                ctrl.tap(BTN_A)
            return return_states(image, "SECOND_BERRY")

        ctrl.dpad(0, 0.05); sleep(0.33)
        return image.state

    elif image.state == "SECOND_BERRY":
            now = monotonic()
            image.debugger.set_rois_for_state("SECOND_BERRY", (const.LZA_STATES["donut"]["berry_select_rois"]), (255, 255, 255))

            row = None
            # Sour
            if number == 1:
                target = "kasib"
            # Sweet
            elif number == 2:
                target = "tanga"
            # Spicy
            elif number == 3:
                target = "coba"
            # Bitter
            elif number == 4:
                target = "charti"
            # Fresh
            else:
                target = "payapa"

            row = None
            for i, roi in enumerate(const.LZA_STATES["donut"]["berry_select_rois"]):
                if is_row_selected(image, roi):
                    row = i
                    break

            if row is None:
                return image.state

            roi = const.LZA_STATES["donut"]["berry_select_rois"][row]
            image.debugger.set_focus_roi(roi, (0, 0, 0))

            if now - image.last_check_t < 0.25:
                return image.state
            image.last_check_t = now

            line = Text.ocr_line(image, roi, psm=7)
            line_n = re.sub(r"[^a-z0-9]+", "", (line or "").lower())

            if target in line_n:
                for _ in range(4):
                    ctrl.tap(BTN_A)
                ctrl.tap(BTN_PLUS)
                return return_states(image, "DONUT_MAKING")

            ctrl.dpad(0, 0.05)
            sleep(0.33)
            return image.state
    
    elif image.state == "DONUT_MAKING":
        if not check_state(image, "LZA", "donut", "donut_results"):
            ctrl.tap(BTN_A, 0.05, 0.5)
        else:
            return return_states(image, "DONUT_FINISHED")
    
    elif image.state == "DONUT_FINISHED":
        image.debugger.set_rois_for_state("DONUT_FINISHED", const.LZA_STATES["donut"]["donut_powers_rois"], (0, 0, 0))
        if not check_state(image, "LZA", "donut", "donut_results"):
            # reset stable OCR trackers so next results screen works
            for i in range(3):
                setattr(image, f"_ocr_prev_donut_line_{i}", "")
                setattr(image, f"_ocr_streak_donut_line_{i}", 0)
                setattr(image, f"_ocr_stable_donut_line_{i}", "")
            return image.state
        
        lines = Text.read_lines(image, const.LZA_STATES["donut"]["donut_powers_rois"], "donut_line_", 3, 4)
        if lines is None:
            return image.state
        
        ok = (
            has_power(lines, image.cfg["power1"], image.cfg["lvl1"]) and
            has_power(lines, image.cfg["power2"], image.cfg["lvl2"])
        )

        image.debugger.log(lines)
        image.debugger.log(ok)

        if not hasattr(image, "donut_scored"):
            image.donut_scored = False

        if not image.donut_scored:
            image.donut_scored = True

            image.database_component.actions += 1
            if ok:
                image.database_component.action_hits += 1
        
        if image.donut_scored == True:
            image.donut_scored = False
            return return_states(image, "DONUT_OK") if ok else return_states(image, "DONUT_BAD")

    elif image.state == "DONUT_BAD":
        image.donut_results_processed = False
        image.donut_visible_since_t = None
        add_program_deltas(
            game= image.game,
            program = image.program,
            actions_delta=1,
            resets_delta=1
        )
        ctrl.tap(BTN_HOME, 0.05, 0.45)
        ctrl.tap(BTN_X, 0.05, 0.25)
        ctrl.tap(BTN_A, 0.05, 02.95)
        image.database_component.resets += 1
        image.generic_bool = True
        return return_states(image, "PAIRING")
    
    elif image.state == "DONUT_OK":
        image.donut_results_processed = False
        image.donut_visible_since_t = None
        add_program_deltas(
            game= image.game,
            program = image.program,
            actions_delta=1,
            action_hits_delta=1
        )
        ctrl.tap(BTN_A, 0.05, 2)
        ctrl.tap(BTN_B, 0.05, 1)
        if image.database_component.action_hits == image.cfg["count"]:
            image.state = "PROGRAM_FINISHED"
            return return_states(image, "PROGRAM_FINISHED")
        return return_states(image, "IN_GAME1")
    
    return image.state