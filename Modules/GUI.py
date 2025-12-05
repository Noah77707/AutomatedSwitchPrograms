import os
import sys
import subprocess
from queue import Queue, Empty
from time import sleep
from typing import TYPE_CHECKING
from threading import Event
import Constants as const
import cv2 as cv
from .Controller import Controller

import PyQt6.QtWidgets as pyqt_w
import PyQt6.QtCore as pyqt_c
import PyQt6.QtGui as pyqt_g

from .Image_Processing import Image_Processing
from Programs.HOME_Scripts import *
from Programs.SWSH_Scripts import *
from Programs.BDSP_Scripts import *
from Programs.LA_Scripts import *
from Programs.SV_Scripts import *
from Programs.LZA_Scripts import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIA_DIR = os.path.join(BASE_DIR, "media")  # media/SWSH, media/BDSP, etc.

MODULE_NAME = 'GUI'

image_label_style = "background-color: #000; border: 1px solid #aaa"
text_label_style = ""
text_style = ""
clock_style = ""
stop_button_style = ""


class App(pyqt_w.QApplication):
    def __init__(self):
        super().__init__([])
        self.setStyleSheet("QWidget { background-color: #333; }")


# New: clickable label that emits x,y when clicked
class ClickableLabel(pyqt_w.QLabel):
    clicked = pyqt_c.pyqtSignal(int, int)

    def mousePressEvent(self, event: pyqt_g.QMouseEvent) -> None:
        if event.button() == pyqt_c.Qt.MouseButton.LeftButton:
            pos = event.position()
            self.clicked.emit(int(pos.x()), int(pos.y()))
        super().mousePressEvent(event)


