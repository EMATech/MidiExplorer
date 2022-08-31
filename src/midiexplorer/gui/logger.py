# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
GUI logging system.
"""
from dearpygui_ext.logger import mvLogger


class Logger:
    """Logger singleton.

    Allows sharing it globally.

    """
    __instance = None

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
        if Logger.__instance is None:
            Logger.__instance = super(Logger, cls).__new__(cls)
        return cls.__instance
