import ctypes
import time
from pathlib import Path

import pyautogui

# https://docs.microsoft.com/en-us/windows/win32/inputdev/wm-syskeydown
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
VK_SHIFT = 0x10
VK_ALT = 0x12  # VK_MENU in Windows-language
VK_S = 0x53


PostMessage = ctypes.windll.user32.PostMessageA
MapVirtualKey = ctypes.windll.user32.MapVirtualKeyA


win = next(
    w
    for w in pyautogui.getWindowsWithTitle('scrcpy')
    if w.title == 'scrcpy'
)


screenshot = Path(r'E:\idle_zombie_hospital\bin\screenshot.bmp')
screenshot.unlink(missing_ok=True)

# https://www.autoitscript.com/forum/topic/20925-send-keys-to-minimized-window/page/2/#comments
def makelong(loword, hiword):
    assert isinstance(loword, int)
    assert isinstance(hiword, int)

    return ((hiword & 0xFFFF) * 0x10000) | (loword & 0xFFFF)


hwnd = win._hWnd
WM_PLUGIN_BASE = 0x0400  # WM_USER
click = 1
key = 2
take_screenshot = 3
SDL_SCANCODE_S = 22
KMOD_LALT = 0x0100
KMOD_RALT = 0x0200
KMOD_LSHIFT = 0x0001
KMOD_RSHIFT = 0x0002
KMOD_ALT = KMOD_LALT | KMOD_RALT
KMOD_SHIFT = KMOD_LSHIFT | KMOD_RSHIFT


# PostMessage(hwnd, WM_PLUGIN_BASE, click, makelong(302, 175))
# PostMessage(hwnd, WM_PLUGIN_BASE, click, makelong(290, 500))
PostMessage(hwnd, WM_PLUGIN_BASE, key, makelong(SDL_SCANCODE_S, KMOD_LSHIFT|KMOD_LALT))
# PostMessage(hwnd, WM_PLUGIN_BASE, take_screenshot, 0)


time.sleep(2)
print('screenshot is: ', 'THERE !!!' if screenshot.exists() else ' -- ')
