# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Generator window and management
"""

from typing import Any, Optional

import sys
from dearpygui import dearpygui as dpg

import mido
from gui.logger import Logger


def create() -> None:
    with dpg.value_registry():
        dpg.add_string_value(tag='generator_decoded_message', default_value='')

    with dpg.window(
            tag='gen_win',
            label="Generator",
            width=1005,
            height=110,
            no_close=True,
            collapsed=False,
            pos=[900, 705]
    ):
        dpg.add_input_text(
            tag='generator_raw_message',
            label="Raw Message",
            hint="XXYYZZ (HEX)",
            hexadecimal=True,
            callback=decode_callback
        )
        dpg.add_input_text(
            label="Decoded",
            readonly=True,
            hint="Automatically decoded raw message",
            source='generator_decoded_message'
        )
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)


def decode_callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)
