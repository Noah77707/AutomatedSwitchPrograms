import os
import sys
from time import time, monotonic, sleep
from typing import TYPE_CHECKING, Tuple, List, Any, Dict
import Constants as const
import numpy as np
import re
from pytesseract import pytesseract as pt

from .Dataclasses import *
from .Window_Capture import *

from .Image_Processing import Image_Processing

state_timer = 0
LM_CACHE: dict[tuple[str, str], TemplateLandmark] = {}


def wait_for_roi_condition(
        image: Image_Processing,
        roi: Tuple[int, int, int, int],
        predicate,
        timeout: float = 2.0,
        min_frames: int = 3,
        ) -> bool:
    start = monotonic()
    good = 0

    # runs while time is 
    while monotonic() - start < timeout:
        frame = getattr(image, 'original_image', None)
        if frame is None:
            sleep(0.01)
            continue
        # This sees if consecutive frames are high enough for the shiny sparkle
        if predicate(frame, roi):
            good += 1
            if good >= min_frames:
                return True
        else:
            good = 0
        sleep(0.01)
    return False
# trhe function that checks the colors
def check_image_position_colors(
    image,
    color: Tuple[int,int,int],
    positions: List[Tuple[int,int]],
    tol: int = 10,
) -> bool:
    frame = getattr(image, "original_image", None)
    if frame is None:
        return False

    h, w = frame.shape[:2]
    for (x, y) in positions:
        if x < 0 or y < 0 or x >= w or y >= h:
            return False

        # get pixel BGR
        b, g, r = frame[y, x]  # OpenCV is row=y, col=x
        if not _color_close((int(b), int(g), int(r)), color, tol):
            return False
    return True
# this passes everything to the check_iamge_position_colors. It mainly makes everything more readable
def _color_close(bgr: Tuple[int,int,int], target: Tuple[int,int,int], tol: int) -> bool:
    return (abs(bgr[0] - target[0]) <= tol and
            abs(bgr[1] - target[1]) <= tol and
            abs(bgr[2] - target[2]) <= tol)

def check_state(image, game: str, name: str) -> bool:
    frame = getattr(image, "original_image", None)
    if frame is None:
        return False

    states = const.GAME_STATES.get(game)
    if not states:
        return False
    cfg = states.get(name)
    if not cfg:
        return False

    color = cfg["color"]
    positions = cfg["positions"]
    tol = int(cfg.get("tol", 10))

    h, w = frame.shape[:2]
    for (x, y) in positions:
        if x < 0 or y < 0 or x >= w or y >= h:
            return False
        b, g, r = frame[y, x]
        if not _color_close((int(b), int(g), int(r)), color, tol):
            return False
    return True
# The player can split states. This is mainly used to programs that run othjer programs. I.E. automated_egg for BDSP
def split_state(s: str | None) -> tuple[str, str | None]:
    if not s:
        return (None, None)
    if "|" not in s:
        return (s, None)
    phase, sub = s.split("|", 1)
    return (phase, sub if sub != "None" else None)

def join_state(phase: str, sub: str | None) -> str:
    return f"{phase}|{sub if sub is not None else 'None'}"
# checks if a landmark/template is in a specified roi. This is used to make reliable macros due to the inprecise microcontroller 
def is_in_area(image: Image_Processing, compared_to_image_path: str, roi: Tuple[int, int, int, int], threshold: float = 0.90) -> float:
    frame = getattr(image, 'original_image', None)
    if frame is None:
        return 0.0

    ref = cv.imread(compared_to_image_path, cv.IMREAD_GRAYSCALE)
    if ref is None:
        return 0.0

    x, y, w, h = roi
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    crop = gray[y:y+h, x:x+w]

    if crop.shape[0] < ref.shape[0] or crop.shape[1] < ref.shape[1]:
        return 0.0

    crop = cv.GaussianBlur(crop, (3, 3), 0)
    ref  = cv.GaussianBlur(ref,  (3, 3), 0)

    res = cv.matchTemplate(crop, ref, cv.TM_CCOEFF_NORMED)
    _, maxv, _, _ = cv.minMaxLoc(res)
    print(maxv)
    return float(maxv)

