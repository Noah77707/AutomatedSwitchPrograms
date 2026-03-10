import os
import sys
from time import sleep
from typing import Any, Callable, Tuple
from queue import Queue, Full, Empty
from threading import Event

from .Macros import *
from .Window_Capture import WindowCapture
from .Image_Processing import Image_Processing
from .Controller import Controller
from .Database import *
from .Debug import *
from Programs.TEST_Scripts import *
from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *
from .Dataclasses import *

from queue import Queue, Empty

ProgramFn = Callable[[object, Controller, str], str]

PROGRAM_TABLE: dict[tuple[str, str], ProgramFn] = {
    # TEST
    ('TEST', 'Connect_Controller_Test'): Connect_Controller_Test,
    ('TEST', 'Return_Home_Test'): Return_Home_Test,
    ('TEST', "Press_A_Repeatadly"): Press_A_Repeatadly,

    # HOME
    ("HOME", "Sort_Home"): Sort_Home,
    ("HOME", "Rename_Boxes"): Rename_Boxes,
    ("HOME", "Sort_Specific_Pokemon_Types"): Sort_Specific_Pokemon_Types,
    
    # SWSH
    ('SWSH', 'Static_Encounter_SWSH'): Static_Encounter_SWSH,
    ('SWSH', 'Egg_Hatcher_SWSH'): Egg_Hatcher_SWSH,
    ('SWSH', "Fossil_Reviver_SWSH"): Fossil_Reviver_SWSH,
    ('SWSH', 'Egg_Collector_SWSH'): Egg_Collector_SWSH,
    ('SWSH', 'Egg_Hatcher_SWSH'): Egg_Hatcher_SWSH,
    ('SWSH', 'Pokemon_Releaser_SWSH'): Pokemon_Releaser_SWSH,

    # BDSP
    ('BDSP', 'Static_Encounter_BDSP'): Static_Encounter_BDSP,
    ('BDSP', 'Egg_Collector_BDSP'): Egg_Collector_BDSP,
    ('BDSP', 'Egg_Hatcher_BDSP'): Egg_Hatcher_BDSP,
    ('BDSP', 'Automated_Egg_BDSP'): Automated_Egg_BDSP,
    ('BDSP', 'Pokemon_Releaser_BDSP'): Pokemon_Releaser_BDSP,
    ('BDSP', 'Cursor_Test_BDSP'): Cursor_Test_BDSP,

    # LA

    # SV
    ('SV', 'Pokemon_Releaser_SV'): Pokemon_Releaser_SV,
    
    # LZA
    ('LZA', 'Donut_Checker'): Donut_Checker,


}

def flush_runstats_to_db(image: Image_Processing) -> None:
    """
    Push everything accumulated in image.database_component (RunStats) into DB.
    Then reset image.database_component to a fresh RunStats.
    """
    rs = getattr(image, "database_component", None)
    if rs is None:
        return

    game = getattr(image, "game", None)
    program = getattr(image, "program", None)
    if not game or not program:
        return

    # Program-level deltas
    add_program_deltas(
        game,
        program,
        runs_delta=int(getattr(rs, "runs", 0)),
        resets_delta=int(getattr(rs, "resets", 0)),
        encounters_delta=int(getattr(rs, "encounters", 0)),
        actions_delta=int(getattr(rs, "actions", 0)),
        action_hits_delta=int(getattr(rs, "action_hits", 0)),
        eggs_collected_delta=int(getattr(rs, "eggs_collected", 0)),
        eggs_hatched_delta=int(getattr(rs, "eggs_hatched", 0)),
        pokemon_encountered_delta=int(getattr(rs, "pokemon_encountered", 0)),
        pokemon_caught_delta=int(getattr(rs, "pokemon_caught", 0)),
        pokemon_released_delta=int(getattr(rs, "pokemon_released", 0)),
        pokemon_skipped_delta=int(getattr(rs, "pokemon_skipped", 0)),
        shinies_delta=int(getattr(rs, "shinies", 0)),
        playtime_seconds_delta=int(getattr(rs, "playtime_seconds", 0)),
    )

    # Pokemon-level deltas (only if we have a valid name)
    name = (getattr(rs, "pokemon_name", None) or "").strip()
    if name:
        add_pokemon_delta(
            game,
            program,
            name,
            encountered_delta=int(getattr(rs, "pokemon_encountered", 0)),
            caught_delta=int(getattr(rs, "pokemon_caught", 0)),
            shinies_delta=int(getattr(rs, "shinies", 0)),
            eggs_hatched_delta=int(getattr(rs, "eggs_hatched", 0)),
        )

    image.database_component = RunStats()
