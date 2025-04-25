# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
GUI logging system.
"""
from enum import IntEnum

# from dearpygui_ext.logger import mvLogger
import dearpygui.dearpygui as dpg

from midiexplorer.__config__ import DEBUG

TRANSPARENT = (0, 0, 0, 0)
GREEN = (0, 255, 0, 255)
BLUE = (64, 128, 255, 255)
WHITE = (255, 255, 255, 255)
YELLOW = (255, 255, 0, 255)
RED = (255, 0, 0, 255)


class LoggingLevel(IntEnum):
    """Logging levels enum.

    """
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


class mvLogger:
    """Logger.

    Borrowed and modified from DearPyGUI_Ext for text selection
    See: https://github.com/hoffstadt/DearPyGui_Ext/issues/1
    MIT License
    Copyright (c) 2021 Raylock, LLC

    FIXME: Multiline messages are not displayed correctly (Only first line)
    """
    def __init__(self, parent=None):

        self.log_level = 0
        self._auto_scroll = True
        self.filter_id = None
        if parent:
            self.window_id = parent
        else:
            self.window_id = dpg.add_window(label="mvLogger", pos=(200, 200), width=500, height=500)
        self.count = 0
        self.flush_count = 1000

        with dpg.group(horizontal=True, parent=self.window_id):
            dpg.add_checkbox(label="Auto-scroll", default_value=True,
                             callback=lambda sender: self.auto_scroll(dpg.get_value(sender)))
            dpg.add_button(label="Clear", callback=lambda: dpg.delete_item(self.filter_id, children_only=True))

        dpg.add_input_text(label="Filter", callback=lambda sender: dpg.set_value(self.filter_id, dpg.get_value(sender)),
                           parent=self.window_id)
        self.child_id = dpg.add_child_window(parent=self.window_id, autosize_x=True, autosize_y=True)
        self.filter_id = dpg.add_filter_set(parent=self.child_id)

        with dpg.theme() as bg_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, TRANSPARENT)
                dpg.add_theme_color(dpg.mvThemeCol_Button, TRANSPARENT)
        dpg.bind_item_theme(self.child_id, bg_theme)

        with dpg.theme() as self.trace_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, GREEN)

        with dpg.theme() as self.debug_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, BLUE)

        with dpg.theme() as self.info_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, WHITE)

        with dpg.theme() as self.warning_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, YELLOW)

        with dpg.theme() as self.error_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, RED)

        with dpg.theme() as self.critical_theme:
            with dpg.theme_component(0):
                dpg.add_theme_color(dpg.mvThemeCol_Text, RED)

    def auto_scroll(self, value):
        self._auto_scroll = value

    def _log(self, message, level):

        if level < self.log_level:
            return

        self.count += 1

        if self.count > self.flush_count:
            self.clear_log()

        theme = self.info_theme

        if level == LoggingLevel.TRACE:
            message = "[TRACE]       " + message
            theme = self.trace_theme
        elif level == LoggingLevel.DEBUG:
            message = "[DEBUG]       " + message
            theme = self.debug_theme
        elif level == LoggingLevel.INFO:
            message = "[INFO]        " + message
        elif level == LoggingLevel.WARNING:
            message = "[WARNING]     " + message
            theme = self.warning_theme
        elif level == LoggingLevel.ERROR:
            message = "[ERROR]       " + message
            theme = self.error_theme
        elif level == LoggingLevel.CRITICAL:
            message = "[CRITICAL]    " + message
            theme = self.critical_theme

        if DEBUG:
            new_log = dpg.add_button(
                label=message,
                parent=self.filter_id, filter_key=message,
                user_data=message, callback=lambda s, a, u: dpg.set_clipboard_text(u))
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text("Press to copy to clipboard")
        else:
            new_log = dpg.add_input_text(
                width=-1,  # Full
                parent=self.filter_id, filter_key=message,
                default_value=message, readonly=True,
                #multiline=True,
            )
        dpg.bind_item_theme(new_log, theme)
        if self._auto_scroll:
            dpg.set_y_scroll(self.child_id, -1.0)

    def log(self, message):
        self._log(message, LoggingLevel.TRACE)

    def log_debug(self, message):
        self._log(message, LoggingLevel.DEBUG)

    def log_info(self, message):
        self._log(message, LoggingLevel.INFO)

    def log_warning(self, message):
        self._log(message, LoggingLevel.WARNING)

    def log_error(self, message):
        self._log(message, LoggingLevel.ERROR)

    def log_critical(self, message):
        self._log(message, LoggingLevel.CRITICAL)

    def clear_log(self):
        dpg.delete_item(self.filter_id, children_only=True)
        self.count = 0


class Logger:
    """Logger singleton.

    Allows sharing it globally.

    """
    __instance: mvLogger | None = None
    # Allows logging messages before mvLogger window creation
    _startup_cache: (str, LoggingLevel) = []

    def __new__(cls, parent: None | int | str = None) -> mvLogger:
        """Instantiates a new logger or retrieves the existing one.

        :param parent: The window ID or tag to which the logger should be attached.
        :return: A logger instance.
        :raises: ValueError -- A parent is required to initialize the Logger.

        """
        if parent is None and Logger.__instance is None:
            raise ValueError("Please provide a parent to initialize the Logger")
        if parent is not None:
            Logger.__instance = mvLogger(parent)
            # Flush startup cache into window
            if cls._startup_cache:
                for item in cls._startup_cache:
                    Logger.__instance._log(*item)
                cls._startup_cache.clear()
        if Logger.__instance is None:
            Logger.__instance = super(Logger, cls).__new__(cls)
        return cls.__instance

    @staticmethod
    def log(message: str, level: LoggingLevel = LoggingLevel.TRACE):
        if isinstance(Logger.__instance, mvLogger):
            Logger.__instance._log(message, level)
        else:
            Logger._startup_cache.append((message, level))

    @staticmethod
    def log_debug(message: str):
        Logger.log(message, LoggingLevel.DEBUG)

    @staticmethod
    def log_warning(message: str):
        Logger.log(message, LoggingLevel.WARNING)

    @staticmethod
    def log_error(message: str):
        Logger.log(message, LoggingLevel.DEBUG)

    @staticmethod
    def log_critical(message: str):
        Logger.log(message, LoggingLevel.CRITICAL)
