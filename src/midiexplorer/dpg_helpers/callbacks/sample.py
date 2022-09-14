# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Sample DearPyGUI callback.

For reference only.
"""

from typing import Any, Optional

from midiexplorer.dpg_helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.gui.config import DEBUG


def callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Generic Dear PyGui callback for debug purposes.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used by DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)
