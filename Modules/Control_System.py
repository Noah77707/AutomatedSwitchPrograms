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
    
    game = None
    program = None
    state = None
    input = None
    running = False
    paused = False

    def finish_and_reset():
        nonlocal game, program
        if not game or not program:
            return
        d: RunStats = getattr(image, "database_component", RunStats())

        finish_run(
            game, program,
            actions_delta=d.actions,
            resets_delta=d.resets,
            pokemon_encountered_delta=d.pokemon_encountered,
            pokemon_caught_delta=d.pokemon_caught,
            eggs_collected_delta=d.eggs_collected,
            eggs_hatched_delta=d.eggs_hatched,
            pokemon_released_delta=d.pokemon_released,
            shinies_delta=d.shinies,
            action_hits_delta=d.action_hits,
            playtime_seconds_delta=d.playtime_seconds,
        )
        image.database_component = RunStats()


    while not shutdown_event.is_set():
        try:
            msg = Command_queue.get_nowait()
        except Empty:
            msg = None

        if isinstance(msg, dict):
            cmd = msg.get('cmd')
            print(msg)
            if cmd == 'SET_PROGRAM':
                game = msg.get('game')
                program = msg.get('program')
                input = msg.get('number')
                

                image.run = int(msg.get('runs', 1))
                image.profile = int(msg.get('profile', 1))

                state = None
                running = True
                paused = False

                image.database_component = RunStats()

            elif cmd == 'STOP' or image.state == 'PROGRAM FINISHED':
                if running and game and program:
                    finish_and_reset()
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

        if not running or game is None or program is None:
            sleep(0.01)
            continue

        if paused:
            sleep(0.01)
            continue

        key = (game, program)
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

