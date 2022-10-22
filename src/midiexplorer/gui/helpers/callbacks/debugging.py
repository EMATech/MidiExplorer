# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Common callback debugging technique.
"""

import inspect
from typing import Any, Optional

from midiexplorer.gui.helpers.logger import Logger


def enable(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Enables callback debugging to the logger.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used by DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    # Debug
    stack_frame = inspect.stack()[1]
    logger.log_debug(f"Callback {stack_frame.function} ({stack_frame.filename} line {stack_frame.lineno}):")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")
