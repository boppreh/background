from PyQt4 import QtGui
from threading import Thread, Lock
import atexit
import sys, os
import re

class _SimpleTray(QtGui.QSystemTrayIcon):
    """ Creates a new tray icon application in blocking fashion.  """
    instance = None

    def __init__(self, hover_name, icon_path, menu_actions,
                 on_click, on_double_click, lock):

        app = QtGui.QApplication(sys.argv)
        super(_SimpleTray, self).__init__(app)

        self.setToolTip(hover_name)
        self.setIcon(QtGui.QIcon(icon_path))
        self.activated.connect(self.click_handler)
        self.messageClicked.connect(lambda: self.notification_click_handler())
        self.setContextMenu(_make_menu(menu_actions, self))
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.show()

        _SimpleTray.instance = self
        lock.release()
        atexit.register(destroy)
        app.exec_()

    def click_handler(self, reason):
        if reason == QtGui.QSystemTrayIcon.Trigger:
            self.on_click()
        elif reason == QtGui.QSystemTrayIcon.DoubleClick:
            self.on_double_click()

    def destroy(self):
        self.hide()
        self.parent().exit()
        _SimpleTray.instance = None

class Icon(object):
    """ Icons for notification balloons.  """
    none = QtGui.QSystemTrayIcon.NoIcon
    information = QtGui.QSystemTrayIcon.Information
    warning = QtGui.QSystemTrayIcon.Warning
    critical = QtGui.QSystemTrayIcon.Critical

def notify(title='Notification', message=' ',
           on_click=lambda: None,
           icon=Icon.information, duration=10.0):
    """
    Displays a balloon notification from the tray icon.

    on_click is a callback to be called in case the balloon is clicked.
    """
    if _SimpleTray.instance is None:
        tray()
    _SimpleTray.instance.showMessage(title, message, icon, duration * 1000)
    _SimpleTray.instance.notification_click_handler = on_click

def destroy():
    """
    Destroys the current tray icon application.
    """
    if _SimpleTray.instance is None:
        return
    _SimpleTray.instance.destroy()

def quit():
    """
    Destroys the current tray icon and calls exit() to quit all threads.
    """
    destroy()
    exit()

def _format_name(name):
    return re.sub('([A-Z])', r' \1', name).replace('_', ' ').strip().title()

def _make_menu(menu_actions, parent=None):
    trayIconMenu = QtGui.QMenu(None)

    for func in menu_actions:
        if func is not None:
            name = _format_name(func.func_name)
            # 'triggered' sends a boolean parameter that must be ignored.
            func_handler = lambda b, func=func: func()
            action = QtGui.QAction(name, parent, triggered=func_handler)
            trayIconMenu.addAction(action)
        else:
            trayIconMenu.addSeparator()

    return trayIconMenu

def tray(hover_name=None,
         icon_path='images/heart.svg',
         menu_actions=[quit],
         on_click=lambda: None,
         on_double_click=lambda: os.startfile('.')):
    """
    Creates a new tray icon and starts processing messages for it. This is a
    non-blocking call that starts a new thread to process events for this tray
    icon.

    hover_name is the name that will appear in a tooltip if the user passes
    the mouse over the icon. If no name is given, the current script name will
    be used.

    icon_path is the path of the .ico file that will be used as icon.

    menu_actions is a list of functions and None values acting as Separator
    instances. If a list of functions is given, the name of each option will be
    extracted from the function's func_name and None objects will be rendered
    as separators. If no function is given, a simple "Quit" option is used.

    on_click function to be called when the icon is clicked.

    on_double_click function to be called when the icon is double clicked. If
    no callback is specified, by default it opens the current directory.
    """
    if hover_name is None:
        if sys.argv[0]:
            script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
            hover_name = _format_name(script_name)
        else:
            hover_name = 'Tray Application from Interpreter'

    lock = Lock()
    lock.acquire()

    args = (hover_name, icon_path, menu_actions,
            on_click, on_double_click, lock)
    Thread(target=_SimpleTray, args=args).start()
    lock.acquire()
    return _SimpleTray.instance

if __name__ == '__main__':
    def testFunction(): print 'hello'
    tray('Tray Test Module', menu_actions=[testFunction, None, lambda: quit()])
    notify('Title', 'Message.')
