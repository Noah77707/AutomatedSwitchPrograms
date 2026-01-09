import os
import sys
from datetime import datetime
from threading import Thread, Timer
from time import sleep, time, perf_counter, monotonic
from typing import Any, Optional, Literal, TYPE_CHECKING, Callable
from queue import Queue
from threading import Event

from .Macros import *
from .Window_Capture import WindowCapture
from .Image_Processing import Image_Processing
from .Controller import Controller
from .Database import *
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

    # SWSH
    ('SWSH', 'Static_Encounter_SWSH'): Static_Encounter_SWSH,
    ('SWSH', 'Egg_Hatcher_SWSH'): Egg_Hatcher_SWSH,
    ('SWSH', 'Pokemon_Releaser_SWSH'): Pokemon_Releaser_SWSH,

    # BDSP
    ('BDSP', 'Static_Encounter_BDSP'): Static_Encounter_BDSP,
    ('BDSP', 'Egg_Collector_BDSP'): Egg_Collector_BDSP,
    ('BDSP', 'Egg_Hatcher_BDSP'): Egg_Hatcher_BDSP,
    ('BDSP', 'Automated_Egg_BDSP'): Automated_Egg_BDSP,
    ('BDSP', 'Pokemon_Releaser_BDSP'): Pokemon_Releaser_BDSP,

    # LA

    # SV

    # LZA
    ('LZA', 'Donut_Checker_Berry'): Donut_Checker,
    ('LZA', 'Donut_Checker_Shiny'): Donut_Checker,


}

def start_control_video(
        Device_Index: int,
        controller: Controller,
        Image_Queue: Queue,
        Shutdown_event: Event,
        stop_event: Event
        ) -> None:
    
    capture = WindowCapture(Device_Index)

    cap = capture.video_capture
    if not cap.isOpened():
        capture.stop()
        print("NO CAPTURE CARD AVAILABLE")
        return

    try:
        cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    while not Shutdown_event.is_set():
        ok, frame = cap.read()
        if not ok or frame is None:
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

        Image_Queue.put(frame)
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
            print(msg)
            if cmd == 'SET_PROGRAM':
                image.game = msg.get('game')
                image.program = msg.get('program')
                input = msg.get('number')
                
                image.run = int(msg.get('runs', 1))
                image.profile = int(msg.get('profile', 1))

                state = None
                running = True
                paused = False

                image.database_component = RunStats()

            elif cmd == 'STOP' or image.state == 'PROGRAM FINISHED':
                add_program_deltas(image.game,
                                    image.program,
                                    actions_delta=int(getattr(image.database_component, "actions", 0)),
                                    action_hits_delta=int(getattr(image.database_component, "action_hits", 0)),
                                    resets_delta=int(getattr(image.database_component, "resets", 0)),
                                    eggs_collected_delta=int(getattr(image.database_component, "eggs_collected", 0)),
                                    eggs_hatched_delta=int(getattr(image.database_component, "eggs_hatched", 0)),
                                    pokemon_released_delta=int(getattr(image.database_component, "pokemon_released", 0)),
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
            sleep(0.0001)
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
        sleep(5)

