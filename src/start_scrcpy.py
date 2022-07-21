import ctypes
import functools
import logging
import os
import subprocess
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np
import pyautogui

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

SCRCPY_TITLE = 'scrcpy'

FindWindow = ctypes.windll.user32.FindWindowW
PostMessage = ctypes.windll.user32.PostMessageW

WM_PLUGIN_BASE = 0x0400  # WM_USER


class PluginActions(Enum):
    click = 1
    key = 2
    take_screenshot = 3


@dataclass(frozen=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self):
        return Point(
            self.x + self.width // 2,
            self.y + self.height // 2
        )


def _load_image(img):
    img = str(img.resolve())

    return cv2.imread(img, cv2.IMREAD_GRAYSCALE)


root_path = Path(__file__).parent / '..'
resources = root_path / 'resources/buttons'
scrcpy_exe = root_path / 'bin/scrcpy.exe'

money_button = [_load_image(img) for img in resources.glob('money_button/*.png')]
claim_button = [_load_image(img) for img in resources.glob('claim_button/*.png')]
x2_money = [_load_image(img) for img in resources.glob('x2_money/*.png')]
riot_images = [_load_image(img) for img in resources.glob('riot/*.png')]


def run_scrcpy_endlessly() -> None:
    os.chdir(scrcpy_exe.parent)
    # max 3 restart in 1 minute

    real_start = datetime.now()
    restarts = 0
    while restarts <= 3:
        subprocess.run([
            'scrcpy',
            # '--always-on-top',
            # '--disable-screensaver',
            '--lock-video-orientation=0',
            '--max-fps=2',
            '--max-size=1024',
            '--no-clipboard-autosync',
            '--no-downsize-on-error',
            '--no-power-on',
            '--stay-awake',
            # '--window-x=0',
            # '--window-y=0',
            '--window-width=350',
            f'--window-title={SCRCPY_TITLE}',
            '--turn-screen-off',
        ])
        last_stop_of_program = datetime.now()

        if (last_stop_of_program - real_start).seconds > 60:
            real_start = datetime.now()
            restarts = 0
        else:
            restarts += 1


@lru_cache(maxsize=1)
def _find_scrcpy_window() -> Optional[int]:  # HWND
    hwnd = FindWindow("SDL_app", SCRCPY_TITLE)
    if not hwnd:
        warnings.warn(f"**DEV WARNING**, I couldn't find the SDL application!")
        return None

    is_minimized = ctypes.windll.user32.IsIconic(hwnd) != 0
    if not is_minimized:
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)

    return hwnd


def get_scrcpy_window() -> int:
    times_tried = 0
    while times_tried <= 5:
        if times_tried > 0:
            _find_scrcpy_window.cache_clear()
            time.sleep(1)

        win = _find_scrcpy_window()
        if win is not None:
            return win

        times_tried += 1

    raise ValueError("No window present...")


def makelong(loword, hiword):
    return ((int(hiword) & 0xFFFF) * 0x10000) | (int(loword) & 0xFFFF)


def _click(loc):
    if not isinstance(loc, Point):
        loc = loc.center

    logging.info(f' * clicking on {loc}')
    PostMessage(get_scrcpy_window(), WM_PLUGIN_BASE, PluginActions.click.value, makelong(loc.x, loc.y))

    time.sleep(0.5)


def _handle_riot_screen():
    logging.info('[riot] Checking riot screen')
    while (location := _get_button_location(riot_images, confidence=0.85)) is not None:
        time.sleep(1)

        logger.info("[riot] clicking it away")
        center = location.center
        above_center = Point(center.x, center.y - 300)
        _click(above_center)


class ImageNotFound(Exception):
    """Raised when the image is not found (duh!)"""


