import os
import sys
from datetime import datetime
from threading import Thread, Timer
from time import sleep, time, perf_counter
from typing import Any, Optional, Literal, TYPE_CHECKING, Callable
from queue import Queue
from threading import Event

from .Macros import *
from .Window_Capture import WindowCapture
from .Image_Processing import Image_Processing
from .Controller import Controller
from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *

from queue import Queue, Empty
from time import sleep, time, perf_counter

ProgramFn = Callable[[object, Controller, str], str]

PROGRAM_TABLE: dict[tuple[str, str], ProgramFn] = {
    # Home
    ('HOME', 'Connect_Controller_Test'): Connect_Controller_Test,
    ('HOME', 'Return_Home_Test'): Return_Home_Test,
    # SWSH
    ('SWSH', 'Static_Encounter_SWSH'): Static_Encounter_SWSH,
    ('SWSH', 'Egg_Hatcher_SWSH'): Egg_Hatcher_SWSH,
    ('SWSH', 'Pokemon_Releaser_SWSH'): Pokemon_Releaser_SWSH,

    # BDSP
    ('BDSP', 'Static_Encounter_BDSP'): Static_Encounter_BDSP,
    ('BDSP', 'Egg_Collector_BDSP'): Egg_Collector_BDSP,
    ('BDSP', 'Pokemon_Releaser_BDSP'): Pokemon_Releaser_BDSP,

}

def start_control_video(
        Device_Index: int,
        controller: Controller,
        Image_Queue: Queue,
        Shutdown_event: Event,
        stop_event: Event
        ) -> None:
    capture = WindowCapture(Device_Index)

    if not capture.video_capture.isOpened():
        capture.stop()
        print("NO CAPTURE CARD AVAILABLE")
        return

    while not Shutdown_event.is_set():
        ok, frame = capture.video_capture.read()
        if not ok:
            sleep(0.001)
            continue

        # drop old frame if present
        try:
            Image_Queue.get_nowait()
        except Empty:
            pass

        Image_Queue.put(frame)
        sleep(0.001)
    
def controller_control(
    ctrl: Controller,
    Command_queue: Queue,
    shutdown_event: Event,
    stop_event: Event,
    image: Image_Processing
) -> None:
    
    current_game = None
    current_program = None
    current_state = None
    running = False
    new_input = None

    while not shutdown_event.is_set():
        try:
            msg = Command_queue.get_nowait()
        except Empty:
            msg = None

        if isinstance(msg, dict):
            cmd = msg.get('cmd')
            print(msg)
            if cmd == 'SET_PROGRAM':
                new_game = msg.get('game')
                new_program = msg.get('program')
                new_input = msg.get('number')
                new_key = (new_game, new_program)
                old_key = (current_game, current_program)

                current_game = new_game
                current_program = new_program
                current_state = None
                running = True

            elif cmd == 'STOP':
                running = False
                
        if stop_event.is_set():
            running = False

        if not running or current_game is None or current_program is None:
            continue

        key = (current_game, current_program)
        step_fn = PROGRAM_TABLE.get(key)
        if step_fn is None:
            sleep(0.01)
            continue
        # print(f"[controller] calling {key} with frame_id={getattr(image, 'frame_id', None)}")

        current_state = step_fn(image, ctrl, current_state, new_input)
    ctrl.close()
        
# ChatGPT Debugger, will get rid of when not needed:
def frame_pump(Image_queue, shutdown_event, image):
    while not shutdown_event.is_set():
        frame = None
        try:
            while True:
                frame = Image_queue.get_nowait()
        except Empty:
            pass

        if frame is not None:
            image.original_image = frame
            image.frame_id = getattr(image, "frame_id", 0) + 1
        else:
            sleep(0.001)

def check_threads(threads: list[dict[str, Any]], shutdown_event: Event) -> None:
    while not shutdown_event.is_set():
        for thread in threads:
            if not thread['thread'].is_alive():
                shutdown_event.set()
        sleep(5)