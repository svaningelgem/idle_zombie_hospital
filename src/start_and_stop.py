import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2

from src.common import click_on_button, continue_images, device, double_images, logger, \
    real_grab_scrcpy, run_scrcpy_endlessly

app_name = 'hotsiberians.idle.zombie.hospital.empire.manager.tycoon'


def _save_screen_to(dir_: str) -> None:
    path = Path('.') / dir_
    path.mkdir(parents=True, exist_ok=True)

    path /= f'{datetime.now():%Y%m%d_%H%M%S}.png'
    cv2.imwrite(str(path), real_grab_scrcpy(gray=False))


def _save_failed_screen(dir_: str) -> None:
    logger.error(f"Couldn't find '{dir_}' button...")
    _save_screen_to(dir_)


def _click_on_buttons():
    while True:
        logger.info('Starting next round.')

        device.start_app(app_name)
        double_img = click_on_button(double_images, wait_for_disappearance=False, waiting_time=20, check_riot_screen=False)
        _save_screen_to('start_stop')

        continue_img = click_on_button(continue_images, wait_for_disappearance=True, waiting_time=20, check_riot_screen=False)

        if not double_img:
            _save_failed_screen('double')
        if not continue_img:
            _save_failed_screen('continue')

        _save_screen_to('start_stop')
        device.stop_app(app_name)
        logger.info("Going to sleep for 50 minutes now... ZzZzZzzzz...")

        time.sleep(50*60)


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        pool.submit(run_scrcpy_endlessly)
        time.sleep(5)  # Wait a bit before starting the rest
        pool.submit(_click_on_buttons)
