# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Logging window
"""

import sys
from typing import Any, Optional

from dearpygui import dearpygui as dpg

from gui.config import DEBUG
from gui.logger import Logger


def create() -> None:
    # TODO: allow logging to file
    # TODO: append/overwrite

    with dpg.window(
            tag='log_win',
            label="Log",
            width=1920,
            height=225,
            pos=[0, 815],
            show=DEBUG,
    ):
        pass


def toggle(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    dpg.configure_item('log_win', show=not dpg.is_item_visible('log_win'))
