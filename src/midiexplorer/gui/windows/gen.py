# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Generator window and management.
"""
import time
from typing import Any, Optional

import mido
from dearpygui import dearpygui as dpg

import midiexplorer.gui.windows.hist.data
from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.gui.helpers.logger import Logger
from midiexplorer.midi.timestamp import Timestamp


def create() -> None:
    """Creates the generator window.

    """
    with dpg.window(
            tag='gen_win',
            label="Generator",
            use_internal_label=False,
            width=dpg.get_viewport_width()/2,
            height=110,
            no_close=True,
            collapsed=False,
            pos=[dpg.get_viewport_width()/2, (dpg.get_viewport_height()/3*2)+20],
    ):
        with dpg.group(tag='generator_container'):
            dpg.add_input_text(
                tag='generator_raw_message',
                label="Raw Message",
                hint="XXYYZZ (HEX)",
                hexadecimal=True,
                callback=decode,
            )
            dpg.add_input_text(
                label="Decoded",
                readonly=True,
                hint="Automatically decoded raw message",
                tag='generator_decoded_message',
            )
        dpg.add_button(
            tag="generator_send_button",
            label="Send",
            enabled=False,
            callback=send,
        )


def toggle(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Callback to toggle the window visibility.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    dpg.configure_item('gen_win', show=not dpg.is_item_visible('gen_win'))

    menu_item = 'menu_tools_generator'
    if sender != menu_item:  # Update menu checkmark when coming from the shortcut handler
        dpg.set_value(menu_item, not dpg.get_value(menu_item))


def decode(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
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

    warning = None
    try:
        decoded: mido.Message = mido.Message.from_hex(app_data)
    except (TypeError, ValueError, IndexError) as error:
        warning = f"Warning: {error!s}"
        pass

    if warning is None:
        logger.log_debug(f"Raw message {app_data} decoded to: {decoded!r}.")
        dpg.set_value('generator_decoded_message', decoded)
        dpg.enable_item('generator_send_button')
        dpg.set_item_user_data('generator_send_button', decoded)
    else:
        logger.log_warning(f"Error decoding raw message {app_data}: {warning}")
        dpg.set_value('generator_decoded_message', warning)
        dpg.disable_item('generator_send_button')
        dpg.set_item_user_data('generator_send_button', None)


def send(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Callback to send raw MIDI message from input.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """

    # Compute timestamp and delta ASAP
    timestamp = Timestamp()

    logger = Logger()

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    port = dpg.get_item_user_data('gen_out')
    if port:
        port.port.send(user_data)
        midiexplorer.gui.windows.hist.data.add(data=user_data, source='Generator', destination=port.label,
                                               timestamp=timestamp)
    else:
        logger.log_warning("Generator output is not connected to anything.")
