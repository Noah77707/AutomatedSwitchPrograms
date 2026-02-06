import os, sys, subprocess, traceback
from queue import Queue, Empty
from time import sleep, monotonic
from threading import Event
from serial.tools import list_ports

import Constants as const
import cv2 as cv
from .Controller import Controller

import PyQt6.QtWidgets as pyqt_w
import PyQt6.QtCore as pyqt_c
import PyQt6.QtGui as pyqt_g

from .Image_Processing import Image_Processing
from .Database import get_program_totals, format_hms

from Programs.TEST_Scripts import *
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
        self.setStyleSheet("""
QWidget { 
    background-color: #333;
}
QPushButton {
    background-color: #333;
    color: white;
    border: 1px solid #666;
    padding: 6px;
}
QPushButton:checked {
    background-color: #2b2b2b;
    border: 1px solid #aaa;
}
QPushButton:hover {
    background-color: #555;
}

""")

class DynamicRow(pyqt_w.QWidget):
    def __init__(self, const_mod, parent=None):
        super().__init__(parent)
        self.const = const_mod

        self._layout = pyqt_w.QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        self._active: str | None = None
        self._cfg: dict = {}
        self.setVisible(False)

        self._input_spin: list[pyqt_w.QSpinBox] = []

        # holders created per-mode
        self._donut_count: pyqt_w.QSpinBox | None = None
        self._fossil_count: pyqt_w.QSpinBox | None = None

    def _clear(self):
        while (item := self._layout.takeAt(0)) is not None:
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cfg = {}
        self._active = None
        self._input_spin = []
        self._donut_count = None
        self._fossil_count = None

    @staticmethod
    def parse_level_range(s: str) -> tuple[int, int]:
        s = (s or "").strip()
        if "-" in s:
            a, b = s.split("-", 1)
            return int(a), int(b)
        v = int(s) if s else 0
        return v, v

    def _make_spin(self, *, minimum=0, maximum=999999, value=0) -> pyqt_w.QSpinBox:
        sp = pyqt_w.QSpinBox(self)
        sp.setRange(int(minimum), int(maximum))
        sp.setValue(int(value))
        sp.valueChanged.connect(self._update_cfg)
        return sp

    def _build_inputs(self, text: Sequence[str] = ("Input",), count: int = 1):
        count = max(1, int(count))
        
        base = (text[0] if text else "Input")

        for i in range(count):
            if len(text) >= count:
                label_text = text[i]
                
            elif count > 1:
                label_text = f"{base} {i + 1}"
            else:
                label_text = base
                
            self._layout.addWidget(pyqt_w.QLabel(label_text, self))

            sp = self._make_spin(minimum=1, maximum=999999, value=1)
            self._input_spin.append(sp)
            self._layout.addWidget(sp)

        self._layout.addStretch(1)
        self._update_cfg()

    def _build_donut(self, flavor:str = "Sour"):
        opts = (const.TEXT.get("DONUT_POWER_OPTIONS") or {})
        powers = opts.get(flavor) or []

        if not powers:
            powers = ["(no powers configured)"]

        self._layout.addWidget(pyqt_w.QLabel("Donuts To Make:", self))
        self._donut_count = self._make_spin(minimum=1, maximum=999999, value=0)
        self._layout.addWidget(self._donut_count)

        self._layout.addWidget(pyqt_w.QLabel("Power 1:", self))
        self.donut_power1 = pyqt_w.QComboBox(self)
        self.donut_power1.addItems(powers)
        self._layout.addWidget(self.donut_power1)

        self._layout.addWidget(pyqt_w.QLabel("Level:", self))
        self.donut_lvl1 = pyqt_w.QComboBox(self)
        self.donut_lvl1.addItems(const.TEXT["DONUT_LEVEL_OPTIONS"])
        self._layout.addWidget(self.donut_lvl1)

        self._layout.addSpacing(10)

        self._layout.addWidget(pyqt_w.QLabel("Power 2:", self))
        self.donut_power2 = pyqt_w.QComboBox(self)
        self.donut_power2.addItems(powers)
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

        # Defaults must match exact option strings
        self.donut_power1.setCurrentText("Item Power: Berries")
        self.donut_lvl1.setCurrentText("3")
        self.donut_power2.setCurrentText("Big Haul Power")
        self.donut_lvl2.setCurrentText("3")

        self._update_cfg()

    def _build_fossil_swsh(self):
        c = self.const

        self._layout.addWidget(pyqt_w.QLabel("Fossils To Revive:", self))
        self._fossil_count = self._make_spin(minimum=1, maximum=999999, value=1)
        self._layout.addWidget(self._fossil_count)

        self._layout.addWidget(pyqt_w.QLabel("Fossil 1:", self))
        self.fossil1 = pyqt_w.QComboBox(self)
        self.fossil1.addItems(c.TEXT["FOSSILS_SWSH"]["FOSSIL1"])
        self._layout.addWidget(self.fossil1)

        self._layout.addWidget(pyqt_w.QLabel("Fossil 2:", self))
        self.fossil2 = pyqt_w.QComboBox(self)
        self.fossil2.addItems(c.TEXT["FOSSILS_SWSH"]["FOSSIL2"])
        self._layout.addWidget(self.fossil2)

        self._layout.addStretch(1)

        self.fossil1.currentIndexChanged.connect(self._update_cfg)
        self.fossil2.currentIndexChanged.connect(self._update_cfg)

        self._update_cfg()

    def _update_cfg(self):
        if self._active == "donut":
            self._cfg = {
                "mode": "donut",
                "flavor": getattr(self, '_donut_flavor', "Sour"),
                "count": int(self._donut_count.value()) if self._donut_count else 0,
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

        if self._active == "fossil_swsh":
            self._cfg = {
                "mode": "fossil_swsh",
                "count": int(self._fossil_count.value()) if self._fossil_count else 0,
                "fossil1": self.fossil1.currentText(),
                "fossil2": self.fossil2.currentText(),
            }
            return

        self._cfg = {}

    def get_cfg(self) -> dict | None:
        return dict(self._cfg) if self._cfg else None

    def set_program(self, text: tuple, number: int = 0, input_count: int = 1):
        """
        number:
          0 = none
          1 = generic input row (spinboxes)
          100 = donut row
          101 = fossil swsh row
        """
        self._clear()

        if number >= 1 and number < 100:
            self.setVisible(True)
            self._active = "input"
            self._build_inputs(text, count=number)
            return

        if number == 100:
            self.setVisible(True)
            self._active = "donut"
            self._build_donut(text)
            return

        if number == 101:
            self.setVisible(True)
            self._active = "fossil_swsh"
            self._build_fossil_swsh()
            return

        self.setVisible(False)
        self._active = None

class TESTTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("Test programs"))

        self.btn_ar = pyqt_w.QPushButton("Push A Repeatedly")
        self.btn_ar.setProperty("tracks", ['actions', "playtime_seconds"])
        self.btn_ar.clicked.connect(lambda _: self.program_selected.emit("TEST", self.btn_ar, "Press_A_Repeatadly", 0, 0))

        self.btn_cct = pyqt_w.QPushButton("Controller Connection Test", self)
        self.btn_cct.setProperty("tracks", [])
        self.btn_cct.clicked.connect(lambda _: self.program_selected.emit("TEST", self.btn_cct, "Connect_Controller_Test", 0, 0))

        self.btn_rht = pyqt_w.QPushButton("Return Home Test", self)
        self.btn_rht.setProperty("tracks", [])
        self.btn_rht.clicked.connect(lambda _: self.program_selected.emit("TEST", self.btn_rht, "Return_Home_Test", 0, 0))

        layout.addWidget(self.btn_cct)
        layout.addWidget(self.btn_rht)
        layout.addWidget(self.btn_ar)
        layout.addStretch(1)

