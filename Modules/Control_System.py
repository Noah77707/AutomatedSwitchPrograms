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
    ('HOME', 'Connect_Controller_Test'): Connect_Controller_Test,
    ('SWSH', 'Static_Encounter_SWSH'): Static_Encounter_SWSH,
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
    Image_queue: Queue,
    Command_queue: Queue,
    shutdown_event: Event,
    stop_event: Event
) -> None:
    
    current_game = None
    current_program = None
    current_state = None
    running = False

    image = Image_Processing()
    image.frame_id = 0

    while not shutdown_event.is_set():
        frame = None
        try:
            while True:
                frame = Image_queue.get_nowait()
        except Empty:
            pass

        if frame is not None:
            image.original_image = frame
            # image.frame_id += 1
            # if image.frame_id % 60 == 0:
            #     print(f"[controller] frame_id=(image.frame_id)")

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

        current_state = step_fn(image, ctrl, current_state)
    ctrl.close()
        

def check_threads(threads: list[dict[str, Any]], shutdown_event: Event) -> None:
    while not shutdown_event.is_set():
        for thread in threads:
            if not thread['thread'].is_alive():
                shutdown_event.set()
        sleep(5)
