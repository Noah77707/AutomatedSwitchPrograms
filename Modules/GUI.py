import os, sys, subprocess, traceback
from queue import Queue, Empty
from time import sleep, monotonic
from threading import Event

import Constants as const
import cv2 as cv
from .Controller import Controller

import PyQt6.QtWidgets as pyqt_w
import PyQt6.QtCore as pyqt_c
import PyQt6.QtGui as pyqt_g

from .Image_Processing import Image_Processing
from .Database import get_program_totals, format_hms

from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, "media")

MODULE_NAME = "GUI"

image_label_style = "background-color: #000; border: 1px solid #aaa"

class App(pyqt_w.QApplication):
    def __init__(self):
        super().__init__([])
        self.setStyleSheet("QWidget { background-color: #333; }")

class DynamicRow(pyqt_w.QWidget):
    def __init__(self, const_mod, parent=None):
        super().__init__(parent)
        self.const = const_mod

        self._layout = pyqt_w.QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        self._active = None
        self._cfg = {}
        self.setVisible(False)


        self._input_spin: list[pyqt_w.QSpinBox] = []

    def _clear(self):
        while (item := self._layout.takeAt(0)) is not None:
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cfg = {}
        self._active = None
        self._input_spin = []

    @staticmethod
    def parse_level_range(s: str) -> tuple[int, int]:
        s = (s or "").strip()
        if "-" in s:
            a, b = s.split("-", 1)
            return int(a), int(b)
        v = int(s)
        return v, v

    def _build_inputs(self, text: str = "Input"):
        self._layout.addWidget(pyqt_w.QLabel("Inputs:", self))

        self._layout.addWidget(pyqt_w.QLabel(text, self))

        sp = pyqt_w.QSpinBox(self)
        sp.setRange(0, 999999)
        sp.setValue(0)
        sp.valueChanged.connect(self._update_cfg)
        self._input_spin.append(sp)
        self._layout.addWidget(sp)

        self._layout.addStretch(1)
        self._update_cfg()

    def _build_donut(self):
        self._layout.addWidget(pyqt_w.QLabel("Donuts To Make", self))

        sp = pyqt_w.QSpinBox(self)
        sp.setRange(0, 999999)
        sp.setValue(0)
        sp.valueChanged.connect(self._update_cfg)
        self._input_spin.append(sp)
        self._layout.addWidget(sp)

        self._layout.addWidget(pyqt_w.QLabel("Power 1:", self))
        self.donut_power1 = pyqt_w.QComboBox(self)
        self.donut_power1.addItems(const.TEXT["DONUT_POWER_OPTIONS"])
        self._layout.addWidget(self.donut_power1)

        self._layout.addWidget(pyqt_w.QLabel("Level:", self))
        self.donut_lvl1 = pyqt_w.QComboBox(self)
        self.donut_lvl1.addItems(const.TEXT["DONUT_LEVEL_OPTIONS"])
        self._layout.addWidget(self.donut_lvl1)

        self._layout.addSpacing(10)

        self._layout.addWidget(pyqt_w.QLabel("Power 2:", self))
        self.donut_power2 = pyqt_w.QComboBox(self)
        self.donut_power2.addItems(const.TEXT["DONUT_POWER_OPTIONS"])
        self._layout.addWidget(self.donut_power2)

        self._layout.addWidget(pyqt_w.QLabel("Level:", self))
        self.donut_lvl2 = pyqt_w.QComboBox(self)
        self.donut_lvl2.addItems(const.TEXT["DONUT_LEVEL_OPTIONS"])
        self._layout.addWidget(self.donut_lvl2)

        self._layout.addStretch(1)

        self.donut_power1.currentIndexChanged.connect(self._update_cfg)
        self.donut_lvl1.currentIndexChanged.connect(self._update_cfg)
        self.donut_power2.currentIndexChanged.connect(self._update_cfg)
        self.donut_lvl2.currentIndexChanged.connect(self._update_cfg)

        # Defaults must match your exact option strings
        self.donut_power1.setCurrentText("Item Power: Berries")
        self.donut_lvl1.setCurrentText("3")
        self.donut_power2.setCurrentText("Big Haul Power")
        self.donut_lvl2.setCurrentText("3")

        self._update_cfg()

    def _update_cfg(self):
        if self._active == "donut":
            self._cfg = {
                "mode": "donut",
                "power1": self.donut_power1.currentText(),
                "lvl1": self.parse_level_range(self.donut_lvl1.currentText()),
                "power2": self.donut_power2.currentText(),
                "lvl2": self.parse_level_range(self.donut_lvl2.currentText()),
            }
            return

        if self._active == "input":
            self._cfg = {
                "mode": "input",
                "inputs": [int(sp.value()) for sp in self._input_spin],
            }
            return

        self._cfg = {}


    def get_cfg(self) -> dict | None:
        return dict(self._cfg) if self._cfg else None

    def set_program(self, text: str, number: int = 0):
        self._clear()

        if number == 1:
            self.setVisible(True)
            self._active = "input"
            self._build_inputs(text)
            return

        elif number == 2:
            self.setVisible(True)
            self._active = "donut"
            self._build_donut()
            return

        self.setVisible(False)
        self._active = None

class HomeTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number
    
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("HOME programs"))

        self.btn_cct = pyqt_w.QPushButton("Controller Connection Test", self)
        self.btn_cct.setProperty("tracks", [])
        self.btn_cct.clicked.connect(lambda _: self.program_selected.emit("HOME", self.btn_cct, "Connect_Controller_Test", 0))

        self.btn_rht = pyqt_w.QPushButton("Return Home Test", self)
        self.btn_rht.setProperty("tracks", [])
        self.btn_rht.clicked.connect(lambda _: self.program_selected.emit("HOME", self.btn_rht, "Return_Home_Test", 0))

        layout.addWidget(self.btn_cct)
        layout.addWidget(self.btn_rht)
        layout.addStretch(1)

class SWSHTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("SWSH programs"))

        # Static Encounter - Regi
        self.ser = pyqt_w.QPushButton("Static Encounter - Regi", self)
        self.ser.setProperty("tracks", ["pokemon_encountered", "resets", "shinies", "playtime_seconds", "state"])
        self.ser.setProperty("db", ["pokemon_encountered", "resets", "shinies", "playtime_seconds"])
        self.ser.clicked.connect(lambda _: self.program_selected.emit("SWSH", self.ser, "Static_Encounter_SWSH", 0, 0))

        # Static Encounter - Sword of Justice
        self.sej = pyqt_w.QPushButton("Static Encounter - Sword of Justice", self)
        self.sej.setProperty("tracks", ["pokemon_encountered", "resets", "shinies", "playtime_seconds", "state"])
        self.sej.setProperty("db", ["pokemon_encountered", "resets", "shinies", "playtime_seconds"])
        self.sej.clicked.connect(lambda _: self.program_selected.emit("SWSH", self.sej, "Static_Encounter_SWSH", 0, 1))

        layout.addWidget(self.ser)
        layout.addWidget(self.sej)
        layout.addStretch(1)

class BDSPTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("BDSP programs"))
        self.setLayout(layout)

        # static encounter
        self.se = pyqt_w.QPushButton("Static Encounter WIP", self)
        self.se.setProperty("tracks", [])
        self.se.clicked.connect(lambda _: self.program_selected.emit("BDSP", self.se, "Static_Encounter_BDSP", 0, 0))   

        # egg collector
        self.ec = pyqt_w.QPushButton("Egg Collector", self)
        self.ec.setProperty("tracks", ["eggs_collected", "shinies", "playtime_seconds", "state"])
        self.ec.clicked.connect(lambda _: self.program_selected.emit("BDSP", self.ec, "Egg_Collector_BDSP", 1, 0))

        # egg hatcher
        self.eh = pyqt_w.QPushButton("Egg Hatcher", self)
        self.eh.setProperty("tracks", ["eggs_hatched", "shinies", "playtime_seconds", "state"])
        self.eh.clicked.connect(lambda _: self.program_selected.emit("BDSP", self.eh, "Egg_Hatcher_BDSP", 1, 0))

        # automated egg
        self.ae = pyqt_w.QPushButton("Automated Egg Collector/Hatcher/Releaser", self)
        self.ae.setProperty("tracks", ["eggs_collected", "eggs_hatched", "pokemon_released", "shinies", "playtime_seconds", "phase", "state"])
        self.ae.clicked.connect(lambda _: self.program_selected.emit("BDSP", self.ae, "Automated_Egg_BDSP", 1, 0))

        # pokemon releaser
        self.pr = pyqt_w.QPushButton("Pokemon Releaser", self)
        self.pr.setProperty("tracks", ["pokemon_released", "pokemon_skipped", "playtime_seconds", "state"])
        self.pr.clicked.connect(lambda _: self.program_selected.emit("BDSP", self.pr, "Pokemon_Releaser_BDSP", 1, 0))

        layout.addWidget(self.se)
        layout.addWidget(self.ec)
        layout.addWidget(self.eh)
        layout.addWidget(self.ae)
        layout.addWidget(self.pr)
        layout.addStretch(1)

class LATab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("LA programs"))
        self.setLayout(layout)
        
class SVTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("SV programs"))
        self.setLayout(layout)

        # pokemon releaser
        self.pr = pyqt_w.QPushButton("Pokemon Releaser", self)
        self.pr.setProperty("tracks", ["pokemon_released", "pokemon_skipped", "playtime_seconds", "state"])
        self.pr.clicked.connect(lambda _: self.program_selected.emit("SV", self.pr, "Pokemon_Releaser_SV", 0, 0))

        layout.addWidget(self.pr)
        layout.addStretch(1)

class LZATab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("LZA programs"))
        self.setLayout(layout)
        
        # donut maker - sour
        self.dms = pyqt_w.QPushButton("Donut Maker - Sour", self)
        self.dms.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds", "state"])
        self.dms.clicked.connect(lambda _, btn=self.dms: self.program_selected.emit("LZA", btn, "Donut_Checker_Berry", 2, 1))

        # donut maker - sweet
        self.dmw = pyqt_w.QPushButton("Donut Maker - Sweet", self)
        self.dmw.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds", "state"])
        self.dmw.clicked.connect(lambda _, btn=self.dmw: self.program_selected.emit("LZA", btn, "Donut_Checker_Shiny", 2, 2))
        
        layout.addWidget(self.dms)
        layout.addWidget(self.dmw)
        layout.addStretch(1)
        