# Not in use currently, Might change that if crashing becomes common after fixing up the code
def maybe_periodic_flush(image: Image_Processing, every_s: float = 10.0) -> None:
    """
    Optional safety flush so it doesn't lose everything in a crash
    """
    now = time()
    last = getattr(image, "_last_stats_flush_t", 0.0)
    if now - last < every_s:
        return
    image._last_stats_flush_t = now

    rs = getattr(image, "database_component", None)
    if rs is None:
        return

    # Only flush if something changed
    if any(
        int(getattr(rs, k, 0)) != 0
        for k in (
            "runs",
            "resets",
            "encounters",
            "actions",
            "action_hits",
            "eggs_collected",
            "eggs_hatched",
            "pokemon_encountered",
            "pokemon_caught",
            "pokemon_released",
            "pokemon_skipped",
            "shinies",
            "playtime_seconds",
        )
    ):
        flush_runstats_to_db(image)

def start_control_video(
    Device_Index,
    Image_Queue,          # unused
    Shutdown_event,
    stop_event,
    image,
) -> None:
    # -1 / None means "no capture yet"
    if Device_Index is None:
        Device_Index = -1
    Device_Index = int(Device_Index)

    capture: Optional[WindowCapture] = None
    last_fid = -1

    def _open(idx: int) -> WindowCapture:
        cap = WindowCapture(idx, w=1280, h=720, fps=60)
        # optional: keep this if you use it elsewhere
        if hasattr(image, "attach_capture"):
            image.attach_capture(cap)
        return cap

    def _close(cap: Optional[WindowCapture]) -> None:
        if cap is None:
            return
        try:
            cap.stop()
        except Exception:
            pass

    # initialize capture state
    try:
        image.capture.capture_index = Device_Index
        image.capture.capture_status = "idle" if Device_Index < 0 else "pending"
        image.capture.capture_status_msg = "" if Device_Index < 0 else f"Opening capture {Device_Index}..."
    except Exception:
        pass

    # open immediately only if valid
    if Device_Index >= 0:
        try:
            capture = _open(Device_Index)
            try:
                image.capture.capture_status = "ok"
                image.capture.capture_status_msg = f"Capture index {Device_Index} ok"
            except Exception:
                pass
        except Exception as e:
            capture = None
            try:
                image.capture.capture_status = "fail"
                image.capture.capture_status_msg = f"Capture open failed: {e}"
            except Exception:
                pass

    while not Shutdown_event.is_set():
        pending = None
        if hasattr(image, "consume_pending_capture_index"):
            pending = image.consume_pending_capture_index()

        if pending is not None:
            pending = int(pending)

            # close current
            _close(capture)
            capture = None
            last_fid = -1

            # publish "no frame" so GUI won't show stale
            try:
                if hasattr(image, "publish_frame"):
                    image.publish_frame(None, fid=None)  # if your publish_frame supports clearing
                else:
                    with image._lock:
                        image.original_image = None
                        image.frame_id += 1
            except Exception:
                pass

            try:
                image.capture.capture_index = pending
                image.capture.capture_epoch += 1
            except Exception:
                pass

            if pending < 0:
                # stay disabled
                try:
                    image.capture.capture_status = "idle"
                    image.capture.capture_status_msg = "No capture selected"
                except Exception:
                    pass
            else:
                # open new
                try:
                    capture = _open(pending)
                    try:
                        image.capture.capture_status = "ok"
                        image.capture.capture_status_msg = f"Capture index {pending} ok"
                    except Exception:
                        pass
                except Exception as e:
                    capture = None
                    try:
                        image.capture.capture_status = "fail"
                        image.capture.capture_status_msg = f"Capture index {pending} open failed: {e}"
                    except Exception:
                        pass

        # IMPORTANT: do not read if capture is disabled
        if capture is None:
            sleep(0.01)
            continue

        frame, fid = capture.read_latest()
        if frame is None or fid == last_fid:
            sleep(0.001)
            continue

        last_fid = fid

        # publish
        if hasattr(image, "publish_frame"):
            # publish_frame(frame_bgr, fid=...)
            try:
                image.publish_frame(frame, fid=fid)
            except TypeError:
                # older signatures
                try:
                    image.publish_frame(fid, frame)
                except TypeError:
                    image.publish_frame(frame)
        else:
            with image._lock:
                image.original_image = frame
                image.frame_id = fid