def detect_template(frame_bgr: np.ndarray, lm: TemplateLandmark) -> float:
    x, y, w, h = lm.roi
    crop = frame_bgr[y:y+h, x:x+w]
    if crop.size == 0:
        return 0.0

    gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    tmpl = lm.template_gray
    tmpl = cv.cvtColor(tmpl, cv.COLOR_BGR2GRAY) if tmpl.ndim == 3 else tmpl

    if gray.shape[0] < tmpl.shape[0] or gray.shape[1] < tmpl.shape[1]:
        return 0.0

    res = cv.matchTemplate(gray, tmpl, lm.method)
    minv, maxv, _, _ = cv.minMaxLoc(res)

    if lm.method in (cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED):
        return float(1.0 - minv)   # minv: 0 best -> score: 1 best
    else:
        return float(maxv)         # maxv: 1 best for *_NORMED

def get_landmark(game: str, name: str, threshold:int = 0.80) -> TemplateLandmark:
    key = (game, name)
    if key in LM_CACHE:
        return LM_CACHE[key]

    cfg = const.GAME_STATES[game][name]
    if "path" not in cfg:
        raise KeyError(f"{game}.{name} is not a template entry (missing 'path')")

    tpl = cv.imread(cfg["path"], cv.IMREAD_GRAYSCALE)
    if tpl is None:
        raise FileNotFoundError(cfg["path"])

    lm = TemplateLandmark(
        template_gray=tpl,
        roi=tuple(cfg["roi"]),
        threshold=float(cfg.get("threshold", threshold)),
        hits_required=int(cfg.get("hits_required", 3)),
        method=int(cfg.get("method", cv.TM_CCOEFF_NORMED)),
    )
    LM_CACHE[key] = lm
    return lm

def _clahe_gray(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("Image is None")

    # Ensure uint8 for CLAHE
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)

    # Handle channel count safely
    if img.ndim == 2:
        gray = img
    elif img.ndim == 3 and img.shape[2] == 1:
        gray = img[:, :, 0]
    elif img.ndim == 3 and img.shape[2] == 3:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    elif img.ndim == 3 and img.shape[2] == 4:
        gray = cv.cvtColor(img, cv.COLOR_BGRA2GRAY)
    else:
        raise ValueError(f"Unsupported image shape: {img.shape}")

    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def _crop_roi(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = roi
    return frame[y:y+h, x:x+w]
# these functinos make a text fragment more visible to the clahe program
def prep_text(img_bgr_or_gray: np.ndarray) -> np.ndarray:
    if img_bgr_or_gray.ndim == 3:
        gray = cv.cvtColor(img_bgr_or_gray, cv.COLOR_BGR2GRAY)
    else:
        gray = img_bgr_or_gray

    gray = cv.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv.INTER_CUBIC)
    gray = cv.GaussianBlur(gray, (3,3), 0)

    # Invert so text becomes white blobs (usually text is dark)
    bw = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)[1]
    return bw

def has_enough_text(bw: np.ndarray, min_ratio: float = 0.01, max_ratio: float = 0.25) -> bool:
    # ratio of "ink" pixels (white in inverted binary)
    ink = float(np.count_nonzero(bw)) / bw.size
    return (ink >= min_ratio) and (ink <= max_ratio)
# this uses those text fragments to see if they are similar. 
def match_text_fragment(
    image: Image_Processing,
    template_bgr_or_gray: np.ndarray,
    roi: Tuple[int,int,int,int],
    sqdiff_max: float = 0.20,
) -> tuple[bool, float]:
    
    frame = image.original_image
    if frame is None:
        return False, 1.0

    x,y,w,h = roi
    crop = frame[y:y+h, x:x+w]
    if crop.size == 0:
        return False, 1.0

    crop_bw = prep_text(crop)
    if not has_enough_text(crop_bw):
        return False, 1.0

    tmpl_bw = prep_text(template_bgr_or_gray)

    res = cv.matchTemplate(crop_bw, tmpl_bw, cv.TM_SQDIFF_NORMED)
    minv, _, _, _ = cv.minMaxLoc(res)  # for SQDIFF, min is best
    return (minv <= sqdiff_max), float(minv)
