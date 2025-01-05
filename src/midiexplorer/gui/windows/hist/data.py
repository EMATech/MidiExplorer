# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
History data management.
"""

from typing import Any, Callable, Optional

import midi_const
import mido
from dearpygui import dearpygui as dpg

import midiexplorer.midi.mido2standard
from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers.callbacks.debugging import \
    enable as enable_dpg_cb_debugging
from midiexplorer.gui.helpers.constants.slots import Slots
from midiexplorer.gui.helpers.convert import tooltip_conv
from midiexplorer.gui.helpers.logger import Logger
from midiexplorer.gui.windows.mon import notation_modes
from midiexplorer.midi.timestamp import Timestamp

S2MS = 1000  # Seconds to milliseconds ratio
MAX_SIZE = 250  # Data table struggles with too many elements.

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
hist_data_counter = 0
selected = None


def clear_hist_data_table(
        sender: None | int | str = None, app_data: Any = None, user_data: Optional[Any] = None) -> None:
    """Clears the history data table.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    global hist_data_counter, selected

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    hist_data_counter = 0
    selected = None

    dpg.delete_item('hist_data_table', children_only=True, slot=Slots.MOST)


def add(data: mido.Message, source: str, destination: str, timestamp: Timestamp) -> None:
    """Adds data to the history table.

    :param data: Midi message
    :param source: Source name
    :param destination: Destination name
    :param timestamp: Message data timestamp

    """
    global hist_data_counter, selected

    logger = Logger()

    # Unselect
    if selected is not None:
        dpg.set_value(selected, False)  # Deselect all items upon receiving new data

    # Flush data after a certain amount to avoid memory leak issues
    # TODO: add setting
    if hist_data_counter >= MAX_SIZE:
        # TODO: serialize chunk somewhere to allow unlimited scrolling when implemented
        clear_hist_data_table()

    chan_val, data0_name, data0_val, data0_dec, data1_name, data1_val, data1_dec = decode(data)

    # FIXME: data.time can also be 0 when using rtmidi time delta. How do we discriminate? Use another property in mido?
    if data.time and DEBUG:
        logger.log_debug("Timing: Using rtmidi time delta")
        delta = data.time
    else:
        logger.log_debug("Timing: Rtmidi time delta not available. Computing timestamp locally.")
        # FIXME: this delta is not relative to the same message train but to every handled messages!
        delta = timestamp.delta

    # Reversed order
    before = 0
    if dpg.get_value('hist_data_table_mode') == "Reversed" and hist_data_counter != 0:
        before = f'hist_data_{hist_data_counter - 1}'

    with dpg.table_row(
            tag=f'hist_data_{hist_data_counter}',
            parent='hist_data_table',
            before=before,
    ):

        # Timestamp (s)
        dpg.add_text(f"{timestamp.value:12.4f}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{timestamp.value}")

        # Delta (ms)
        dpg.add_text(f"{delta * S2MS:12.4f}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{delta * S2MS}")

        # Source
        dpg.add_text(source)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(source)

        # Destination
        dpg.add_text(destination)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(destination)

        # Raw message
        raw_label = data.hex()
        dpg.add_text(raw_label)
        tooltip_conv(raw_label, data.bin())

        # Decoded message
        if DEBUG:
            dec_label = str(data)
            dpg.add_text(dec_label)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(dec_label)

        # Status
        status_byte = midiexplorer.midi.mido2standard.get_status_by_type(
            data.type
        )
        stat_label = midi_const.STATUS_BYTES[status_byte]
        dpg.add_text(stat_label)
        if hasattr(data, 'channel'):
            status_nibble = int((status_byte - data.channel) / 16)
            tooltip_conv(stat_label, status_nibble, hlen=1, dlen=2, blen=4)
        else:
            tooltip_conv(stat_label, status_byte)

        # Channel
        chan_label = "Global"
        if chan_val is not None:
            chan_label = chan_val + 1  # Human-readable format
        dpg.add_text(f'{chan_label: >2}')
        tooltip_conv(chan_label, chan_val, hlen=1, dlen=2, blen=4)

        # Helper function equivalent to str() but avoids displaying 'None'.
        xstr: Callable[[Any], str] = lambda s: '' if s is None else str(s)

        # Data 1
        if data0_dec:
            dpg.add_text(str(data0_dec))
        else:
            dpg.add_text(f'{xstr(data1_val): >3}')
        prefix0 = ""
        if data0_name:
            prefix0 = data0_name + ": "
        tooltip_conv(prefix0 + xstr(data0_dec if data0_dec else data0_val), data0_val, blen=7)

        # Data 2
        dpg.add_text(f'{xstr(data1_val): >3}')
        prefix1 = ""
        if data1_name:
            prefix1 = data1_name + ": "
        tooltip_conv(prefix1 + xstr(data1_dec if data1_dec else data1_val), data1_val, blen=7)

        # Selectable
        target = f'selectable_{hist_data_counter}'
        dpg.add_selectable(span_columns=True, tag=target, callback=_selection, user_data=data)

    hist_data_counter += 1

    # TODO: per message type color coding
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('hist_data_table_mode') == "Auto-Scroll":
         dpg.set_y_scroll('hist_data_table', -1.0)


