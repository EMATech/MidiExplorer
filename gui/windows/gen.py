import sys
from typing import Any, Optional

import mido
from dearpygui import dearpygui as dpg

from gui.logger import Logger


def create():
    with dpg.value_registry():
        dpg.add_string_value(tag='generator_decoded_message', default_value='')

    with dpg.window(
            tag='gen_win',
            label="Generator",
            width=960,
            height=100,
            no_close=True,
            collapsed=False,
            pos=[960, 715]
    ) as gen_win:
        message = dpg.add_input_text(label="Raw Message", hint="XXYYZZ (HEX)", hexadecimal=True,
                                     callback=decode_callback)
        dpg.add_input_text(label="Decoded", readonly=True, hint="Automatically decoded raw message",
                           source='generator_decoded_message')
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)

    return gen_win


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