class HOMETab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int, tuple)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("Home programs"))
        
        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        self.sh = pyqt_w.QPushButton("Home Sorter", self)
        self.sh.setCheckable(True)
        self.group.addButton(self.sh)
        self.sh.setProperty("tracks", [])
        self.sh.clicked.connect(lambda _:
                                (self._set_program_info("Sort_Home"),
                                  self.program_selected.emit("HOME", self.sh, "Sort_Home", 3, 0, ("First Box", "First Box to Sort", "Last Box to Sort"))))
                
        self.rb = pyqt_w.QPushButton("Home Sorter", self)
        self.rb.setCheckable(True)
        self.group.addButton(self.rb)
        self.rb.setProperty("tracks", [])
        self.rb.clicked.connect(lambda _:
                                (self._set_program_info("Rename_Boxes"),
                                  self.program_selected.emit("HOME", self.rb, "Rename_Boxes", 3, 0, ("First Box", "First Box to Sort", "Last Box to Sort"))))
        
        self.sspt = pyqt_w.QPushButton("Sort_Specific_Pokemon_Types", self)
        self.sspt.setCheckable(True)
        self.group.addButton(self.sspt)
        self.sspt.setProperty("tracks", [])
        self.sspt.clicked.connect(lambda _:
                                (self._set_program_info("Sort_Specific_Pokemon_Types"),
                                  self.program_selected.emit("HOME", self.sspt, "Sort_Specific_Pokemon_Types", 3, 0, ("First Box", "First Box to Sort", "Last Box to Sort"))))

        layout.addWidget(self.sh)
        layout.addWidget(self.rb)
        layout.addWidget(self.sspt)
        layout.addStretch(1)

        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)

class SWSHTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int, tuple)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("SWSH programs"))

        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        # Static Encounter - Regi
        self.ser = pyqt_w.QPushButton("Static Encounter - Regi", self)
        self.ser.setCheckable(True)
        self.group.addButton(self.ser)
        self.ser.setProperty("tracks", ["pokemon_encountered", "resets", "shinies", "playtime_seconds"])
        self.ser.clicked.connect(lambda _:
                                 (self._set_program_info("Static_Encounter_SWSH"),
                                 self.program_selected.emit("SWSH", self.ser, "Static_Encounter_SWSH", 0, 0, ("",))))

        # Static Encounter - Sword of Justice
        self.sej = pyqt_w.QPushButton("Static Encounter - Sword of Justice", self)
        self.sej.setCheckable(True)
        self.group.addButton(self.sej)
        self.sej.setProperty("tracks", ["pokemon_encountered", "resets", "shinies", "playtime_seconds"])
        self.sej.clicked.connect(lambda _:
                                (self._set_program_info("Static_Encounter_SWSH"),
                                self.program_selected.emit("SWSH", self.sej, "Static_Encounter_SWSH", 0, 1, ("",))))

        self.fr = pyqt_w.QPushButton("Fossil Reviver", self)
        self.fr.setCheckable(True)
        self.group.addButton(self.fr)
        self.fr.setProperty("tracks", ["actions", "resets", "shinies", "playtime_seconds"])
        self.fr.clicked.connect(lambda _:
                                (self._set_program_info("Fossil_Reviver_SWSH"),
                                 self.program_selected.emit("SWSH", self.fr, "Fossil_Reviver_SWSH", 101, 0, ("",))))
        
        self.ec = pyqt_w.QPushButton("Egg Collector WIP", self)
        self.ec.setCheckable(True)
        self.group.addButton(self.ec)
        self.ec.setProperty("tracks", ["eggs_collected", "playtime_seconds"])
        self.ec.clicked.connect(lambda _:
                                (self._set_program_info("Static_Encounter_SWSH"),
                                  self.program_selected.emit("BDSP", self.ec, "Egg_Collector_SWSH", 1, 0, ("Number of eggs",))))

        self.eh = pyqt_w.QPushButton("Egg Hatcher WIP", self)
        self.eh.setCheckable(True)
        self.group.addButton(self.eh)
        self.eh.setProperty("tracks", ["eggs_hatched", "shinies", "playtime_seconds"])
        self.eh.setProperty("db", ["eggs_hatched", "shinies", "playtime_seconds"])
        self.eh.clicked.connect(lambda _:
                                (self._set_program_info("Egg_Hatcher_SWSH"),
                                  self.program_selected.emit("BDSP", self.eh, "Egg_Hatcher_SWSH", 1, 0, ("Number of eggs:",))))

        self.r = pyqt_w.QPushButton("Pokemon Releaser", self)
        self.r.setCheckable(True)
        self.group.addButton(self.r)
        self.r.setProperty("tracks", ["pokemon_released", "pokemon_skipped", "playtime_seconds"])
        self.r.clicked.connect(lambda _:
                               (self._set_program_info("Pokemon_Releaser_SWSH"),
                               self.program_selected.emit("SWSH", self.r, "Pokemon_Releaser_SWSH", 1, 0, ("Boxes of pokemon",))))

        layout.addWidget(self.ser)
        layout.addWidget(self.sej)
        layout.addWidget(self.fr)
        layout.addWidget(self.ec)
        layout.addWidget(self.eh)
        layout.addWidget(self.r)
        layout.addStretch(1)

        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)
        
class BDSPTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int, tuple)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("BDSP programs"))
        self.setLayout(layout)

        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        # static encounter
        self.se = pyqt_w.QPushButton("Static Encounter WIP", self)
        self.se.setCheckable(True)
        self.group.addButton(self.se)
        self.se.setProperty("tracks", [])
        self.se.clicked.connect(lambda _:
                                (self._set_program_info("Static_Encounter_BDSP"),
                                  self.program_selected.emit("BDSP", self.se, "Static_Encounter_BDSP", 0, 0, ("",))))

        # egg collector
        self.ec = pyqt_w.QPushButton("Egg Collector", self)
        self.ec.setCheckable(True)
        self.group.addButton(self.ec)
        self.ec.setProperty("tracks", ["eggs_collected", "playtime_seconds"])
        self.ec.clicked.connect(lambda _:
                                (self._set_program_info("Static_Encounter_BDSP"),
                                  self.program_selected.emit("BDSP", self.ec, "Egg_Collector_BDSP", 1, 0, ("Number of eggs",))))

        # egg hatcher
        self.eh = pyqt_w.QPushButton("Egg Hatcher", self)
        self.eh.setCheckable(True)
        self.group.addButton(self.eh)
        self.eh.setProperty("tracks", ["eggs_hatched", "shinies", "playtime_seconds"])
        self.eh.setProperty("db", ["eggs_hatched", "shinies", "playtime_seconds"])
        self.eh.clicked.connect(lambda _:
                                (self._set_program_info("Egg_Hatcher_BDSP"),
                                  self.program_selected.emit("BDSP", self.eh, "Egg_Hatcher_BDSP", 1, 0, ("Number of eggs:",))))

        # automated egg
        self.ae = pyqt_w.QPushButton("Automated Egg Collector/Hatcher/Releaser", self)
        self.ae.setCheckable(True)
        self.group.addButton(self.ae)
        self.ae.setProperty("tracks", ["eggs_collected", "eggs_hatched", "pokemon_released", "shinies", "playtime_seconds", "phase"])
        self.ae.clicked.connect(lambda _:
                                (self._set_program_info("Automated_Egg_BDSP"),
                                  self.program_selected.emit("BDSP", self.ae, "Automated_Egg_BDSP", 1, 0, ("Number of eggs",))))

        # pokemon releaser
        self.pr = pyqt_w.QPushButton("Pokemon Releaser", self)
        self.pr.setCheckable(True)
        self.group.addButton(self.pr)
        self.pr.setProperty("tracks", ["pokemon_released", "pokemon_skipped", "playtime_seconds"])
        self.pr.clicked.connect(lambda _:
                                (self._set_program_info("Pokemon_Releaser_BDSP"),
                                  self.program_selected.emit("BDSP", self.pr, "Pokemon_Releaser_BDSP", 1, 0, ("Boxes of pokemon",))))

        layout.addWidget(self.se)
        layout.addWidget(self.ec)
        layout.addWidget(self.eh)
        layout.addWidget(self.ae)
        layout.addWidget(self.pr)
        layout.addStretch(1)

        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)

class LATab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("LA programs"))
        self.setLayout(layout)

        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        
        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)
        
class SVTab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int, tuple)  # game, btn, program, temp_row, number
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("SV programs"))
        self.setLayout(layout)

        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        # pokemon releaser
        self.pr = pyqt_w.QPushButton("Pokemon Releaser", self)
        self.pr.setCheckable(True)
        self.group.addButton(self.pr)
        self.pr.setProperty("tracks", ["pokemon_released", "pokemon_skipped", "playtime_seconds"])
        self.pr.clicked.connect(lambda _:
                                (self._set_program_info("Pokemon_Releaser_SV"),
                                 self.program_selected.emit("SV", self.pr, "Pokemon_Releaser_SV", 1, 0, ("",))))

        layout.addWidget(self.pr)
        layout.addStretch(1)

        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)

