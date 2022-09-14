# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Logging window.
"""

from typing import Any, Optional

from dearpygui import dearpygui as dpg

from midiexplorer.dpg_helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.gui.config import DEBUG


def create() -> None:
    """Creates the logging window.

    """
    # TODO: allow logging to file
    # TODO: append/overwrite modes

    with dpg.window(
            tag='log_win',
            label="Log",
            width=1905,
            height=230,
            pos=[0, 815],
            show=DEBUG,
    ):
        pass


def toggle(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Callback to toggle the logging window visibility.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    dpg.configure_item('log_win', show=not dpg.is_item_visible('log_win'))
