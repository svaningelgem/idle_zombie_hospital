import time
from concurrent.futures import ProcessPoolExecutor

from src.common import click_on_buttons, run_scrcpy_endlessly

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        pool.submit(run_scrcpy_endlessly)
        time.sleep(5)  # Wait a bit before starting the rest
        pool.submit(click_on_buttons)
