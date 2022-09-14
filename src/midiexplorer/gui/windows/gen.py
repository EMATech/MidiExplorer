# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Generator window and management.
"""

from typing import Any, Optional

import mido
from dearpygui import dearpygui as dpg

from midiexplorer.dpg_helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.gui.config import DEBUG
from midiexplorer.gui.logger import Logger


def create() -> None:
    """Creates the generator window.

    """
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
    """Callback to decode raw MIDI message input.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as error:
        decoded = f"Warning: {error!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)
