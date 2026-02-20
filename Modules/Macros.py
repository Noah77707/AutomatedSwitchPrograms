import os
import sys
import time
from time import monotonic, sleep
import serial
from enum import Enum
from .Controller import Controller
from .Image_Processing import Image_Processing, Text
from .States import *
from .Database import *
from .Debug import *
# controller_buttons.py
BTN_Y = 0
BTN_B = 1
BTN_A = 2
BTN_X = 3
BTN_L = 4
BTN_R = 5
BTN_ZL = 6
BTN_ZR = 7
BTN_MINUS = 8
BTN_PLUS = 9
BTN_LSTICK = 10
BTN_RSTICK = 11
BTN_HOME = 12
BTN_CAPTURE = 13
class Pokemon_Boxes:
    @staticmethod
    def _red_mask(bgr: np.ndarray) -> np.ndarray:
        """
        Binary mask of 'red outline' pixels. Tuned for BDSP cursor outline.
        Adjust S/V mins if needed.
        """
        hsv = cv.cvtColor(bgr, cv.COLOR_BGR2HSV)

        # red wraps hue around 0, so we need two ranges
        m1 = cv.inRange(hsv, (0,   70, 70), (10,  255, 255))
        m2 = cv.inRange(hsv, (170, 70, 70), (180, 255, 255))
        m = cv.bitwise_or(m1, m2)

        # cleanup
        k = np.ones((3, 3), np.uint8)
        m = cv.morphologyEx(m, cv.MORPH_OPEN, k, iterations=1)
        m = cv.dilate(m, k, iterations=1)
        return m

    @staticmethod
    def _green_mask(bgr: np.ndarray) -> np.ndarray:
        """
        Binary mask for the HOME cursor green outline.
        Hue ~ 35..85 is usually safe for "green" in OpenCV HSV (0..180).
        """
        hsv = cv.cvtColor(bgr, cv.COLOR_BGR2HSV)
        m = cv.inRange(hsv, (35, 70, 70), (85, 255, 255))
        k = np.ones((3, 3), np.uint8)
        m = cv.morphologyEx(m, cv.MORPH_OPEN, k, iterations=1)
        m = cv.dilate(m, k, iterations=1)
        return m

    @staticmethod
    def _blue_mask(bgr: np.ndarray) -> np.ndarray:
        """
        Binary mask for the HOME cursor blue outline.
        Hue ~ 90..135 is usually safe for "blue/cyan" in OpenCV HSV (0..180).
        """
        hsv = cv.cvtColor(bgr, cv.COLOR_BGR2HSV)
        m = cv.inRange(hsv, (90, 70, 70), (135, 255, 255))
        k = np.ones((3, 3), np.uint8)
        m = cv.morphologyEx(m, cv.MORPH_OPEN, k, iterations=1)
        m = cv.dilate(m, k, iterations=1)
        return m

    @staticmethod
    def _load_cursor_template_mask(template_path: str) -> np.ndarray | None:
        """
        Loads template image, builds a red-outline mask.
        If PNG has alpha, uses it to restrict the mask to the cursor pixels.
        """
        tpl = cv.imread(template_path, cv.IMREAD_UNCHANGED)
        if tpl is None:
            return None

        if tpl.ndim == 2:
            tpl_bgr = cv.cvtColor(tpl, cv.COLOR_GRAY2BGR)
            alpha = None
        elif tpl.shape[2] == 4:
            tpl_bgr = tpl[:, :, :3]
            alpha = tpl[:, :, 3]
        else:
            tpl_bgr = tpl
            alpha = None

        mask = Pokemon_Boxes._red_mask(tpl_bgr)

        if alpha is not None:
            mask = cv.bitwise_and(mask, alpha)

        # guard: empty mask => later normalization can blow up
        if cv.countNonZero(mask) < 25:
            return None

        return mask

    @staticmethod
    def find_cursor(frame_bgr: np.ndarray, template_mask: np.ndarray, search_roi=None) -> tuple[float, tuple[float, float] | None]:
        """
        Returns (score, (cx, cy)) or (0.0, None) if not found.
        Matching is done on red-outline binary masks to survive held-item overlays.
        """
        if search_roi is not None:
            x, y, w, h = map(int, search_roi)
            img = frame_bgr[y:y+h, x:x+w]
            offx, offy = x, y
        else:
            img = frame_bgr
            offx, offy = 0, 0

        if img.size == 0:
            return 0.0, None

        img_mask = Pokemon_Boxes._red_mask(img)

        # guard: if no red in ROI, TM_CCORR_NORMED can produce inf/NaN
        if cv.countNonZero(img_mask) < 25:
            return 0.0, None

        # ensure types match what OpenCV expects
        src = img_mask.astype(np.uint8)
        tpl = template_mask.astype(np.uint8)

        res = cv.matchTemplate(src, tpl, cv.TM_CCORR_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(res)

        if not np.isfinite(max_val):
            return 0.0, None

        th, tw = tpl.shape[:2]
        cx = float(offx + max_loc[0] + tw * 0.5)
        cy = float(offy + max_loc[1] + th * 0.5)
        return float(max_val), (cx, cy)

    @staticmethod
    def detect_box_cursor_xy(image, game: str) -> tuple[float, float] | None:
        g = const.GAME_STATES[game]["box"]["grid"]

        frame = getattr(image, "original_image", None)
        if frame is None:
            return None

        grid_roi = tuple(map(int, g["grid_roi"]))

        # allow either a single template path or a list
        tpl_paths = g.get("cursor_templates")
        if not tpl_paths:
            tpl_paths = g.get("cursor_template_paths") or []
            if isinstance(tpl_paths, str):
                tpl_paths = [tpl_paths]
            if not tpl_paths and g.get("cursor_template_path"):
                tpl_paths = [g["cursor_template_path"]]
            if not tpl_paths:
                return None


        best_score = -1.0
        best_pos = None

        for i, path in enumerate(tpl_paths):
            cache_key = f"_cursor_tplmask_{i}"
            tpl_mask = getattr(image, cache_key, None)
            if tpl_mask is None:
                tpl_mask = Pokemon_Boxes._load_cursor_template_mask(path)
                setattr(image, cache_key, tpl_mask)

            if tpl_mask is None:
                continue

            score, pos = Pokemon_Boxes.find_cursor(frame, tpl_mask, search_roi=grid_roi)
            if score > best_score and pos is not None:
                best_score, best_pos = score, pos

        if best_pos is None:
            return None

        th = float(g.get("cursor_threshold", 0.55))
        if best_score < th:
            return None

        return best_pos

    @staticmethod
    def get_box_cursor_rowcol(image, game: str) -> tuple[int, int] | None:
        g = const.GAME_STATES[game]["box"]["grid"]
        pos = Pokemon_Boxes.detect_box_cursor_xy(image, game)
        if pos is None:
            return None

        cx, cy = pos
        ox, oy = map(float, g["origin"])
        dx, dy = float(g["dx"]), float(g["dy"])
        rows, cols = int(g["rows"]), int(g["cols"])

        # pick nearest grid center (more stable than round)
        col = min(range(cols), key=lambda i: abs(cx - (ox + i * dx)))
        row = min(range(rows), key=lambda j: abs(cy - (oy + j * dy)))

        # optional sanity check
        tol = float(g.get("snap_tol_px", 30))
        ex = ox + col * dx
        ey = oy + row * dy
        if abs(cx - ex) > tol or abs(cy - ey) > tol:
            return None

        return row, col

    @staticmethod
    def snake_next(row: int, col: int, *, rows: int = 5, cols: int = 6) -> tuple[int, int, bool]:
        """
        Returns (next_row, next_col, done)

        Snake order:
          row 0: 0 -> 5
          row 1: 5 -> 0
          row 2: 0 -> 5
          ...
        """
        row = int(row); col = int(col)

        last_row = rows - 1
        last_col = cols - 1

        # finished already
        if row == last_row and col == (last_col if row % 2 == 0 else 0):
            return row, col, True

        if row % 2 == 0:
            if col < last_col:
                return row, col + 1, False
            return row + 1, last_col, False
        else:
            if col > 0:
                return row, col - 1, False
            return row + 1, 0, False

    @staticmethod
    def box_grid_final(
        ctrl,
        image,
        game: str,
        target_row: int,
        target_col: int,
        *,
        rows: int = 5,
        cols: int = 6,
        sleep_time: float = 0.10,
        verify: bool = True,
        timeout_s: float | None = None,
        stick_time: float = 0.17,
    ) -> tuple[int, int]:

        target_row = max(0, min(rows - 1, int(target_row)))
        target_col = max(0, min(cols - 1, int(target_col)))

        cur = Pokemon_Boxes.get_box_cursor_rowcol(image, game) if verify else None
        if cur is None:
            cur = (int(getattr(image.box, "row", 0)), int(getattr(image.box, "col", 0)))
        row, col = cur

        # --- dynamic timeout: scales with distance and your sleep_time ---
        step_s = float(stick_time) + float(sleep_time)
        dist = abs(target_row - row) + abs(target_col - col)
        needed = 0.75 + dist * (step_s + 0.03)  # +buffer for detection overhead
        if timeout_s is None:
            timeout_s = needed
        else:
            timeout_s = max(float(timeout_s), needed)

        def _safe_update(v: tuple[int, int] | None, exp_row: int, exp_col: int) -> tuple[int, int]:
            """Only accept verify updates if they are close to expected (prevents skipping)."""
            if v is None:
                return exp_row, exp_col
            vr, vc = v
            if abs(vr - exp_row) <= 1 and abs(vc - exp_col) <= 1:
                return vr, vc
            return exp_row, exp_col

        t0 = monotonic()
        while col != target_col and monotonic() - t0 < timeout_s:
            if col < target_col:
                ctrl.stick_right("L", stick_time)
                col += 1
            else:
                ctrl.stick_left("L", stick_time)
                col -= 1
            sleep(sleep_time)

            if verify:
                row, col = _safe_update(Pokemon_Boxes.get_box_cursor_rowcol(image, game), row, col)

        t0 = monotonic()
        while row != target_row and monotonic() - t0 < timeout_s:
            if row < target_row:
                ctrl.stick_down("L", stick_time)
                row += 1
            else:
                ctrl.stick_up("L", stick_time)
                row -= 1
            sleep(sleep_time)

            if verify:
                row, col = _safe_update(Pokemon_Boxes.get_box_cursor_rowcol(image, game), row, col)

        image.box.row, image.box.col = row, col
        return row, col

    def box_grid_advance(ctrl, row: int, col: int, cols: int = 6, rows: int = 5, sleep_time: float = 0.05) -> tuple[int, int]:
        if col < cols - 1:
            ctrl.stick_right("L", 0.1); sleep(sleep_time)
            return row, col + 1

        if row < rows - 1:
            ctrl.stick_down("L", 0.1); sleep(sleep_time)
            for _ in range(cols - 1):
                ctrl.stick_left("L", 0.1); sleep(sleep_time)
            return row + 1, 0

        return row, col

    def next_box(ctrl) -> None:
        for _ in range(4):
            ctrl.stick_up("L", 0.17); sleep(0.17)
        for _ in range(5):
            ctrl.stick_left("L", 0.17); sleep(0.17)
        sleep(0.17)
        ctrl.tap(BTN_R)

    def grab_pokemon(ctrl, image):
        image.box.cfg.append([image.box.row, image.box.col])
        x, y = image.box.row, image.box.col
        image.debugger.log("Grabbing from box slot:", image.box.row, image.box.col)
        ctrl.tap(BTN_A)
        
        Pokemon_Boxes.box_grid_final(ctrl, image, image.game, 0, 0, sleep_time=0.2)
            
        sleep(0.33); ctrl.stick_left("L", 0.17); sleep(0.33)
        for _ in range(5):
            ctrl.stick_down("L", 0.17); sleep(0.33)
        ctrl.tap(BTN_A, 0.05, 0.75)
        for _ in range(5):
            ctrl.stick_up("L", 0.17); sleep(0.33)
        ctrl.stick_right("L", 0.17); sleep(1)
        
        image.debugger.log("Putting in party", x, y)    
        Pokemon_Boxes.box_grid_final(ctrl, image, image.game, x, y, sleep_time=0.2)

    def put_pokemon(ctrl, image):
        """
        This is used to put the second pokemon in the party into a specific slot.
        Currently only works for the second party slot.
        """
        row, col = image.box.cfg.pop(0)
        
        ctrl.stick_left("L", 0.05); sleep(0.33)
        ctrl.stick_down("L", 0.05); sleep(0.33)
        kind, name = get_box_slot_kind(image, image.game)
        if kind == "shiny":
            image.database_component.shinies += 1
        ctrl.tap(BTN_A)
        ctrl.stick_up("L", 0.05); sleep(0.33)
        ctrl.stick_right("L", 0.05); sleep(0.33)
        Pokemon_Boxes.box_grid_final(ctrl, image, image.game, row, col, sleep_time=0.2)
        ctrl.tap(BTN_A)
        if image.box.cfg:
            Pokemon_Boxes.box_grid_final(ctrl, image, image.game, 0, 0, sleep_time=0.2)

def release_pokemon(ctrl: Controller, image: Image_Processing) -> str:
    """
    Should work for SWSH, BDSP, LA, and SV.\n
    LZA has a shiny symbol roi check instead of a state check.\n
    """
    match image.game:
        case "SWSH":
            sleeptime = 0.2
        case "BDSP":
            sleeptime = 0.2

    def _release_pokemon(ctrl: Controller):
        ctrl.tap(BTN_A)
        wait_state(image, image.game, False, 0.1, "text", "reply")
        sleep(sleeptime); ctrl.stick_up("L", 0.17)
        sleep(sleeptime); ctrl.stick_up("L", 0.17)
        sleep(sleeptime); ctrl.tap(BTN_A); sleep(sleeptime)
        wait_state(image, image.game, False, 0.4, "text", "reply")
        sleep(sleeptime); ctrl.stick_up("L", 0.17) 
        sleep(sleeptime); ctrl.tap(BTN_A); sleep(sleeptime)
        match image.game:
            case "SWSH":
                    wait_state(image, image.game, False, 0.1, "text", "text_ended")
                    ctrl.tap(BTN_A)
            case "BDSP":
                    sleep(1); ctrl.tap(BTN_A)

    if image.state == "IN_BOX":
        if image.box.box_i < image.box.box_amount:
            return return_states(image, "GO_THROUGH_BOX")
        else:
            return return_states(image, "PROGRAM_FINISHED")
        
    elif image.state == "GO_THROUGH_BOX":
        sleep(0.17)
        if hasattr(image, "wait_new_frame"):
            image.wait_new_frame(timeout_s=0.35)
        
        kind, name = get_box_slot_kind(image, image.game)
        image.debugger.log(kind, name, image.box.row, image.box.col)
        if kind == "pokemon":
            _release_pokemon(ctrl) 
            
            cleared = wait_state(
                image, image.game, True, 3.0, "pokemon", "pokemon_in_box",
                stable_frames=10
            )

            if not cleared:
                ctrl.tap(BTN_A, 0.05, 0.4)
                cleared = wait_state(
                    image, image.game, True, 2.0, "pokemon", "pokemon_in_box",
                    stable_frames=8
                )

            image.database_component.pokemon_released += 1
        elif kind == "shiny":
            image.database_component.shinies += 1
            image.database_component.pokemon_skipped += 1
        else:
            image.database_component.pokemon_skipped += 1

        if not (image.box.row == image.box.rows - 1 and image.box.col == image.box.cols - 1):
            image.box.row, image.box.col = Pokemon_Boxes.box_grid_advance(ctrl, image.box.row, image.box.col, sleep_time=0.17)
            return image.state
        else:
            return return_states(image, "NEXT_BOX")
    
    elif image.state == "NEXT_BOX":
        image.box.row = image.box.col = 0
        image.box.box_i += 1
        Pokemon_Boxes.next_box(ctrl); sleep(0.5)
        return return_states(image, "IN_BOX")

def home_screen_checker_macro(ctrl: Controller, image: Image_Processing, state: str | None) -> str:
    image.debugger.set_rois_for_state('PAIRING', [const.GENERIC_STATES['playing']['roi']], (0, 255, 0))

    if not hasattr(image, "_playing_lm"):
        image._playing_lm = get_landmark("GENERIC", "playing", 0.7)
    lm = image._playing_lm

    if check_state(image, 'GENERIC', 'pairing_screen'):
        ctrl.tap(BTN_L)
        ctrl.tap(BTN_R)
        sleep(1)
        ctrl.tap(BTN_A, 0.1, 1.5)
        ctrl.tap(BTN_HOME, 0.05, 0.5)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'controller_screen'):
        ctrl.tap(BTN_A, 0.05, 2)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'local_communication'):
        ctrl.tap(BTN_A, 0.05, 1.5)
        image.state= 'PAIRING'

    elif check_state(image, 'GENERIC', 'home_screen') and check_state(image, 'GENERIC', 'controller_connected'):
        if not hasattr(image, "playing_last_check_t"):
            image.playing_last_check_t = 0.0
        if not hasattr(image, "playing_last_score"):
            image.playing_last_score = 0.0

        now = monotonic()
        if now - image.playing_last_check_t >= 0.15:
            image.playing_last_check_t = now
            image.playing_last_score = detect_template(image.original_image, lm)

        score = image.playing_last_score
        if score >= lm.threshold:
            ctrl.tap(BTN_A)
            image.playing = True
            image.debugger.clear()
            return return_states(image, 'IN_GAME')
        else:
            ctrl.tap(BTN_A, 0.05, 1)
            ctrl.tap(BTN_A, 0.05, 0.75)
            image.debugger.clear()
            return return_states(image, "START_SCREEN")

    elif check_state(image, 'GENERIC', 'home_screen') and not check_state(image, 'GENERIC', 'controller_connected'):
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_B)
        image.state= 'PAIRING'

    elif image.state == 'PAIRING' and not check_state(image, 'GENERIC', 'home_screen') and not check_state(image, 'GENERIC', 'pairing_screen'):
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_B)
        ctrl.tap(BTN_HOME, 0.05, 0.4)
        ctrl.stick_down("L", 0.2); sleep(0.05)
        for _ in range(5):
            ctrl.stick_right("L", 0.2); sleep(0.05)
        ctrl.tap(BTN_A, 0.05, 2)
        image.state= 'PAIRING'
    
    else:
        if hasattr(image, "playing_checked"):
            image.playing_checked = False

    return image.state
 