def _locate_on_screen(haystack, needle, limit=1, confidence=0.90, step=1) -> Box:
    needle_height, needle_width = needle.shape[:2]

    if step == 2:
        confidence *= 0.95
        needle = needle[::step, ::step]
        haystack = haystack[::step, ::step]
    else:
        step = 1

    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)

    match_indices = np.arange(result.size)[(result > confidence).flatten()]
    matches = np.unravel_index(match_indices[:limit], result.shape)

    if len(matches[0]) == 0:
        raise ImageNotFound

    matchx = matches[1] * step
    matchy = matches[0] * step
    for x, y in zip(matchx, matchy):
        return Box(x, y, needle_width, needle_height)

    raise ImageNotFound


def run_only_once_every(seconds=0, microseconds=750_000):
    max_diff = timedelta(seconds=seconds, microseconds=microseconds)

    def _inner(func):
        last_ret = None
        last_ret_time: Optional[datetime] = None

        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            nonlocal last_ret_time, last_ret

            if last_ret_time is not None and (datetime.now() - last_ret_time) < max_diff:
                return last_ret

            ret = func(*args, **kwargs)
            last_ret_time = datetime.now()
            last_ret = ret

            return ret

        return _wrapped

    return _inner


@run_only_once_every()
def _grab_scrcpy():
    hwnd = get_scrcpy_window()
    screenshot_location = scrcpy_exe.parent / 'screenshot.bmp'
    screenshot_location.unlink(missing_ok=True)
    PostMessage(hwnd, WM_PLUGIN_BASE, PluginActions.take_screenshot.value, 0)
    while not screenshot_location.exists():
        time.sleep(0.1)

    return _load_image(screenshot_location)


def _get_button_location(buttons, confidence=0.90) -> Optional[Box]:
    if not isinstance(buttons, Iterable):
        buttons = [buttons]

    # locate button on the screen
    screen_copy = _grab_scrcpy()
    for button in buttons:
        try:
            return _locate_on_screen(
                screen_copy,
                button,
                confidence=confidence,
            )
        except ImageNotFound:
            continue

    return None


def _click_on_button(button, wait_before_click: float = 0, wait_for_disappearance: bool = True):
    enter_into_method = datetime.now()
    found_button = None
    while True:
        _handle_riot_screen()

        if (datetime.now() - enter_into_method).seconds > 600:
            pyautogui.screenshot('failure.png')
            logging.error("Couldn't find a button in 10 minutes?")
            raise ValueError("Couldn't find a button in 10 minutes?")

        # locate button on the screen
        logger.debug(' -- trying to find the button')
        location = _get_button_location(button)
        if location is None:
            logger.debug(f' -- not found (found_button: {found_button})')
            if found_button is not None:
                # We found the button, and now we don't find it anymore... Good -> Stop the loop.
                return found_button

            time.sleep(1)
            continue

        if wait_before_click:
            time.sleep(wait_before_click)

        logger.debug(f' -- clicking {location}')
        _click(location)

        if not wait_for_disappearance:
            logger.debug(f' -- done')
            return location

        found_button = location

        time.sleep(1)


def click_on_buttons():
    last_x2_money_check: Optional[datetime] = None

    while True:
        _handle_riot_screen()

        logging.info('[money] checking for money button')
        _click_on_button(money_button)
        logging.info('[money] checking for claim button')
        _click_on_button(claim_button, wait_before_click=0.5)
        logging.info('[money] finished')

        did_x2_money_check = False
        if last_x2_money_check is None or (datetime.now() - last_x2_money_check).seconds > 600:
            increase_multiplier()
            last_x2_money_check = datetime.now()
            did_x2_money_check = True

        # It's not immediately that this money thing comes again. No need to waste resources...
        time.sleep(50 if did_x2_money_check else 55)


def increase_multiplier():
    logging.info('[x2 money] first click')
    x2_button = _click_on_button(x2_money, wait_for_disappearance=False)

    logging.info('[x2 money] claim button')
    _click_on_button(claim_button, wait_for_disappearance=False)

    time.sleep(1)

    while _get_button_location(claim_button) is not None:
        logging.info('[x2 money] get out')
        _click(x2_button)
        time.sleep(1)

    logging.info('[x2 money] finished')


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        pool.submit(run_scrcpy_endlessly)
        time.sleep(5)  # Wait a bit before starting the rest
        pool.submit(click_on_buttons)
