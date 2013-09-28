import win32con
import os
from tray import *
from server import *

# Map common key names to their official names in the win32con module.
_replacement_hotkeys = {'BACKSPACE': 'BACK',
                        'CTRL': 'CONTROL',
                        'ESC': 'ESCAPE',
                        'ENTER': 'RETURN'}
keycodes = {}
# Prepare hotkeys for regular numbers (not from the numpad).
for k in map(str, range(1, 10)):
    keycodes[k] = ord(k)

# Prepare hotkeys for letter keys, a-z. No special character support yet.
import string
for k in string.uppercase:
    keycodes[k] = ord(k)

# Prepare named hotkeys ("escape", "return", etc) from the win32con module.
for k in dir(win32con):
    # Hotkey constants start with VK_ .
    if k.startswith('VK_'):
        # Prepare hotkey without the VK_ .
        keycodes[k[3:]] = getattr(win32con, k)
        # Prepare the same hotkey with spaces instead of underscores.
        keycodes[k[3:].replace('_', ' ')] = getattr(win32con, k)

# Prepare hotkeys for the "replacements", keys usually called one thing but
# named another in the win32con module (e.g. ENTER -> RETURN).
for k, new_k in _replacement_hotkeys.items():
    keycodes[k] = getattr(win32con, 'VK_' + new_k)

def _register_many_hotkeys_blocking(key_callback_pairs,
                         ctrl=False,
                         alt=False,
                         shift=False,
                         win=False):
    """
    Register a list of hotkeys and blocks listening for their events. For
    docs, see "register_many_hotkeys".
    """
    hotkeys = []

    modifiers = 0
    if ctrl: modifiers |= MOD_CONTROL
    if alt: modifiers |= MOD_ALT
    if shift: modifiers |= MOD_SHIFT
    if win: modifiers |= MOD_WIN

    for key, callback in key_callback_pairs:
        if type(key) == type(1):
            keycode = key
        elif key.upper() in keycodes:
            keycode = keycodes[key.upper()]
        else:
            raise KeyError('Unknown hotkey ' + key + '. Hotkey must be numeric \
    keycode or string from "background.keycodes" keys.')

        id = len(hotkeys)
        hotkeys.append(callback)
        ctypes.windll.user32.RegisterHotKey(None, id, modifiers, keycode)

    from ctypes import wintypes
    from ctypes import byref
    msg = wintypes.MSG()

    while ctypes.windll.user32.GetMessageA(byref(msg), None, 0, 0) != 0:
        if msg.message == win32con.WM_HOTKEY:
            hotkeys[msg.wParam]()
        else:
            ctypes.windll.user32.TranslateMessage(byref(msg))
            ctypes.windll.user32.DispatchMessageA(byref(msg))

def register_many_hotkeys(key_callback_pairs,
                         ctrl=False,
                         alt=False,
                         shift=False,
                         win=False):
    """
    Registers a group of global hotkeys, which invokes their respective
    callbacks any time the given key (with modifiers) is pressed, regardless of
    the application focused. The modifiers selected apply to all hotkeys in the
    list.

    This is a non-blocking function that spawns a new thread to listen for
    hotkey events.

    key_callback_pairs a list of (key, callback) pairs. "key" is the code of the
    desired key or a caseless string representation (e.g.: "F1", "tab", "enter",
    "a", "5"). All the accepted hotkey strings are listed in the
    "background.keycodes" dictionary. "callback" must be a function with no
    arguments to be invoked when the hotkey is activated.

    ctrl if the key should be pressed while the Ctrl key is pressed.

    alt if the key should be pressed while the Alt key is pressed.

    shift if the key should be pressed while the Shift key is pressed.

    win if the key should be pressed while the Win key is pressed (the key
    usually with the Windows logo between Ctrl and Alt).
    """
    args = (key_callback_pairs, ctrl, alt, shift, win)
    from threading import Thread
    Thread(target=_register_many_hotkeys_blocking, args=args).start()

def register_hotkey(key,
                    callback,
                    ctrl=False,
                    alt=False,
                    shift=False,
                    win=False):
    """
    Registers a new global hotkey, which invokes the callback any time the given
    key (with modifiers) is pressed, regardless of the application focused.

    This is a non-blocking function that spawns a new thread to listen for
    hotkey events.

    key the code of the desired key or a caseless string representation
    (e.g.: "F1", "tab", "enter", "a", "5"). All the accepted hotkey strings are
    listed in the "background.keycodes" dictionary.

    callback a function to be called when the hotkey is invoked

    ctrl if the key should be pressed while the Ctrl key is pressed.

    alt if the key should be pressed while the Alt key is pressed.

    shift if the key should be pressed while the Shift key is pressed.

    win if the key should be pressed while the Win key is pressed (the key
    usually with the Windows logo between Ctrl and Alt).
    """
    register_many_hotkeys([(key, callback)],
                          ctrl=ctrl,
                          alt=alt,
                          shift=shift,
                          win=win)

import win32clipboard

class Clipboard(object):
    def __enter__(self):
        win32clipboard.OpenClipboard()
        return self

    def __exit__(self, *exit_info):
        win32clipboard.CloseClipboard()

    def get(self, format):
        if win32clipboard.IsClipboardFormatAvailable(format):
            return win32clipboard.GetClipboardData(format)
        else:
            return None

    def set(self, format, data):
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(format, data)

clipboard = Clipboard()

def get_clipboard_as_text():
    with clipboard as c:
        return c.get(win32con.CF_TEXT)

def get_clipboard_as_filepaths():
    with clipboard as c:
        return c.get(win32clipboard.CF_HDROP)

def set_clipboard_as_text(text):
    with clipboard as c:
        return c.set(win32con.CF_TEXT, text)

get_clipboard = get_clipboard_as_text

def copy_selected():
    """
    Sends a Ctrl+C to the current window, hopefully copying the selected
    content to the clipboard, returning the clipboard contents copied.
    """
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(ord('C'), 0, 0, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0x2, 0)
    # Without this sleep the ctrl+c is sent, but the *previous* clipboard text
    # is read. Windows seems to need a "moment to think".
    sleep(0.01)
    return get_clipboard()


home_location = os.path.expanduser('~')
downloads_location = os.path.join(home_location, 'Downloads')
try:
    from win32com.shell import shell, shellcon
    desktop_location = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)
except:
    # TODO: Get desktop location in *nix.
    pass

if __name__ == '__main__':
    notify('a', 'v')
    #tray()
