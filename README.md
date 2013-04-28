background
==========

Library for Python applications that run in the background. The idea is to let
those programs run unobtrusive tray icons and global hotkeys to interface with
the user once in a while.

Windows support only for the moment.


Tray Icon
---------

`tray` allows the creation of a tray icon, with name, icon, menu and left/right
click handlers.


Notifications
-------------

`notify` displays a balloon notification over the created tray icon (or creates
one if necessary). Has handlers for click and fade events.


Global Hotkeys
--------------

`register_hotkey` and `register_many_hotkeys` allows creates global hotkeys
that invoke the supplied callbacks. Keys can be entered as keycode, character
value and descriptive string ("enter").


Clipboard
---------

Get and set clipboard contents. Allows to retrieve the files the user has
copied, too.
