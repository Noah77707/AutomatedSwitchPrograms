import os
import sys
import subprocess
from queue import Queue, Empty
from time import sleep, monotonic
from typing import TYPE_CHECKING
from threading import Event
import Constants as const
import cv2 as cv
from .Controller import Controller

import PyQt6.QtWidgets as pyqt_w
import PyQt6.QtCore as pyqt_c
import PyQt6.QtGui as pyqt_g

from .Image_Processing import Image_Processing
from .Database import get_stats, format_hms
from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIA_DIR = os.path.join(BASE_DIR, 'media')  # media/SWSH, media/BDSP, etc.

MODULE_NAME = 'GUI'

image_label_style = 'background-color: #000; border: 1px solid #aaa'
text_label_style = ''
text_style = ''
clock_style = ''
stop_button_style = ''

class App(pyqt_w.QApplication):
    def __init__(self):
        super().__init__([])
        self.setStyleSheet('QWidget { background-color: #333; }')

class GUI(pyqt_w.QWidget):
    def __init__(
            self, 
            Image_queue: Queue, 
            Command_queue: Queue, 
            shutdown_event: Event, 
            stop_event: Event, 
            image: Image_Processing) -> None:
        super().__init__()

        # tracks information that is important that every part of the gui can access

        self.Image_queue = Image_queue
        self.Command_queue = Command_queue
        self.image = image

        self.game = str
        self.program = str
        self.state = str
        self.tracks = []
        self.numberinput = int
        self.debug = False
        self.running = False
        self.paused = False
        self.run_seconds = 0.0
        self.run_last_t = None

        self.stats_timer = pyqt_c.QTimer(self)
        self.stats_timer.timeout.connect(self.stat_timer)
        self.stats_timer.start(1000)

        self.setWindowTitle('Auto Switch Programs')

        main_layout = pyqt_w.QHBoxLayout(self)

        self.latest_frame = None
        self.region_radius = 5

        self.items = {
            'switch_capture_label': pyqt_w.QLabel(self),
            'start_stop_button': pyqt_w.QPushButton(self),
            'current_state_label': pyqt_w.QLabel(self                                                  ),
            'stats_label': pyqt_w.QLabel(self),
            'tab_home': pyqt_w.QWidget(self),
            'tab_swsh': pyqt_w.QWidget(self),
            'tab_bdsp': pyqt_w.QWidget(self),
            'tab_la':   pyqt_w.QWidget(self),
            'tab_sv':   pyqt_w.QWidget(self),
            'tab_lza':  pyqt_w.QWidget(self),
        }
        # sets up the switch capture label so that the program outputs the screen
        self.items['switch_capture_label'].setFixedSize(*const.MAIN_FRAME_SIZE)
        self.items['switch_capture_label'].setStyleSheet(image_label_style)

        self.tabs = pyqt_w.QTabWidget()
        self.tabs.setTabPosition(pyqt_w.QTabWidget.TabPosition.West)
        self.tabs.setMovable(True)

        # HOME tab
        Home_layout = pyqt_w.QVBoxLayout()
        Home_layout.addWidget(pyqt_w.QLabel('HOME programs'))
        CCT_HOME = pyqt_w.QPushButton('Controller Connection Test', self)
        CCT_HOME.clicked.connect(lambda checked, p='Connect_Controller_Test': self.update_script('HOME', p, checked))
        RHT_HOME = pyqt_w.QPushButton('Return Home Test', self)
        RHT_HOME.clicked.connect(lambda checked, p='Return_Home_Test': self.update_script('Home', p, checked))

        Home_layout.addWidget(CCT_HOME)
        Home_layout.addWidget(RHT_HOME)
        self.items['tab_home'].setLayout(Home_layout)

        # SWSH tab
        SWSH_layout = pyqt_w.QVBoxLayout()
        SWSH_layout.addWidget(pyqt_w.QLabel('SWSH programs'))
        self.items['tab_swsh'].setLayout(SWSH_layout)

        # BDSP tab
        BDSP_layout = pyqt_w.QVBoxLayout()
        BDSP_layout.addWidget(pyqt_w.QLabel('BDSP programs'))

        STATIC_ENCOUNTER_BDSP = pyqt_w.QPushButton('Static Encounter WIP', self)
        STATIC_ENCOUNTER_BDSP.clicked.connect(lambda checked, p='Static_Encounter_BDSP': self.update_script('BDSP', p, checked))
        
        EGG_COLLECTOR_BDSP = pyqt_w.QPushButton('Egg Collector', self)
        EGG_COLLECTOR_BDSP.setProperty('tracks', ['eggs_collected', 'shinies', 'playtime_seconds'])
        EGG_COLLECTOR_BDSP.clicked.connect(lambda checked, btn= EGG_COLLECTOR_BDSP: self.update_script_textbox('BDSP', btn, 'Egg_Collector_BDSP', checked))
        
        EGG_HATCHER_BDSP = pyqt_w.QPushButton('Egg Hatcher', self)
        EGG_HATCHER_BDSP.setProperty('tracks', ['eggs_hatched', 'shinies', 'playtime_seconds'])
        EGG_HATCHER_BDSP.clicked.connect(lambda checked, btn= EGG_HATCHER_BDSP: self.update_script_textbox('BDSP', btn, 'Egg_Hatcher_BDSP', checked))
        
        AUTOMATED_EGG_BDSP = pyqt_w.QPushButton('Automated Egg Collector/Hatcher/Releaser')
        AUTOMATED_EGG_BDSP.setProperty('tracks', ['eggs_collected', 'eggs_hatched', 'pokemon_released', 'shinies', 'playtime_seconds'])
        AUTOMATED_EGG_BDSP.clicked.connect(lambda checked, btn= AUTOMATED_EGG_BDSP: self.update_script_textbox('BDSP', btn, 'Automated_Egg_BDSP', checked))
        
        RELEASER_BDSP = pyqt_w.QPushButton('Pokemon Releaser', self)
        RELEASER_BDSP.setProperty('tracks', ['pokemon_released', 'pokemon_skipped', 'playtime_seconds'])
        RELEASER_BDSP.clicked.connect(lambda checked, btn= RELEASER_BDSP: self.update_script_textbox('BDSP', btn, 'Pokemon_Releaser_BDSP', checked))

        BDSP_layout.addWidget(STATIC_ENCOUNTER_BDSP)
        BDSP_layout.addWidget(EGG_COLLECTOR_BDSP)
        BDSP_layout.addWidget(EGG_HATCHER_BDSP)
        BDSP_layout.addWidget(AUTOMATED_EGG_BDSP)
        BDSP_layout.addWidget(RELEASER_BDSP)
        self.items['tab_bdsp'].setLayout(BDSP_layout)

        self.tabs.addTab(self.items['tab_home'], 'HOME')
        self.tabs.addTab(self.items['tab_swsh'], 'SWSH')
        self.tabs.addTab(self.items['tab_bdsp'], 'BDSP')
        self.tabs.addTab(self.items['tab_la'],   'LA')
        self.tabs.addTab(self.items['tab_sv'],   'SV')
        self.tabs.addTab(self.items['tab_lza'],  'LZA')

        self.current_program_name = self.tabs.tabText(self.tabs.currentIndex())
        self.current_process = None

        self.tabs.currentChanged.connect(self.on_tab_changed)

        # ---------- LEFT PANEL: tabs ----------
        left_panel = pyqt_w.QVBoxLayout()
        left_panel.addWidget(self.tabs)

        # ---------- RIGHT PANEL: capture + labels + buttons ----------
        right_panel = pyqt_w.QVBoxLayout()
        right_panel.addWidget(self.items['switch_capture_label'])

        info_row = pyqt_w.QHBoxLayout()
        info_row.addWidget(self.items['stats_label'])
        self.items['stats_label'].setText(self.update_stats())
        self.items['stats_label'].setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)

        self.debug_button = pyqt_w.QPushButton('Draw Debug', self)
        self.debug_button.clicked.connect(self.update_debug)

        self.screenshot_button = pyqt_w.QPushButton('Save Screenshot', self)
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)

        self.start_button = pyqt_w.QPushButton('Start Program', self)
        self.start_button.clicked.connect(self.start_scripts)

        self.pause_button = pyqt_w.QPushButton('Pause Program', self)
        self.pause_button.clicked.connect(self.pause_scripts)

        self.stop_button = pyqt_w.QPushButton('Stop Program', self)
        self.stop_button.clicked.connect(self.stop_scripts)

        self.items['start_stop_button'].setText("Start / Stop")

        button_row_debug = pyqt_w.QHBoxLayout()
        button_row_debug.addWidget(self.debug_button)
        button_row_debug.addWidget(self.screenshot_button)

        button_row_program = pyqt_w.QHBoxLayout()
        button_row_program.addWidget(self.start_button)
        button_row_program.addWidget(self.pause_button)
        button_row_program.addWidget(self.stop_button)

        right_panel.addLayout(info_row)
        right_panel.addLayout(button_row_debug)
        right_panel.addLayout(button_row_program)
        right_panel.addStretch(1)

        # ---------- attach to main ----------
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 0)     

        self.timer = pyqt_c.QTimer(self)
        self.timer.timeout.connect(lambda: self.update_GUI(shutdown_event))
        self.timer.start(16)

        self.show()

    # updates the GUI's capture screen so the current frame from the switch is being shown
    def update_GUI(self, shutdown_event: Event) -> None:
        if shutdown_event.is_set():
            self.close()
            return
        
        self.items['stats_label'].setText(self.update_stats())

        frame = getattr(self.image, 'original_image', None)
        if frame is None:
            return

        frame_to_show = frame
        if getattr(self.image, 'draw_debug', False):
            frame_to_show = self.image.draw_debug(frame.copy())

        # convert BGR -> RGB
        frame_rgb = cv.cvtColor(frame_to_show, cv.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        qimg = pyqt_g.QImage(
            frame_rgb.data, w, h, bytes_per_line,
            pyqt_g.QImage.Format.Format_RGB888
        )
        pix = pyqt_g.QPixmap.fromImage(qimg)
        # if label size differs from frame size, scale
        if (self.items['switch_capture_label'].width(), self.items['switch_capture_label'].height()) != (w, h):
            pix = pix.scaled(
                self.items['switch_capture_label'].width(),
                self.items['switch_capture_label'].height(),
                pyqt_c.Qt.AspectRatioMode.KeepAspectRatio,
                pyqt_c.Qt.TransformationMode.SmoothTransformation
            )
        self.items['switch_capture_label'].setPixmap(pix)
    # updates the stats that are shown to the player
    def update_stats(self):
        s = getattr(self.image, 'database_component', None)
        if not s:
            return ''
        
        parts = []
        for key in self.tracks:
            val = getattr(s, key, 0)
            if key == 'playtime_seconds':
                parts.append(f'time: {format_hms(int(val))}')
            else:
                parts.append(f'{key}: {val}')
        parts.append(f'state: {getattr(self.image, 'state', None)}')
        return ' | '.join(parts)
    # creates the timer that is used to see how long the program ran
    def stat_timer(self):
        if self.running and not self.paused:
            now = monotonic()
            if self.run_last_t is None:
                self.run_last_t = now
            else:
                dt = (now - self.run_last_t)
                self.run_last_t = now
                if dt > 0:
                    self.run_seconds += dt
                    whole = int(self.run_seconds)
                    if whole > 0:
                        self.run_seconds -= whole
                        database = getattr(self.image, 'database_component', None)
                        if database is not None:
                            database.playtime_seconds += whole
        
        self.items['stats_label'].setText(self.update_stats())
    # changes the programs you can see per tab
    def on_tab_changed(self, index: int) -> None:
        self.current_program_name = self.tabs.tabText(index)
        self.Command_queue.put({
            'type': 'SET_GAME',
            'game': self.current_program_name
        })
    # updates the program to be the one that runs when you start the script
    def update_script(self, game: str, btn: pyqt_w.QPushButton, program: str, checked: bool = False) -> None:
        self.game = game
        self.program = program
        self.tracks = btn.property('tracks') or []
        self.numberinput = 0
    # updates the program to be the one that runs when you start the script, along with adding an input for the player
    def update_script_textbox(self, game: str, btn: pyqt_w.QPushButton, program: str, checked: bool = False) -> None:
        text, ok = pyqt_w.QInputDialog.getText(self, 'How Many Boxes', 'Enter Box Amount (input 0 for all boxes):')
        if ok and text:
            self.numberinput = text
        self.game = game
        self.program = program
        self.tracks = btn.property('tracks') or []
    # starts the script/program
    def start_scripts(self) -> None:
        self.Command_queue.put({'cmd': 'SET_PROGRAM', 'game': self.game, 'program': self.program, 'number': self.numberinput, 'running': True})
        self.running = True
        self.paused = False
        self.run_last_t = monotonic()
        self.run_seconds = 0.0
    # pauses the script/program
    def pause_scripts(self) -> None:
        if not self.running:
            return
        
        if not self.paused:
            self.Command_queue.put({'cmd': 'PAUSE'})
            self.paused = True
            self.run_last_t = None
            self.pause_button.setText('Resume Program')
        else:
            self.Command_queue.put({'cmd': 'RESUME'})
            self.paused = False
            self.run_last_t = monotonic()
            self.pause_button.setText('Pause Program')
    # ends the scripts/program, sends command to update the database
    def stop_scripts(self) -> None:
        self.Command_queue.put({'cmd': 'STOP'})
        self.running = False
        self.paused = False
        self.run_last_t = None
        self.run_seconds = 0.0
    # allows the player to put the debug information (rois only currently) onto the screen
    def update_debug(self) -> None:
        if self.image.debug_draw == False:
            self.image.debug_draw = True
        else:
            self.image.debug_draw = False
    # Allows the player to take a screenshot
    def on_screenshot_clicked(self) -> None:
        filename, _ = pyqt_w.QFileDialog.getSaveFileName(
            self,
            'Save Screenshot',
            '',
            'PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)'
        )
        if not filename:
            return  # user cancelled

        cv.imwrite(filename, self.image.original_image)