def swsh_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'START_SCREEN':
        if check_state(image, 'SWSH', "screens", 'title_screen'):
            ctrl.tap(BTN_A, 0.1, 0.2)
            return 'IN_GAME'
        return "START_SCREEN"
    return image.state

def bdsp_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'HOME_SCREEN':
        if check_state(image, 'GENERIC', 'home_screen'):
            mash_a_while_textbox(ctrl, image, 'BDSP')
            return return_states(image, 'START_SCREEN')

    elif image.state == 'START_SCREEN':
        if not check_state(image, 'GENERIC', 'black_screen') and not check_state(image, 'BDSP', "screens", 'title_screen'):
            ctrl.tap(BTN_A, 0.05, 0.95)
            return return_states(image, 'START_SCREEN')
        if check_state(image, 'BDSP', "screens", 'title_screen'):
            sleep(1)
            ctrl.tap(BTN_A)
            return return_states(image, 'IN_GAME')
        
    return image.state

def sv_start_screens_macro(ctrl: Controller, image: Image_Processing, state = str) -> str:
    if image.state == 'START_SCREEN':
        if check_state(image, 'SV', 'title_screen'):
            ctrl.tap(BTN_A, 0.1, 0.2)
            return 'IN_GAME'
        return "START_SCREEN"
    return image.state