def controller_control(
    ctrl: Controller,
    Command_queue: Queue,
    shutdown_event: Event,
    stop_event: Event,
    image: Image_Processing
) -> None:

    initialize_database()

    current_port = None
    state = None
    input = None
    running = False
    paused = False

    while not shutdown_event.is_set():
        msg = None
        if not running:
            try:
                msg = Command_queue.get(timeout=0.1)
            except Empty:
                msg = None
        else:
            try:
                msg = Command_queue.get_nowait()
            except Empty:
                msg = None

        if isinstance(msg, dict):
            cmd = msg.get("cmd")
            if getattr(image, "debugger", None) is not None:
                image.debugger.log(msg)

            if cmd == "SET_DEVICES":
                cap_idx = msg.get("capture_index", None)
                if cap_idx is not None:
                    image.request_capture_index(int(cap_idx))

                new_port = (msg.get("mcu_port") or "").strip()
                if new_port and new_port != current_port:
                    try:
                        ctrl.close()
                    except Exception:
                        pass
                    try:
                        ctrl.connect(new_port)
                        current_port = new_port
                    except Exception as e:
                        current_port = None
                        if getattr(image, "debugger", None) is not None:
                            image.debugger.log(f"MCU connect failed: {e}")
                continue

            if cmd == "SET_PROGRAM":
                image.game = msg.get("game")
                image.program = msg.get("program")
                input = msg.get("number")

                image.run = int(msg.get("runs", 1))
                image.profile = int(msg.get("profile", 1))
                image.cfg = msg.get("cfg") or {}

                state = None
                running = True
                paused = False
                image.state = None
                image.database_component = RunStats()

            elif cmd == "STOP":
                flush_runstats_to_db(image)
                image.database_component = RunStats()
                image.debugger = Debug()
                image.gate = FrameGate()
                image.capture = CaptureState()
                image.box = Box()
                image.egg = Egg()

                running = False
                paused = False
                state = None
                image.state = None

            elif cmd == "PAUSE":
                paused = True

            elif cmd == "RESUME":
                if running:
                    paused = False

        if stop_event.is_set():
            running = False

        if not running or image.game is None or image.program is None:
            continue

        if paused:
            sleep(0.01)
            continue

        key = (image.game, image.program)
        step_fn = PROGRAM_TABLE.get(key)
        if step_fn is None:
            sleep(0.01)
            continue

        state = step_fn(image, ctrl, state, input)

        if getattr(image, "state", None) == "PROGRAM_FINISHED":
            flush_runstats_to_db(image)
            image.database_component = RunStats()
            running = False
            paused = False
            state = None
            image.state = None

    try:
        ctrl.close()
    except Exception:
        pass

def check_threads(threads: list[dict[str, Any]], shutdown_event: Event) -> None:
    while not shutdown_event.is_set():
        for thread in threads:
            if not thread['thread'].is_alive():
                shutdown_event.set()
        sleep(1)