def _selection(sender, app_data, user_data):
    """History row selection management.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    global selected

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    # Single selection
    if selected is not None:
            dpg.set_value(selected, False)
    selected = sender

    message = user_data
    midiexplorer.gui.windows.mon.data.update_gui_monitor(message, static=True)

    # TODO: prevent overwriting user input
    if dpg.get_value('hist_data_to_gen'):
        dpg.set_value('generator_raw_message', message.hex())
        dpg.set_value('generator_decoded_message', message)
        dpg.set_item_user_data('generator_send_button', message)
        dpg.enable_item('generator_send_button')


def decode(data: mido.Message) -> tuple[int, int, int, int, int, int, int]:
    """Decodes the data.

    :param data: MIDI data.
    :return: Channel value, data 1 & 2 names, values and decoded.

    """
    # Channel
    chan_val = None
    if hasattr(data, 'channel'):
        chan_val = data.channel

    # Data 1 & 2
    data0_name: str | False = False
    data0_val: int | tuple | None = None
    data0_dec: str | False = False
    data1_name: str | False = False
    data1_val: int | None = None
    data1_dec: str | False = False
    if 'note' in data.type:
        data0_name = "Note"
        data0_val: int = data.note
        data0_dec = notation_modes.get(dpg.get_value('notation_mode')).get(data.note)
        data1_name = "Velocity"
        data1_val: int = data.velocity
    elif 'polytouch' == data.type:
        data0_name = "Note"
        data0_val: int = data.note
        data0_dec = notation_modes.get(dpg.get_value('notation_mode')).get(data.note)
        data1_val: int = data.value
    elif 'control_change' == data.type:
        data0_name = "Controller"
        data0_val: int = data.control
        data0_dec = midi_const.CONTROLLER_NUMBERS.get(data.control)
        data1_name = "Value"
        data1_val: int = data.value
    elif 'program_change' == data.type:
        data0_name = "Program"
        data0_val: int = data.program
        # TODO: Optionally decode General MIDI names.
    elif 'aftertouch' == data.type:
        data0_name = "Value"
        data0_val: int = data.value
    elif 'pitchwheel' == data.type:
        data0_name = "Pitch"
        data0_val: int = data.pitch
    elif 'sysex' == data.type:
        data0_name = "Data"
        data0_val: tuple = data.data
    elif 'quarter_frame' == data.type:
        data0_name = "Frame type"
        data0_val = data.frame_type  # TODO: decode
        data1_name = "Frame value"
        data1_val = data.frame_value  # TODO: decode
    elif 'songpos' == data.type:
        data0_name = "Position Pointer"
        data0_val = data.pos
    elif 'song_select' == data.type:
        data0_name = "Song #"
        data0_val = data.song

    return chan_val, data0_name, data0_val, data0_dec, data1_name, data1_val, data1_dec