class LZATab(pyqt_w.QWidget):
    program_selected = pyqt_c.pyqtSignal(str, object, str, int, int, tuple)  # game, btn, program, temp_row, number, flavor
    
    def _set_program_info(self, program: str):
        text, img = ProgramInfo.get(program)
        self.info_text.setText(text)

        if img and img != "N/A":
            pix = pyqt_g.QPixmap(img)
            self.info_img.setPixmap(pix if not pix.isNull() else pyqt_g.QPixmap())
        else:
            self.info_img.clear()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = pyqt_w.QVBoxLayout(self)
        layout.addWidget(pyqt_w.QLabel("LZA programs"))
        self.setLayout(layout)
        
        self.group = pyqt_w.QButtonGroup(self)
        self.group.setExclusive(True)

        # donut maker - sour
        self.dmsour = pyqt_w.QPushButton("Donut Maker - Sour", self)
        self.dmsour.setCheckable(True)
        self.group.addButton(self.dmsour)
        self.dmsour.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds"])
        self.dmsour.clicked.connect(lambda _:
                                 (self._set_program_info("Donut_Checker"),
                                  self.program_selected.emit("LZA", self.dmsour, "Donut_Checker", 100, 1, ("Sour",))))

        # donut maker - sweet
        self.dmsweet = pyqt_w.QPushButton("Donut Maker - Sweet", self)
        self.dmsweet.setCheckable(True)
        self.group.addButton(self.dmsweet)
        self.dmsweet.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds"])
        self.dmsweet.clicked.connect(lambda _:
                                 (self._set_program_info("Donut_Checker"),
                                  self.program_selected.emit("LZA", self.dmsweet, "Donut_Checker", 100, 2, ("Sweet",))))
        
        # donut maker - spicy
        self.dmspicy = pyqt_w.QPushButton("Donut Maker - Spicy", self)
        self.dmspicy.setCheckable(True)
        self.group.addButton(self.dmspicy)
        self.dmspicy.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds"])
        self.dmspicy.clicked.connect(lambda _:
                                 (self._set_program_info("Donut_Checker"),
                                  self.program_selected.emit("LZA", self.dmspicy, "Donut_Checker", 100, 3, ("Spicy",))))
        # donut maker - bitter
        self.dmbitter = pyqt_w.QPushButton("Donut Maker - Bitter", self)
        self.dmbitter.setCheckable(True)
        self.group.addButton(self.dmbitter)
        self.dmbitter.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds"])
        self.dmbitter.clicked.connect(lambda _:
                                 (self._set_program_info("Donut_Checker"),
                                  self.program_selected.emit("LZA", self.dmbitter, "Donut_Checker", 100, 4, ("Bitter",))))

        # donut maker - fresh
        self.dmfresh = pyqt_w.QPushButton("Donut Maker - Fresh", self)
        self.dmfresh.setCheckable(True)
        self.group.addButton(self.dmfresh)
        self.dmfresh.setProperty("tracks", ["actions", "action_hits", "resets", "playtime_seconds"])
        self.dmfresh.clicked.connect(lambda _:
                                 (self._set_program_info("Donut_Checker"),
                                  self.program_selected.emit("LZA", self.dmfresh, "Donut_Checker", 100, 5, ("Fresh",))))


        layout.addWidget(self.dmsour)
        layout.addWidget(self.dmsweet)
        layout.addWidget(self.dmspicy)
        layout.addWidget(self.dmbitter)
        layout.addWidget(self.dmfresh)
        layout.addStretch(1)

        self.info_img = pyqt_w.QLabel(self)
        self.info_img.setFixedHeight(140)
        self.info_img.setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        self.info_img.setScaledContents(True)

        self.info_text = pyqt_w.QLabel(self)
        self.info_text.setWordWrap(True)

        layout.addWidget(self.info_img)
        layout.addWidget(self.info_text)

class ProgramInfo(pyqt_w.QWidget):
    def get(program: str) -> tuple[str, str]:
        info = const.TEXT.get("PROGRAM_DESCRIPTIONS", {}).get(program, {})
        text = info.get("text")
        image = info.get("image")
        return text, image

