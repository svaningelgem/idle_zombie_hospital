import logging
import os
import subprocess
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import cv2
import pyautogui
import pygetwindow
from pygetwindow import PyGetWindowException
from required_files import RequiredLatestGithubZipFile

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def _load_image(img):
    return cv2.imread(str(resources / img), cv2.IMREAD_COLOR)


pyautogui.useImageNotFoundException()

root_path = Path(__file__).parent / '..'
resources = root_path / 'resources/buttons'
scrcpy_exe = root_path / 'bin/scrcpy.exe'

money_button = _load_image('money_button.png')
claim_button = _load_image('claim_button.png')
riot_images = {
    'humans': [
        _load_image('humans_won_riot_1.png'),
        _load_image('humans_won_riot_2.png'),
    ],
    'zombies': [
        _load_image('zombies_won_riot_1.png'),
    ],
}

x2_money = _load_image('x2_money.png')
x2_claim_button = _load_image('x2_claim_button.png')


RequiredLatestGithubZipFile(
    url='https://github.com/Genymobile/scrcpy/releases/latest/',
    save_as=scrcpy_exe.parent,
    file_to_check=scrcpy_exe.name,
).check()


def run_scrcpy_endlessly() -> None:
    os.chdir(scrcpy_exe.parent)
    while True:
        subprocess.run([
            'scrcpy',
            '--always-on-top',
            '--disable-screensaver',
            '--lock-video-orientation=0',
            '--max-fps=2',
            '--max-size=1024',
            '--no-clipboard-autosync',
            '--no-downsize-on-error',
            '--no-power-on',
            '--stay-awake',
            '--window-x=0',
            '--window-y=0',
            '--window-width=350',
            '--turn-screen-off',
            '--window-title=scrcpy',
        ])


@lru_cache(maxsize=1)
def _find_scrcpy_window() -> Optional[pygetwindow.Window]:
    possible = [
        w
        for w in pyautogui.getWindowsWithTitle(title='scrcpy')
        if (
           w.title == 'scrcpy'
           and 350 <= w.width <= 450
           and 700 <= w.height <= 1100
        )
    ]

    if len(possible) != 1:
        warnings.warn(f'**DEV WARNING**, I got {len(possible)} windows... Should only have 1.')
        return None

    return possible[0]


def get_scrcpy_window() -> pygetwindow.Window:
    times_tried = 0
    while times_tried <= 5:
        if times_tried > 0:
            _find_scrcpy_window.cache_clear()
            time.sleep(1)

        try:
            win = _find_scrcpy_window()
            if not win.visible:
                win.activate()
            return win
        except (PyGetWindowException, AttributeError, TypeError):
            times_tried += 1

    raise ValueError("No window present...")


@lru_cache(maxsize=1)
def _screen_size() -> Tuple[int, int]:
    ss = pyautogui.screenshot()
    return ss.width, ss.height


def _get_scrcpy_rect() -> Tuple[int, int, int, int]:
    win = get_scrcpy_window()

    w, h = _screen_size()

    return (
        max(0, min(win.left, w)),
        max(0, min(win.top, h)),
        max(0, min(win.width, w)),
        max(0, min(win.height, h)),
    )


def _check_if_riot_happened():
    ...


def _click(loc):
    if not isinstance(loc, pyautogui.Point):
        loc = pyautogui.center(loc)

    logging.info(f' * clicking on {loc}')
    one_pix_diff = pyautogui.Point(loc.x + 1, loc.y - 1)
    pyautogui.moveTo(loc)
    time.sleep(0.25)
    pyautogui.moveTo(one_pix_diff)
    time.sleep(0.25)
    pyautogui.click(loc)
    time.sleep(0.5)


def _handle_riot_screen():
    logging.info('[riot] Checking riot screen')
    location = None

    def _continue():
        nonlocal location

        for section, imgs in riot_images.items():
            for img in imgs:
                location = _get_button_location(img, confidence=0.85)
                if location:
                    return section

        return False

    while who_won := _continue() is not False:
        logger.info(f"[riot] {who_won} won")
        time.sleep(1)

        logger.info("[riot] clicking it away")
        center = pyautogui.center(location)
        above_center = pyautogui.Point(center.x, center.y - 300)
        _click(above_center)


def _get_button_location(button, confidence=0.999):
    # locate button on the screen
    try:
        return pyautogui.locateOnScreen(
            button,
            region=_get_scrcpy_rect(),
            confidence=confidence,
        )
    except pyautogui.ImageNotFoundException:
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

        if last_x2_money_check is None or (datetime.now() - last_x2_money_check).seconds > 600:
            increase_multiplier()
            last_x2_money_check = datetime.now()

        # It's not immediately that this money thing comes again. No need to waste resources...
        time.sleep(40)

        # TODO: riot lost
        # TODO: x2 money nearly gone (check every 10 minutes or so)


def increase_multiplier():
    logging.info('[x2 money] first click')
    x2_button = _click_on_button(x2_money, wait_for_disappearance=False)

    logging.info('[x2 money] claim button')
    _click_on_button(x2_claim_button, wait_for_disappearance=False)
    _click_on_button(x2_claim_button, wait_for_disappearance=False)

    time.sleep(1)

    while _get_button_location(x2_claim_button) is not None:
        logging.info('[x2 money] get out')
        _click(x2_button)
        time.sleep(1)

    logging.info('[x2 money] finished')


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        pool.submit(run_scrcpy_endlessly)
        time.sleep(5)  # Wait a bit before starting the rest
        pool.submit(click_on_buttons)
