from win32api import *
from win32gui import *
from win32con import *
import win32con
import win32api
import ctypes
import sys, os
from time import sleep

class _BaseMenu(object):
    """ Base class for the objects that appear in a menu. """
    @staticmethod
    def create_from(options):
        _BaseMenu.next_menu_id = 1023
        _BaseMenu.menu_actions = {}

        popup_menu = CreatePopupMenu()
        for option in options:
            option._create_on(popup_menu)
        return popup_menu

class Separator(_BaseMenu):
    """ Class for a menu option that is a simple horizontal line. """
    def _create_on(self, menu):
        return AppendMenu(menu, MF_SEPARATOR, _BaseMenu.next_menu_id, '')

class MenuOption(_BaseMenu):
    """
    Class for a menu option that displays a name, optionally with an icon, and
    calls a given function when selected by the user.
    """
    def __init__(self, title, callback, icon=None):
        """
        Creates a new simple menu option.

        title is the name that will appear on the line.

        callback is the function to be called when this option is selected.

        icon is the path of the .ico file to the displayed before the title.
        """
        self.title = title
        self.callback = callback
        self.icon = icon

    def _create_on(self, menu):
        _BaseMenu.menu_actions[_BaseMenu.next_menu_id] = self.callback
        AppendMenu(menu, MF_STRING, self.next_menu_id, self.title)
        _BaseMenu.next_menu_id += 1

class SubMenu(_BaseMenu):
    """
    Class for a menu option that displays another menu when selected by the
    user.
    """
    def __init__(self, title, options, icon=None):
        """
        Creates a new option that gives a submenu.

        title is the name that will appear on the line.

        options is a list of other Separator, MenuOption or SubMenu instances.

        icon is the path of the .ico file to the displayed before the title.
        """
        self.title = title
        self.options = options
        self.icon = icon

    def _create_on(self, menu):
        sub_menu = CreatePopupMenu()
        for option in self.options:
            option._create_on(sub_menu)
        AppendMenu(menu, MF_POPUP, sub_menu, self.title)


class TrayIcon(object):
    """
    Singleton class for a tray icon. Has support for notifications (the little
    balloons near the bottom right corner), right click menus (with sub-menus)
    and callbacks for each menu item, left click on the icon or on the
    notification balloon.

    It is advised to create new instances using the tray() module function.
    """

    instance_created = False
    instance = None

    CLICK = WM_LBUTTONUP
    DOUBLE_CLICK = WM_LBUTTONDBLCLK
    BALLOON_CLICK = 1029
    BALLOON_FADE = 1028

    def __init__(self,
                 hover_name='Tray Icon',
                 icon_path=None,
                 menu=[],
                 actions={}):

        self._create_window(hover_name)
        self._create_icon(hover_name, icon_path)
        self.menu = menu
        self.actions = actions

    def _create_window(self, hover_name):
        wc = WNDCLASS()
        self.hinst = wc.hInstance = GetModuleHandle(None)
        wc.lpszClassName = hover_name
        wc.style = CS_VREDRAW | CS_HREDRAW
        wc.hCursor = LoadCursor(0, IDC_ARROW)
        wc.lpfnWndProc = {
            WM_COMMAND: self._command,
            WM_USER + 20: self._receive_event,
            WM_DESTROY: self._destroy
        }
        style = WS_OVERLAPPED | WS_SYSMENU
        class_atom = RegisterClass(wc)
        self.hwnd = CreateWindow(class_atom, 'Taskbar', style, 0, 0,
                                 CW_USEDEFAULT, CW_USEDEFAULT, 0, 0, self.hinst,
                                 None)
        UpdateWindow(self.hwnd)

    def _destroy(self, hwnd, msg, wparam, lparam):
        Shell_NotifyIcon(NIM_DELETE, (self.hwnd, 0))
        PostQuitMessage(0)

    def _create_icon(self, hover_name, icon_path):
        if icon_path:
            icon_path = os.path.abspath(os.path.join(sys.path[0], icon_path))
            icon_flags = LR_LOADFROMFILE | LR_DEFAULTSIZE
            self.hicon = LoadImage(self.hinst, icon_path, IMAGE_ICON, 0, 0,
                                   icon_flags)
        else:
            self.hicon = LoadIcon(0, IDI_APPLICATION)

        flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid = (self.hwnd, 0, flags, WM_USER + 20, self.hicon, hover_name)
        Shell_NotifyIcon(NIM_ADD, nid)

    def _command(self, hwnd, msg, wparam, lparam):
        _BaseMenu.menu_actions[LOWORD(wparam)]()

    def _receive_event(self, hwnd, msg, wparam, lparam):
        if lparam == WM_RBUTTONUP:
            self.last_menu_id = 1023
            self.menu_actions = {}
            self._show_menu()
        elif lparam in self.actions:
                self.actions[lparam]()

    def _show_menu(self):
        menu = _BaseMenu.create_from(self.menu)
        pos = GetCursorPos()
        SetForegroundWindow(self.hwnd)
        TrackPopupMenu(menu, TPM_LEFTALIGN, pos[0], pos[1], 0,
                       self.hwnd, None)
        PostMessage(self.hwnd, WM_NULL, 0, 0)

    def notify(self, title, message):
        Shell_NotifyIcon(NIM_MODIFY,
                         (self.hwnd, 0, NIF_INFO, WM_USER + 20,
                          self.hicon, 'Balloon Tooltip', message, 200,
                          title))

    def destroy(self):
        DestroyWindow(TrayIcon.instance.hwnd)