class GUI(pyqt_w.QWidget):
    def __init__(
        self,
        Command_queue: Queue,
        shutdown_event: Event,
        image: Image_Processing,
    ) -> None:
        super().__init__()

        self.Command_queue = Command_queue
        self.image = image
        self.shutdown_event = shutdown_event
        self.settings = pyqt_c.QSettings("YourApp", "AutoSwitchPrograms")

        self.game = ""
        self.program = ""
        self.state = ""
        self.tracks: list[str] = []
        self.numberinput = 0
        self.userprofile = 1
        self.debug = False
        self.run = Running()
        
        self._last_video_frame_id = -1
        self._last_ui_frame_id = -1
        self._last_label_size = None
        self._db_totals_cache = {}
        self._db_totals_t = 0.0
        self._keep_rgb = None  # keeps numpy rgb alive for QImage safety
        self._keep_qimg = None

        self.setWindowTitle("Auto Switch Programs")
        main_layout = pyqt_w.QHBoxLayout(self)

        self.items = {
            "switch_capture_label": pyqt_w.QLabel(self),
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
        test_tab = TESTTab(self)
        test_tab.program_selected.connect(self.update_script)
        self.tabs.addTab(test_tab, "TEST")
        
        home_tab = HOMETab(self)
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

        # ---------- CAPTURE CARD AND MCU ----------
        self.capture_index = pyqt_w.QSpinBox(self)
        self.capture_index.setRange(0, 20)
        self.capture_index.setValue(int(self.settings.value("capture_index", 0)))
        saved_idx = self.settings.value("capture_index", 0)
        try:
            saved_idx = int(saved_idx)
        except Exception:
            saved_idx = 0
        self.capture_index.setValue(saved_idx)

        self.capture_test = pyqt_w.QPushButton("Test Capture", self)
        self.capture_test.clicked.connect(self._test_capture)

        self.mcu_port = pyqt_w.QComboBox(self)

        saved_port = self.settings.value("mcu_port", "")
        if saved_port:
            i = self.mcu_port.findData(saved_port)
            if i >= 0:
                self.mcu_port.setCurrentIndex(i)

        self.mcu_refresh = pyqt_w.QPushButton("Refresh", self)
        self.mcu_refresh.clicked.connect(self._refresh_ports)

        self.capture_index.valueChanged.connect(
            lambda v: self.settings.setValue("capture_index", int(v))
        )

        self.mcu_port.currentIndexChanged.connect(
            lambda _: self.settings.setValue("mcu_port", self.mcu_port.currentData() or "")
        )

        self._refresh_ports()

        # ---------- PROGRAM BUTTONS ----------
        self.debug_button = pyqt_w.QPushButton("Debug On", self)
        self.debug_button.clicked.connect(self.update_debug)
        
        self.screenshot_button = pyqt_w.QPushButton("Save Screenshot", self)
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)

        self.start_button = pyqt_w.QPushButton("Start Program", self)
        self.start_button.clicked.connect(self.start_scripts)

        self.pause_button = pyqt_w.QPushButton("Pause Program", self)
        self.pause_button.clicked.connect(self.pause_scripts)

        self.stop_button = pyqt_w.QPushButton("Stop Program", self)
        self.stop_button.clicked.connect(self.stop_scripts)

        # ---------- ROWS ----------
        port_row = pyqt_w.QHBoxLayout()
        port_row.addWidget(pyqt_w.QLabel("Capture card Index:", self))
        port_row.addWidget(self.capture_index)
        port_row.addWidget(self.capture_test)
        port_row.addWidget(pyqt_w.QLabel("Micro Controller Port:", self))
        port_row.addWidget(self.mcu_port)
        port_row.addWidget(self.mcu_refresh)

        info_row = pyqt_w.QHBoxLayout()
        info_row.addWidget(self.items["current_state_label"])
        self.items["current_state_label"].setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)
        
        info2_row = pyqt_w.QHBoxLayout()
        info2_row.addWidget(self.items["stats_label"])
        self.items["stats_label"].setText(self.update_stats())
        self.items["stats_label"].setAlignment(pyqt_c.Qt.AlignmentFlag.AlignCenter)

        button_row_debug = pyqt_w.QHBoxLayout()
        button_row_debug.addWidget(self.debug_button)
        button_row_debug.addWidget(self.screenshot_button)

        button_row_program = pyqt_w.QHBoxLayout()
        button_row_program.addWidget(self.start_button)
        button_row_program.addWidget(self.pause_button)
        button_row_program.addWidget(self.stop_button)

        # Dynamic extras row
        self.dynamic_row = DynamicRow(const, self)

        right_panel.addLayout(port_row)
        right_panel.addWidget(self.items["switch_capture_label"])
        right_panel.addLayout(info_row)
        right_panel.addLayout(info2_row)
        right_panel.addWidget(self.dynamic_row)
        right_panel.addLayout(button_row_program)
        right_panel.addLayout(button_row_debug)
        right_panel.addStretch(1)

        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 0)

        self.ui_timer = pyqt_c.QTimer(self)
        self.ui_timer.timeout.connect(self.update_GUI)
        self.ui_timer.timeout.connect(self.stat_timer)
        self.ui_timer.start(100)

        self.video_timer = pyqt_c.QTimer(self)
        self.video_timer.timeout.connect(self.update_video)
        self.video_timer.start(33)

        # ---------- CAPTURE CARD AND MCU UPDATE ----------
        pyqt_c.QTimer.singleShot(0, lambda: self.Command_queue.put({
            "cmd": "SET_DEVICES",
            "capture_index": int(self.capture_index.value()),
            "mcu_port": self.mcu_port.currentData() or "",
        }))
        pyqt_c.QTimer.singleShot(0, self._apply_devices)

        self.show()

    def update_GUI(self) -> None:
        try:
            if self.shutdown_event.is_set():
                self.ui_timer.stop()
                self.close()
                return

            if self.run.running and getattr(self.image, "state", None) == "PROGRAM_FINISHED":
                self.stop_scripts()
                return
            
            # GUI-only updates. No cvtColor. No pixmaps. No frame operations.
            rs = getattr(self.image, "database_component", None)
            if rs is not None:
                self.items["stats_label"].setText(self.update_stats())
            
            if self.program != "":
                self.items["current_state_label"].setText(
                    f"Game: {self.game} | Program: {self.program} | state: {getattr(self.image, 'state', None)}"
                )

            rs = getattr(self.image, "database_component", None)
            if rs is not None:
                self.items["stats_label"].setText(self.update_stats())
                        
        except Exception:
            traceback.print_exc()

    def update_video(self) -> None:
        try:
            if self.shutdown_event.is_set():
                self.video_timer.stop()
                return

            img = self.image
            if img is None:
                return

            with img._lock:
                fid = int(getattr(img, "frame_id", 0))
                frame = getattr(img, "original_image", None)
                cur_state = getattr(img, "state", None)

            if frame is None:
                return

            if not hasattr(self, "_last_video_state"):
               self._last_video_state = cur_state
               
            if fid == self._last_video_frame_id and cur_state == self._last_video_state:
                return

            self._last_video_frame_id = fid
            self._last_video_state = cur_state

            dbg = getattr(img, "debugger", None)
            if dbg is not None and dbg.enabled and dbg._state == cur_state:
                frame_to_show = dbg.draw(frame.copy(), getattr(img, "state", None))
            else:
                img.debugger.clear()
                frame_to_show = frame

            h, w, ch = frame_to_show.shape

            # Avoid cvtColor: use BGR directly
            self._keep_rgb = frame_to_show  # keep buffer alive

            bytes_per_line = ch * w
            qimg = pyqt_g.QImage(
                frame_to_show.data,
                w,
                h,
                bytes_per_line,
                pyqt_g.QImage.Format.Format_BGR888,
            )

            pix = pyqt_g.QPixmap.fromImage(qimg)

            label = self.items.get("switch_capture_label")
            if label is None:
                return

            # Scaling is expensive. If you can, make capture w/h match label to avoid this.
            if (label.width(), label.height()) != (w, h):
                pix = pix.scaled(
                    label.width(),
                    label.height(),
                    pyqt_c.Qt.AspectRatioMode.KeepAspectRatio,
                    pyqt_c.Qt.TransformationMode.FastTransformation,
                )

            label.setPixmap(pix)

        except Exception:
            traceback.print_exc()

    def update_stats(self):
        s = getattr(self.image, "database_component", None)
        if not s:
            return ""
        
        now = monotonic()
        if now - self._db_totals_t >= 1.0:
            self._db_totals_cache = get_program_totals(str(self.game), str(self.program)) or {}
            self._db_totals_t = now

        db = self._db_totals_cache
        parts = []

        for key in self.tracks:
            val = getattr(s, key, 0)
            db_val = db.get(key, 0)

            if key == "playtime_seconds":
                parts.append(f"run_time: {format_hms(int(val))}")
                parts.append(f"total_time: {format_hms(int(db_val + val))}")
            else:
                parts.append(f"{key}: {val} (total {db_val + val})")

        return " | ".join(parts)

    def stat_timer(self):
        try:
            if self.run.running and not self.run.paused:
                now = monotonic()
                if self.run.run_last_t == 0.0:
                    self.run.run_last_t = now
                else:
                    dt = now - self.run.run_last_t
                    self.run.run_last_t = now
                    if dt > 0:
                        self.run.run_seconds += dt
                        whole = int(self.run.run_seconds)
                        if whole > 0:
                            self.run.run_seconds -= whole
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
        text: tuple = ("Input",),
    ) -> None:
        self.game = game
        self.program = program
        self.tracks = btn.property("tracks") or []
        self.temp_row_usage = temp_row_usage
        self.numberinput = int(number)

        self.dynamic_row.set_program(text=text, number=self.temp_row_usage)
        self.image.cfg = self.dynamic_row.get_cfg()

    def start_scripts(self) -> None:
        cap_idx = int(self.capture_index.value())
        mcu_port = (self.mcu_port.currentData() or "").strip()

        self.settings.setValue("capture_index", cap_idx)
        self.settings.setValue("mcu_port", mcu_port)

        extras = self.dynamic_row.get_cfg() or {}

        runs = int(self.run_spin.value()) if hasattr(self, "run_spin") else 1
        profile = int(self.profile_spin.value()) if hasattr(self, "profile_spin") else 1

        self._apply_devices()

        self.Command_queue.put({
            "cmd": "SET_PROGRAM",
            "game": self.game,
            "program": self.program,
            "number": int(self.numberinput),
            "runs": runs,
            "profile": profile,
            "cfg": extras,
        })

        self.run.running = True
        self.run.paused = False
        self.run.run_last_t = monotonic()
        self.run.run_seconds = 0.0

    def pause_scripts(self) -> None:
        if not self.run.running:
            return

        if not self.run.paused:
            self.Command_queue.put({"cmd": "PAUSE"})
            self.run.paused = True
            self.run.run_last_t = 0.0
            self.pause_button.setText("Resume Program")
        else:
            self.Command_queue.put({"cmd": "RESUME"})
            self.run.paused = False
            self.run.run_last_t = monotonic()
            self.pause_button.setText("Pause Program")

    def stop_scripts(self) -> None:
        self.Command_queue.put({"cmd": "STOP"})
        
        self.run.running = False
        self.run.paused = False
        self.run.run_last_t = 0.0
        self.run.run_seconds = 0.0
        
        if hasattr(self, "pause_button"):
            self.pause_button.setText("Pause Program")

    def update_debug(self) -> None:
        dbg = getattr(self.image, "debugger", None)
        dbg.set_enabled(not dbg.enabled)


        if dbg.enabled:
            self.debug_button.setText("Debug Off")
        else:
            self.debug_button.setText("Debug On")

    def on_screenshot_clicked(self) -> None:
        try:
            frame = getattr(self.image, "original_image", None)
            if frame is None or getattr(frame, "size", 0) == 0:
                pyqt_w.QMessageBox.warning(self, "Screenshot", "No frame available to save.")
                return

            result = pyqt_w.QFileDialog.getSaveFileName(
                self,
                "Save Screenshot",
                "",
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)",
            )

            # PyQt returns (filename, selected_filter)
            if not result or len(result) < 1:
                return

            filename = result[0]
            selected_filter = result[1] if len(result) > 1 else ""

            # Ensure filename is a plain Python str
            filename = str(filename).strip()
            if not filename:
                return

            low = filename.lower()
            if not (low.endswith(".png") or low.endswith(".jpg") or low.endswith(".jpeg")):
                if "PNG" in selected_filter:
                    filename += ".png"
                elif "JPEG" in selected_filter:
                    filename += ".jpg"
                else:
                    filename += ".png"

            ok = cv.imwrite(filename, frame)
            if not ok:
                pyqt_w.QMessageBox.critical(self, "Screenshot", f"cv.imwrite failed:\n{filename}")

        except Exception as e:
            pyqt_w.QMessageBox.critical(self, "Screenshot", f"{type(e).__name__}: {e}")
            traceback.print_exc()

    def _test_capture(self):
        idx = int(self.capture_index.value())

        # ask backend video thread to switch
        self.Command_queue.put({"cmd": "SET_DEVICES", "capture_index": idx, "mcu_port": ""})

        # poll for result a moment later
        pyqt_c.QTimer.singleShot(300, self._show_capture_test_result)

    def _show_capture_test_result(self):
        msg = getattr(self.image, "capture_status_msg", "")
        if msg:
            pyqt_w.QMessageBox.information(self, "Capture Test", msg)

    def _refresh_ports(self):
        self.mcu_port.clear()
        ports = list(list_ports.comports())
        for p in ports:
            # p.device is COM3 or /dev/tty...
            self.mcu_port.addItem(f"{p.device}  ({p.description})", p.device)

        if self.mcu_port.count() == 0:
            self.mcu_port.addItem("No ports found", "")

    def _apply_devices(self):
        cap_idx = int(self.capture_index.value())

        port = (self.mcu_port.currentData() or "").strip()
        if not port:
            port = (self.mcu_port.currentText().split(" ", 1)[0] or "").strip()

        self.Command_queue.put({
            "cmd": "SET_DEVICES",
            "capture_index": cap_idx,
            "mcu_port": port,
        })