class GUI(pyqt_w.QWidget):
    def __init__(
        self,
        Image_queue: Queue,
        Command_queue: Queue,
        shutdown_event: Event,
        image: Image_Processing,
    ) -> None:
        super().__init__()

        self.Image_queue = Image_queue
        self.Command_queue = Command_queue
        self.image = image

        self.game = ""
        self.program = ""
        self.state = ""
        self.tracks: list[str] = []
        self.numberinput = 0
        self.userprofile = 1
        self.debug = False
        self.running = False
        self.paused = False
        self.run_seconds = 0.0
        self.run_last_t = None

        self.stats_timer = pyqt_c.QTimer(self)
        self.stats_timer.timeout.connect(self.stat_timer)
        self.stats_timer.start(1000)

        self.setWindowTitle("Auto Switch Programs")
        main_layout = pyqt_w.QHBoxLayout(self)

        self.latest_frame = None
        self.region_radius = 5

        self.items = {
            "switch_capture_label": pyqt_w.QLabel(self),
            "start_stop_button": pyqt_w.QPushButton(self),
            "current_state_label": pyqt_w.QLabel(self),
            "stats_label": pyqt_w.QLabel(self),
        }

        self.items["switch_capture_label"].setFixedSize(*const.MAIN_FRAME_SIZE)
        self.items["switch_capture_label"].setStyleSheet(image_label_style)
        self.items["switch_capture_label"].setAttribute(
            pyqt_c.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self.tabs = pyqt_w.QTabWidget()
        self.tabs.setTabPosition(pyqt_w.QTabWidget.TabPosition.West)
        self.tabs.setMovable(True)

        # ---------- Tabs ----------
        home_tab = HomeTab(self)
        home_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(home_tab, "HOME")

        swsh_tab = SWSHTab(self)
        swsh_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(swsh_tab, "SWSH")

        bdsp_tab = BDSPTab(self)
        bdsp_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(bdsp_tab, "BDSP")

        la_tab = LATab(self)
        la_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(la_tab, "LA")

        sv_tab = SVTab(self)
        sv_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(sv_tab, "SV")

        lza_tab = LZATab(self)
        lza_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(lza_tab, "LZA")

        self.current_program_name = self.tabs.tabText(self.tabs.currentIndex())
        self.current_process = None
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # ---------- LEFT PANEL ----------
        left_panel = pyqt_w.QVBoxLayout()
        left_panel.addWidget(self.tabs)

        # ---------- RIGHT PANEL ----------
        right_panel = pyqt_w.QVBoxLayout()
        right_panel.addWidget(self.items["switch_capture_label"])

        info_row = pyqt_w.QHBoxLayout()
        info_row.addWidget(self.items["stats_label"])
        self.items["stats_label"].setText(self.update_stats())
        self.items["stats_label"].setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)

        self.debug_button = pyqt_w.QPushButton("Draw Debug", self)
        self.debug_button.clicked.connect(self.update_debug)

        self.screenshot_button = pyqt_w.QPushButton("Save Screenshot", self)
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)

        self.start_button = pyqt_w.QPushButton("Start Program", self)
        self.start_button.clicked.connect(self.start_scripts)

        self.pause_button = pyqt_w.QPushButton("Pause Program", self)
        self.pause_button.clicked.connect(self.pause_scripts)

        self.stop_button = pyqt_w.QPushButton("Stop Program", self)
        self.stop_button.clicked.connect(self.stop_scripts)

        button_row_debug = pyqt_w.QHBoxLayout()
        button_row_debug.addWidget(self.debug_button)
        button_row_debug.addWidget(self.screenshot_button)

        button_row_program = pyqt_w.QHBoxLayout()
        button_row_program.addWidget(self.start_button)
        button_row_program.addWidget(self.pause_button)
        button_row_program.addWidget(self.stop_button)


        # Dynamic extras row
        self.dynamic_row = DynamicRow(const, self)

        right_panel.addLayout(info_row)
        right_panel.addWidget(self.dynamic_row)
        right_panel.addLayout(button_row_program)
        right_panel.addLayout(button_row_debug)
        right_panel.addStretch(1)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 0)

        self.timer = pyqt_c.QTimer(self)
        self.timer.timeout.connect(lambda: self.update_GUI(shutdown_event))
        self.timer.start(33)

        self.show()

    def update_GUI(self, shutdown_event: Event) -> None:
        try:
            if shutdown_event.is_set():
                self.close()
                return

            frame = getattr(self.image, "original_image", None)
            if frame is None:
                return

            fid = getattr(self.image, "frame_id", None)
            if not hasattr(self, "_last_gui_frame_id"):
                self._last_gui_frame_id = -1
            if fid is not None and fid == self._last_gui_frame_id:
                return
            if fid is not None:
                self._last_gui_frame_id = fid

            frame_to_show = frame
            if getattr(self.image, "debug", False):
                frame_to_show = self.image.draw_debug(frame.copy())

            frame_rgb = cv.cvtColor(frame_to_show, cv.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            qimg = pyqt_g.QImage(frame_rgb.data, w, h, bytes_per_line, pyqt_g.QImage.Format.Format_RGB888)
            pix = pyqt_g.QPixmap.fromImage(qimg)

            if (self.items["switch_capture_label"].width(), self.items["switch_capture_label"].height()) != (w, h):
                pix = pix.scaled(
                    self.items["switch_capture_label"].width(),
                    self.items["switch_capture_label"].height(),
                    pyqt_c.Qt.AspectRatioMode.KeepAspectRatio,
                    pyqt_c.Qt.TransformationMode.FastTransformation,
                )
            self.items["switch_capture_label"].setPixmap(pix)
        except Exception:
            traceback.print_exc()

    def update_stats(self):
        s = getattr(self.image, "database_component", None)
        if not s:
            return ""

        db = get_program_totals(str(self.game), str(self.program)) or {}
        parts = []
        parts.append(f"program: {self.program}")

        for key in self.tracks:
            val = getattr(s, key, 0)
            db_val = db.get(key, 0)

            if key == "playtime_seconds":
                parts.append(f"run time: {format_hms(int(val))}")
                parts.append(f"total_time: {format_hms(int(db_val + val))}")
            elif key == "phase":
                parts.append(f"phase: {getattr(self.image, 'phase', None)}")
            elif key == "state":
                parts.append(f"state: {getattr(self.image, 'state', None)}")
            else:
                parts.append(f"{key}: {val} (total {db_val})")

        return " | ".join(parts)

    def stat_timer(self):
        try:
            if self.running and not self.paused:
                now = monotonic()
                if self.run_last_t is None:
                    self.run_last_t = now
                else:
                    dt = now - self.run_last_t
                    self.run_last_t = now
                    if dt > 0:
                        self.run_seconds += dt
                        whole = int(self.run_seconds)
                        if whole > 0:
                            self.run_seconds -= whole
                            database = getattr(self.image, "database_component", None)
                            if database is not None:
                                database.playtime_seconds += whole

            self.items["stats_label"].setText(self.update_stats())
        except Exception:
            traceback.print_exc()

    def on_tab_changed(self, index: int) -> None:
        self.current_program_name = self.tabs.tabText(index)
        self.Command_queue.put({"type": "SET_GAME", "game": self.current_program_name})

    def update_script(
        self,
        game: str,
        btn: pyqt_w.QPushButton,
        program: str,
        temp_row_usage: int = 0,
        number: int = 0,
        text: str = "Input",
        _: bool = False,
    ) -> None:
        self.game = game
        self.program = program
        self.tracks = btn.property("tracks") or []
        self.temp_row_usage = temp_row_usage
        self.numberinput = int(number)

        self.dynamic_row.set_program(text=text, number=self.temp_row_usage)
        self.image.donut_cfg = self.dynamic_row.get_cfg()

    def start_scripts(self) -> None:
        extras = self.dynamic_row.get_cfg()  # may be None
        self.image.donut_cfg = extras if extras and extras.get("mode") == "donut" else None

        input_value = 0
        if extras and extras.get("mode") == "input":
            input_value = int(extras.get("value", 0))


        self.Command_queue.put(
            {
                "cmd": "SET_PROGRAM",
                "game": self.game,
                "program": self.program,
                "number": self.numberinput,
                "running": True,
                "runs": input_value,
            }
        )
        self.running = True
        self.paused = False
        self.run_last_t = monotonic()
        self.run_seconds = 0.0

    def pause_scripts(self) -> None:
        if not self.running:
            return

        if not self.paused:
            self.Command_queue.put({"cmd": "PAUSE"})
            self.paused = True
            self.run_last_t = None
            self.pause_button.setText("Resume Program")
        else:
            self.Command_queue.put({"cmd": "RESUME"})
            self.paused = False
            self.run_last_t = monotonic()
            self.pause_button.setText("Pause Program")

    def stop_scripts(self) -> None:
        self.Command_queue.put({"cmd": "STOP"})
        self.running = False
        self.paused = False
        self.run_last_t = None
        self.run_seconds = 0.0

    def update_debug(self) -> None:
        if self.image.debug is False:
            self.image.debug = True
            self.debug_button.setText("Remove Debug")
        else:
            self.image.debug = False
            self.debug_button.setText("Draw Debug")

    def on_screenshot_clicked(self) -> None:
        filename = pyqt_w.QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)",
        )
        if not filename:
            return
        cv.imwrite(filename, self.image.original_image)