def notify(title='Notification', message=' ', on_click=None, on_closed=None):
    """
    Displays a balloon notification from the tray icon.

    on_click is a callback to be called in case the balloon is clicked.

    on_closed is a callback to be called when the balloon fades naturally or the
    user clicks the X button to close it.
    """
    if not TrayIcon.instance_created:
        tray()
        while not TrayIcon.instance:
            sleep(0.001)

    actions = TrayIcon.instance.actions
    actions[TrayIcon.BALLOON_CLICK] = on_click or (lambda: None)
    actions[TrayIcon.BALLOON_FADE] = on_closed or (lambda: None)

    TrayIcon.instance.notify(title, message)

def destroy():
    """
    Destroys the current tray icon application.
    """
    TrayIcon.instance.destroy()

def quit():
    """
    Destroys the current tray icon and calls exit() to quit all threads.
    """
    destroy()
    exit()

def _convert_function_to_option(function):
    if function:
        name = function.func_name.replace('_', ' ').title()
        return MenuOption(name, function)
    else:
        return Separator()

def tray(hover_name=None,
         icon_path=None,
         menu=[],
         on_click=None,
         on_double_click=None):
    """
    Creates a new tray icon and starts processing messages for it. This is a
    non-blocking call that starts a new thread to process events for this tray
    icon.

    hover_name is the name that will appear in a tooltip if the user passes
    the mouse over the icon. If no name is given, the current script name will
    be used.

    icon_path is the path of the .ico file that will be used as icon.

    menu is either a list of functions, or a list of MenuOption, SubMenu and
    Separator instances. If a list of functions is given, the name of each
    option will be extracted from the function's func_name and None objects
    will be rendered as separators. If not function is given, a simple "Quit"
    option is used.

    on_click function to be called when the icon is clicked.

    on_double_click function to be called when the icon is double clicked. If
    no callback is specified, by default it opens the current directory.
    """
    if hover_name is None:
        import sys
        if sys.argv[0]:
            from os import path
            script_name = path.basename(sys.argv[0]).rsplit('.')[0]
            hover_name = script_name.replace('_', ' ').title()
        else:
            hover_name = 'Tray Application from Interpreter'

    menu = menu or [quit]

    if any(map(callable, menu)):
        menu = map(_convert_function_to_option, menu)

    on_click = on_click or (lambda: None)
    on_double_click = on_double_click or (lambda: os.startfile('.'))

    TrayIcon.instance_created = True

    def start_tray_application():
        actions = {}
        actions[TrayIcon.CLICK] = on_click
        actions[TrayIcon.DOUBLE_CLICK] = on_double_click

        TrayIcon.instance = TrayIcon(hover_name, icon_path, menu, actions)
        PumpMessages()

    from threading import Thread
    Thread(target=start_tray_application).start()

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


from win32com.shell import shell, shellcon
from os import path
home_location = path.expanduser('~')
downloads_location = path.join(home_location, 'Downloads')
desktop_location = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)

if __name__ == '__main__':
    #notify('Press ^q to quit.')
    def a():
        print get_selected()
    register_hotkey('space', a)
    #print get_clipboard()