class GUI(pyqt_w.QWidget):
    def __init__(self, Image_queue: Queue, Command_queue: Queue, shutdown_event: Event, stop_event: Event) -> None:
        super().__init__()

        self.game_rois = {}  # e.g. {"SWSH": (x, y, w, h), "BDSP": (...)}

        self.Image_queue = Image_queue
        self.Command_queue = Command_queue

        self.setWindowTitle("Auto Switch Programs")
        main_layout = pyqt_w.QVBoxLayout(self)

        # keep latest frame around for pixel sampling
        self.latest_frame = None
        # region radius in pixels for area stats (2*r+1 square)
        self.region_radius = 5

        self.items = {
            'game_selector': pyqt_w.QMenu(self),
            # use ClickableLabel instead of QLabel
            'switch_capture_label': ClickableLabel(self),
            'start_stop_button': pyqt_w.QPushButton(self),
            'current_state_label': pyqt_w.QLabel(self),
            'encounter_amount_label': pyqt_w.QLabel(self),
            "tab_home": pyqt_w.QWidget(self),
            'tab_swsh': pyqt_w.QWidget(self),
            'tab_bdsp': pyqt_w.QWidget(self),
            'tab_la':   pyqt_w.QWidget(self),
            'tab_sv':   pyqt_w.QWidget(self),
            'tab_lza':  pyqt_w.QWidget(self),
        }

        self.items['switch_capture_label'].setFixedSize(*const.MAIN_FRAME_SIZE)
        self.items['switch_capture_label'].setStyleSheet(image_label_style)
        # connect click signal
        self.items['switch_capture_label'].clicked.connect(self.on_image_clicked)

        self.tabs = pyqt_w.QTabWidget()
        self.tabs.setTabPosition(pyqt_w.QTabWidget.TabPosition.West)
        self.tabs.setMovable(True)

        Home_layout = pyqt_w.QVBoxLayout()
        Home_layout.addWidget(pyqt_w.QLabel("HOME program UI here"))
        CCT_HOME = pyqt_w.QPushButton("Controller Connection Test", self)
        CCT_HOME.clicked.connect(lambda checked, p='Connect_Controller_Test': self.Run_script("HOME", p, checked))
        Home_layout.addWidget(CCT_HOME)
        self.items['tab_home'].setLayout(Home_layout)

        SWSH_layout = pyqt_w.QVBoxLayout()
        SWSH_layout.addWidget(pyqt_w.QLabel("SWSH program UI here"))
        STATIC_ENCOUNTER_SWSH = pyqt_w.QPushButton("Static Encounter", self)
        STATIC_ENCOUNTER_SWSH.clicked.connect(lambda checked, p='Static_Encounter_SWSH': self.Run_script("SWSH", p, checked))
        SWSH_layout.addWidget(STATIC_ENCOUNTER_SWSH)
        self.items['tab_swsh'].setLayout(SWSH_layout)

        BDSP_layout = pyqt_w.QVBoxLayout()
        BDSP_layout.addWidget(pyqt_w.QLabel("BDSP program UI here"))
        self.items['tab_bdsp'].setLayout(BDSP_layout)

        LA_layout = pyqt_w.QVBoxLayout()
        LA_layout.addWidget(pyqt_w.QLabel("LA program UI here"))
        self.items['tab_la'].setLayout(LA_layout)

        SV_layout = pyqt_w.QVBoxLayout()
        SV_layout.addWidget(pyqt_w.QLabel("SV program UI here"))
        self.items['tab_sv'].setLayout(SV_layout)

        LZA_layout = pyqt_w.QVBoxLayout()
        LZA_layout.addWidget(pyqt_w.QLabel("LZA program UI here"))
        self.items['tab_lza'].setLayout(LZA_layout)

        self.tabs.addTab(self.items['tab_home'], "HOME")
        self.tabs.addTab(self.items['tab_swsh'], "SWSH")
        self.tabs.addTab(self.items['tab_bdsp'], "BDSP")
        self.tabs.addTab(self.items['tab_la'],   "LA")
        self.tabs.addTab(self.items['tab_sv'],   "SV")
        self.tabs.addTab(self.items['tab_lza'],  "LZA")

        self.current_program_name = self.tabs.tabText(self.tabs.currentIndex())
        self.current_process = None

        self.tabs.currentChanged.connect(self.on_tab_changed)

        center_layout = pyqt_w.QHBoxLayout()
        center_layout.addWidget(self.tabs)
        center_layout.addWidget(self.items['switch_capture_label'])

        main_layout.addLayout(center_layout)

        self.screenshot_button = pyqt_w.QPushButton("Save Screenshot", self)
        self.screenshot_button.clicked.connect(self.on_screenshot_clicked)
        main_layout.addWidget(self.screenshot_button)

        self.roi_button = pyqt_w.QPushButton("Select ROI from image", self)
        self.roi_button.clicked.connect(self.on_select_roi_clicked)
        main_layout.addWidget(self.roi_button)

        # New: labels to display pixel and area info
        info_layout = pyqt_w.QVBoxLayout()
        self.pixel_info_label = pyqt_w.QLabel("Pixel: (x, y) BGR=(...) RGB=(...) HEX=...")
        self.area_info_label = pyqt_w.QLabel("Area: size, bounds, mean color")
        self.pixel_info_label.setStyleSheet("color: #eee;")
        self.area_info_label.setStyleSheet("color: #eee;")
        info_layout.addWidget(self.pixel_info_label)
        info_layout.addWidget(self.area_info_label)
        main_layout.addLayout(info_layout)

        self.timer = pyqt_c.QTimer(self)
        self.timer.timeout.connect(lambda: self.update_GUI(shutdown_event))
        self.timer.start(1)
        self.show()

    def update_GUI(self, shutdown_event: Event) -> None:
        if shutdown_event.is_set():
            self.close()
            return

        try:
            frame = self.Image_queue.get_nowait()   # this is np.ndarray now
        except Empty:
            return

        self.latest_frame = frame

        # convert BGR -> RGB
        frame_rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
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

    def on_tab_changed(self, index: int) -> None:
        self.current_program_name = self.tabs.tabText(index)
        self.Command_queue.put({
            'type': 'SET_GAME',
            'game': self.current_program_name
        })

    def Run_script(self, game: str, program: str, checked: bool = False) -> None:
        self.Command_queue.put({'cmd': 'SET_PROGRAM', 'game': game, 'program': program, 'running': True})

    def on_screenshot_clicked(self) -> None:
        if self.latest_frame is None:
            msg = pyqt_w.QMessageBox(self)
            msg.setIcon(pyqt_w.QMessageBox.Icon.Warning)
            msg.setWindowTitle("No Frame")
            msg.setText("No video frame available to save.")
            msg.exec()
            return

        filename, _ = pyqt_w.QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            "",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*)"
        )
        if not filename:
            return  # user cancelled

        cv.imwrite(filename, self.latest_frame)

    def on_select_roi_clicked(self) -> None:
        # Which game is active from the tab
        game = self.current_program_name  # e.g. "SWSH", "BDSP"
        game_dir = os.path.join(MEDIA_DIR, game)

        # Let user pick an image starting in media/<game>
        filename, _ = pyqt_w.QFileDialog.getOpenFileName(
            self,
            f"Select image for ROI ({game})",
            game_dir,
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if not filename:
            return  # user cancelled

        img = cv.imread(filename)
        if img is None:
            msg = pyqt_w.QMessageBox(self)
            msg.setIcon(pyqt_w.QMessageBox.Icon.Warning)
            msg.setWindowTitle("Error")
            msg.setText(f"Could not load image:\n{filename}")
            msg.exec()
            return

        cv.namedWindow("Select ROI", cv.WINDOW_NORMAL)
        cv.imshow("Select ROI", img)
        x, y, w, h = cv.selectROI("Select ROI", img, showCrosshair=True, fromCenter=False)
        cv.destroyWindow("Select ROI")

        if w == 0 or h == 0:
            return

        self.game_rois[game] = (int(x), int(y), int(w), int(h))

        msg = pyqt_w.QMessageBox(self)
        msg.setIcon(pyqt_w.QMessageBox.Icon.Information)
        msg.setWindowTitle("ROI Selected")
        msg.setText(f"{game} ROI: x={x}, y={y}, w={w}, h={h}")
        msg.exec()

        print(f"[ROI] {game}: x={x}, y={y}, w={w}, h={h}")

    # New: handle clicks on the live image
    def on_image_clicked(self, x: int, y: int) -> None:
        if self.latest_frame is None:
            return
        pix = self.items['switch_capture_label'].pixmap()
        if pix is None:
            return

        frame = self.latest_frame
        h, w, _ = frame.shape

        label_w = self.items['switch_capture_label'].width()
        label_h = self.items['switch_capture_label'].height()

        # map label coords to frame coords
        # assume pixmap is scaled with aspect ratio into label
        pix_w = pix.width()
        pix_h = pix.height()

        # compensate for potential letterboxing
        # compute scale and offset
        scale = min(label_w / pix_w, label_h / pix_h)
        disp_w = int(pix_w * scale)
        disp_h = int(pix_h * scale)
        offset_x = (label_w - disp_w) // 2
        offset_y = (label_h - disp_h) // 2

        # if click outside displayed image, ignore
        if not (offset_x <= x < offset_x + disp_w and offset_y <= y < offset_y + disp_h):
            return

        rel_x = x - offset_x
        rel_y = y - offset_y

        img_x = int(rel_x * pix_w / disp_w)
        img_y = int(rel_y * pix_h / disp_h)

        # clamp
        img_x = max(0, min(w - 1, img_x))
        img_y = max(0, min(h - 1, img_y))

        b, g, r = map(int, frame[img_y, img_x])
        hex_pixel = "#{:02X}{:02X}{:02X}".format(r, g, b)

        # region around the pixel
        rrad = self.region_radius
        x0 = max(img_x - rrad, 0)
        x1 = min(img_x + rrad + 1, w)
        y0 = max(img_y - rrad, 0)
        y1 = min(img_y + rrad + 1, h)

        region = frame[y0:y1, x0:x1]
        area = region.shape[0] * region.shape[1]

        mean_bgr = region.mean(axis=(0, 1))
        mb, mg, mr = mean_bgr.tolist()
        hex_mean = "#{:02X}{:02X}{:02X}".format(int(mr), int(mg), int(mb))

        self.pixel_info_label.setText(
            f"Pixel ({img_x}, {img_y})  BGR=({b}, {g}, {r})  RGB=({r}, {g}, {b})  HEX={hex_pixel}"
        )
        self.area_info_label.setText(
            f"Area {(2*rrad+1)}x{(2*rrad+1)} -> actual {area} px, "
            f"bounds x={x0}..{x1-1}, y={y0}..{y1-1}, "
            f"mean BGR=({mb:.1f}, {mg:.1f}, {mr:.1f})  "
            f"mean RGB=({mr:.1f}, {mg:.1f}, {mb:.1f})  HEX={hex_mean}"
        )