# this has the player move until a specified landmark is in sight
def walk_until_landmark_dpad(
    ctrl,
    image,
    lm: TemplateLandmark,   # expects: lm.template_gray (np.ndarray), lm.roi, lm.threshold, lm.method
    dpad_dir: int,
    game: str = None,
    state: str = None,
    hold_s: float = 0.10,
    pause_s: float = 0.05,
    max_steps: int = 500,
    template_cache: Optional[dict[int, np.ndarray]] = None,  # key: id(lm)
) -> bool:
    """
    Uses CLAHE-normalized grayscale template matching to reduce time-of-day sensitivity.
    Returns True if found, False if max_steps reached.
    """

    cache_key = id(lm)

    # Load + preprocess template once (optionally cached)
    if template_cache is not None and cache_key in template_cache:
        tmpl_p = template_cache[cache_key]
    else:
        tmpl = getattr(lm, "template_gray", None)
        if not isinstance(tmpl, np.ndarray):
            raise TypeError("lm.template_gray must be a numpy array (already-loaded template image).")
        tmpl_p = _clahe_gray(tmpl)  # safe for 2D gray or 3D bgr
        if template_cache is not None:
            template_cache[cache_key] = tmpl_p

    for _ in range(max_steps):
        frame = getattr(image, "original_image", None)
        if frame is not None:
            crop = _crop_roi(frame, lm.roi)
            if crop.size:
                crop_p = _clahe_gray(crop)
                res = cv.matchTemplate(crop_p, tmpl_p, lm.method)
                _, maxv, _, _ = cv.minMaxLoc(res)
                if maxv >= lm.threshold:
                    return True

        ctrl.dpad(dpad_dir, hold_s)
        if pause_s:
            sleep(pause_s)

    return False

def find_keywords_in_texts(
    texts: list[str],
    keywords: list[str],
) -> dict[str, bool]:
    joined = " | ".join(texts)
    return {k: (k.lower() in joined) for k in keywords}

def is_row_selected(image: Image_Processing, roi, white_thres=240, ratio= 0.35):
    frame  = image.original_image
    x, y, w, h = roi
    crop = frame[y:y+h, x:x+w]
    gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY)

    white_pixels = np.count_nonzero(gray > white_thres)
    return (white_pixels / gray.size) > ratio

def match_label(frame_bgr, roi, template_gray, thresh=0.85) -> bool:
    x, y, w, h = map(int, roi)
    crop = frame_bgr[y:y+h, x:x+w]
    if crop.size == 0:
        return False

    gray = cv.cvtColor(crop, cv.COLOR_BGR2GRAY) if crop.ndim == 3 else crop

    tmpl = template_gray
    if tmpl is None:
        return False
    if tmpl.ndim == 3:
        tmpl = cv.cvtColor(tmpl, cv.COLOR_BGR2GRAY)

    if gray.shape[0] < tmpl.shape[0] or gray.shape[1] < tmpl.shape[1]:
        return False

    res = cv.matchTemplate(gray, tmpl, cv.TM_CCOEFF_NORMED)
    _, maxv, _, _ = cv.minMaxLoc(res)
    return float(maxv) >= float(thresh)

def match_any_slot(frame_bgr, rois, tpl_gray, threshold=0.78) -> tuple[bool, float]:
    for roi in rois:
        if match_label(frame_bgr, roi, tpl_gray, threshold):
            return True
    return False


def get_tpl(image, path: str, flags=cv.IMREAD_GRAYSCALE):
    if not hasattr(image, "tpl_cache"):
        image.tpl_cache = {}

    key = (path, flags)
    if key not in image.tpl_cache:
        tpl = cv.imread(path, flags)
        if tpl is None:
            raise FileNotFoundError(f"Template not found: {path}")
        image.tpl_cache[key] = tpl

    return image.tpl_cache[key]
