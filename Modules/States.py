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

from .Image_Processing import Image_Processing, Text

state_timer = 0
LM_CACHE: dict[tuple[str, str], TemplateLandmark] = {}

def return_states(image: Image_Processing, state: str) -> str:
    if image.state != state:
        image.state = state
        image.debugger._state = state
    return state

def check_state(image, game: str, *path: str) -> bool:
    frame = getattr(image, "original_image", None)
    if frame is None:
        return False

    states = const.GAME_STATES.get(game)
    cfg = states
    for key in path:
        cfg = cfg.get(key)
        if cfg is None:
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

def wait_state(
    image,
    game: str,
    check_if_not: bool,
    timeout_s: float,
    *path: str,
    stable_frames: int = 2,
    poll_sleep: float = 0.005,
    require_cfg: bool = True,
) -> bool:
    """
    check_if_not=True  -> wait until NOT check_state(...)
    check_if_not=False -> wait until check_state(...)
    Condition must be true for `stable_frames` *new frames* in a row.

    require_cfg=True prevents accidental early-True when config/path is missing.
    """
    if require_cfg:
        states = getattr(const, "GAME_STATES", {}).get(game)
        cfg = states
        for key in path:
            if not isinstance(cfg, dict) or key not in cfg:
                return False
            cfg = cfg[key]

    t0 = monotonic()
    streak = 0
    last_fid = int(getattr(image, "frame_id", 0))

    while True:
        elapsed = monotonic() - t0
        remaining = timeout_s - elapsed
        if remaining <= 0:
            return False

        if hasattr(image, "wait_new_frame"):
            try:
                image.wait_new_frame(last_id=last_fid, timeout_s=min(0.35, remaining))
            except TypeError:
                image.wait_new_frame(timeout_s=min(0.35, remaining))

        fid = int(getattr(image, "frame_id", 0))
        if fid == last_fid:
            sleep(min(poll_sleep, max(0.0, remaining)))
            continue
        last_fid = fid

        frame = getattr(image, "original_image", None)
        if frame is None:
            streak = 0
            sleep(min(poll_sleep, max(0.0, remaining)))
            continue

        ok = check_state(image, game, *path)
        cond = (not ok) if check_if_not else ok

        if cond:
            streak += 1
            if streak >= stable_frames:
                return True
        else:
            streak = 0

def split_state(s: str | None) -> tuple[str, str | None]:
    if not s:
        return (None, None)
    if "|" not in s:
        return (s, None)
    state, sub = s.split("|", 1)
    return (state, sub if sub != "None" else None)

def join_state(state: str, sub: str | None) -> str:
    return f"{state}|{sub if sub is not None else 'None'}"

def get_box_slot_kind(image, game: str) -> tuple[str, str]:
    """ 
    Returns (kind, name)
    kind: "empty", "egg", "pokemon", "shiny"
    name: name
    """
    name_rois = const.GAME_STATES[game]["pokemon"]["pokemon_in_box"]["rois"]
    image.debugger.add_roi(name_rois[0], (0, 0, 0), 2)
    best = ""
    for roi in name_rois:
        raw = Text.recognize_box_name(image, roi)
        raw = (raw or "").strip()
        if raw:
            best = raw
            break
        
    if not best:
        return "empty", ""
    
    if best.lower() == "egg":
        return "egg", "Egg"
    
    is_shiny = check_state(image, game, "pokemon", "shiny_symbol")
    return ("shiny" if is_shiny else "pokemon"), best

# Will move later

def _crop(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    """Safe ROI crop. Returns empty array if invalid."""
    if frame is None:
        return np.empty((0, 0), dtype=np.uint8)

    x, y, w, h = map(int, roi)
    if w <= 0 or h <= 0:
        return np.empty((0, 0), dtype=np.uint8)

    H, W = frame.shape[:2]
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(W, x + w)
    y2 = min(H, y + h)

    if x2 <= x1 or y2 <= y1:
        return np.empty((0, 0), dtype=np.uint8)

    return frame[y1:y2, x1:x2]

# this passes everything to the check_iamge_position_colors. It mainly makes everything more readable
def _color_close(bgr: Tuple[int,int,int], target: Tuple[int,int,int], tol: int) -> bool:
    return (abs(bgr[0] - target[0]) <= tol and
            abs(bgr[1] - target[1]) <= tol and
            abs(bgr[2] - target[2]) <= tol)
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
    return float(maxv)
# this uses the TemplateLandmark and returns the information first. It doesn't do the same job as get_tpl
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

# this has the player move until a specified landmark is in sight
def walk_until_landmark_dpad(
    ctrl,
    image,
    lm: TemplateLandmark,   # expects: lm.template_gray (np.ndarray), lm.roi, lm.threshold, lm.method
    dir: int,
    game: str = None,
    state: str = None,
    hold_s: float = 0.10,
    pause_s: float = 0.05,
    max_steps: int = 500,
    template_cache: Optional[dict[int, np.ndarray]] = None,  # key: id(lm)
) -> bool:
    """
    directions:
    0 is up, 2 is right, 4 is down, and 6 is left
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
            crop = _crop(frame, lm.roi)
            if crop.size:
                crop_p = _clahe_gray(crop)
                res = cv.matchTemplate(crop_p, tmpl_p, lm.method)
                _, maxv, _, _ = cv.minMaxLoc(res)
                if maxv >= lm.threshold:
                    return True

        ctrl.dpad(dir, hold_s)
        if pause_s:
            sleep(pause_s)

    return False

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

def match_any_slot(frame_bgr, rois, tpl_gray, threshold=0.78, number= 1) -> tuple[bool, float]:
    for roi in rois:
        if match_label(frame_bgr, roi, tpl_gray, threshold):
            return True, number
    number += 1
    return False
# Important
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
