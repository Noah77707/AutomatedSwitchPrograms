import os
import sys
from time import sleep
from typing import Any, Callable
from queue import Queue
from threading import Event

from .Macros import *
from .Window_Capture import WindowCapture
from .Image_Processing import Image_Processing
from .Controller import Controller
from .Database import *
from .Debug import *
from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *

from queue import Queue, Empty, Full

ProgramFn = Callable[[object, Controller, str], str]

PROGRAM_TABLE: dict[tuple[str, str], ProgramFn] = {
    # Home
    ('HOME', 'Connect_Controller_Test'): Connect_Controller_Test,
    ('HOME', 'Return_Home_Test'): Return_Home_Test,
    ('HOME', "Press_A_Repeatadly"): Press_A_Repeatadly,

    # SWSH
    ('SWSH', 'Static_Encounter_SWSH'): Static_Encounter_SWSH,
    ('SWSH', 'Egg_Hatcher_SWSH'): Egg_Hatcher_SWSH,
    ('SWSH', "Fossil_Reviver_SWSH"): Fossil_Reviver_SWSH,
    ('SWSH', 'Pokemon_Releaser_SWSH'): Pokemon_Releaser_SWSH,

    # BDSP
    ('BDSP', 'Static_Encounter_BDSP'): Static_Encounter_BDSP,
    ('BDSP', 'Egg_Collector_BDSP'): Egg_Collector_BDSP,
    ('BDSP', 'Egg_Hatcher_BDSP'): Egg_Hatcher_BDSP,
    ('BDSP', 'Automated_Egg_BDSP'): Automated_Egg_BDSP,
    ('BDSP', 'Pokemon_Releaser_BDSP'): Pokemon_Releaser_BDSP,

    # LA

    # SV
    ('SV', 'Pokemon_Releaser_SV'): Pokemon_Releaser_SV,
    
    # LZA
    ('LZA', 'Donut_Checker'): Donut_Checker,


}

def start_control_video(
        Device_Index: int,
        controller: Controller,
        Image_Queue: Queue,
        Shutdown_event: Event,
        stop_event: Event,
        image: Image_Processing
        ) -> None:
    
    image.capture_index = int(Device_Index)
    capture = WindowCapture(image.capture_index)
    try:
        test = capture.read_frame()
        if test is None:
            image.capture_status = "fail"
            image.capture_status_msg = f"Capture index {image.capture_index} read failed"
        else:
            image.capture_status = "ok"
            image.capture_status_msg = f"Capture index {image.capture_index} ok"
    except Exception as e:
        image.capture_status = "fail"
        image.capture_status_msg = f"Capture error: {e}"


    while not Shutdown_event.is_set():
        pending = image.consume_pending_capture_index()
        if pending is not None and pending != image.capture_index:
            try:
                # if your WindowCapture has a release/close, call it
                if hasattr(capture, "release"):
                    capture.release()
                elif hasattr(capture, "close"):
                    capture.close()
            except Exception:
                pass

            image.capture_index = int(pending)
            capture = WindowCapture(image.capture_index)

        frame = capture.read_frame()
        if frame is None:
            sleep(0.005)
            continue
        
        # drop old frame if present
        while True:
            try:
                Image_Queue.put_nowait(frame)
                break
            except Full:
                try:
                    Image_Queue.get_nowait()
                except Empty:
                    break
        sleep(0.001)
    
def controller_control(
    ctrl: Controller,
    Command_queue: Queue,
    shutdown_event: Event,
    stop_event: Event,
    image: Image_Processing
) -> None:
    
    initialize_database()
    ensure_stats(image)

    current_port = None
    state = None
    input = None
    running = False
    paused = False

    while not shutdown_event.is_set():
        try:
            msg = Command_queue.get_nowait()
        except Empty:
            msg = None

        if isinstance(msg, dict):
            cmd = msg.get('cmd')
            image.debugger.log(msg)
            if cmd == "SET_DEVICES":
                # capture
                cap_idx = msg.get("capture_index", None)
                if cap_idx is not None:
                    image.request_capture_index(int(cap_idx))

                # microcontroller
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
                        image.debugger.log(f"MCU connect failed: {e}")
                continue

            if cmd == 'SET_PROGRAM':
                image.game = msg.get('game')
                image.program = msg.get('program')
                input = msg.get('number')
                            
                image.run = int(msg.get('runs', 1))
                image.profile = int(msg.get('profile', 1))
                image.cfg = msg.get("cfg") or {}

                state = None
                running = True
                paused = False

                image.database_component = RunStats()

            elif cmd == 'STOP' or image.state == "PROGRAM_FINISHED":
                add_program_deltas(image.game,
                                    image.program,
                                    playtime_seconds_delta=int(getattr(image.database_component, "playtime_seconds", 0)),
                            )
                image.database_component = RunStats()
                running = False
                paused = False
                state = False
                image.state = None
            elif cmd == 'PAUSE':
                paused = True

            elif cmd == 'RESUME':
                if running:
                   paused = False
                
        if stop_event.is_set():
            running = False

        if not running or image.game is None or image.program is None:
            sleep(0.01)
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
    ctrl.close()
        
def frame_pump(Image_queue, shutdown_event, image):
    if not hasattr(image, "frame_id"):
        image.frame_id = 0

    while not shutdown_event.is_set():
        try:
            # Block briefly waiting for one frame
            frame = Image_queue.get_nowait()
        except Empty:
            sleep(0.001)
            continue

        if frame is None:
            continue

        image.original_image = frame
        image.frame_id += 1
    
def check_threads(threads: list[dict[str, Any]], shutdown_event: Event) -> None:
    while not shutdown_event.is_set():
        for thread in threads:
            if not thread['thread'].is_alive():
                shutdown_event.set()
        sleep(1)