def mash_a_while_textbox(
        ctrl,
        image,
        game= str,
        max_seconds=15.0,
        press_interval=0.20,
        gone_confirm=30,
        watch_state: str | None = None
):
    t0 = time.time()
    last_press = 0.0
    gone_streak = 0

    while time.time() - t0 < max_seconds:
        if watch_state and check_state(image, game, watch_state):
            saw_watch = True
        
        visible = check_state(image, game, "text", "text_box")

        if visible:
            gone_streak = 0
            now = time.time()
            if now - last_press >= press_interval:
                ctrl.tap(BTN_A, 0.05, 0.0)
                last_press = now
            sleep(0.05)
        else:
            gone_streak += 1
            if gone_streak >= gone_confirm:
                return True
            sleep(0.1)

    return saw_watch

# time range is the amount of frames between the first battle textbox and the second battle textbox
# this finds the shiny due to the shiny animation adding a lot more frames inbetween both text boxes
def shiny_wait_checker(image, game, roi, frames: int, time_range_max: float, stable_frames: int = 2):
    now = monotonic()
    fid = getattr(image, 'frame_id', 0)
    last = getattr(image, 'last_frame_id', -1)
    if fid == last:
        return image.state
    image.last_frame_id = fid

    if not hasattr(image, "name"):
        image.name = ""
    if not hasattr(image, "name_captured"):
        image.name_captured = False
    if not hasattr(image, "name_prev"):
        image.name_prev = ""
    if not hasattr(image, "name_streak"):
        image.name_streak = 0

    text_visible = check_state(image, game, "text_box")

    # Rising edge: textbox appears
    if text_visible and not image.generic_bool:
        image.generic_bool = True

        if image.generic_count == 0:
            image.start_time = now
            image.generic_count = 1

            # reset name capture state for this encounter
            image.name = ""
            image.name_captured = False
            image.name_prev = ""
            image.name_streak = 0

        elif image.generic_count == 1:
            image.end_time = now
            image.generic_count = 2

    # While first textbox is visible: capture name when stable (no fixed delay)
    if text_visible and image.generic_bool and image.generic_count == 1 and not image.name_captured:
        raw = Text.recognize_pokemon(image, roi)
        raw = (raw or "").strip()

        # ignore trivial garbage
        if len(raw) >= 3:
            if raw == image.name_prev:
                image.name_streak += 1
            else:
                image.name_prev = raw
                image.name_streak = 1

            if image.name_streak >= stable_frames:
                image.database_component.pokemon_name = raw
                image.name_captured = True
                image.debugger.log("Name:", image.database_component.pokemon_name)

    # Falling edge: textbox disappears
    if (not text_visible) and image.generic_bool:
        image.generic_bool = False

    # Decide after second textbox
    if image.generic_count == 2:
        dt = float(image.end_time - image.start_time)
        image.debugger.log("dt_seconds:", dt)

        # reset for next
        image.generic_count = 0
        image.name_prev = ""
        image.name_streak = 0
        image.name_captured = False
        image.database_component.pokemon_encountered += 1

        if dt < time_range_max:
            image.database_component.resets += 1
            image.state = "NOT_SHINY"
        else:
            image.database_component.shinies += 1
            image.state = "FOUND_SHINY"

    return image.state

