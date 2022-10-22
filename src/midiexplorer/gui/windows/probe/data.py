# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe data management.
"""
from typing import Callable, Any, Optional

import mido
from dearpygui import dearpygui as dpg

import midiexplorer.midi
from midiexplorer.dpg_helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.dpg_helpers.constants.slots import Slots
from midiexplorer.gui.config import START_TIME, DEBUG
from midiexplorer.gui.logger import Logger
from midiexplorer.gui.windows.probe.blink import _mon, _note_on, _note_off, reset_mon
from midiexplorer.gui.windows.probe.settings import notation_modes
from midiexplorer.midi.constants import NOTE_OFF_VELOCITY
from midiexplorer.midi.decoders.sysex import DecodedUniversalSysExPayload, DecodedSysEx

US2MS = 1000  # microseconds to milliseconds ratio

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
probe_data_counter = 0
previous_timestamp = START_TIME
selectables = []


def _selection(sender, app_data, user_data):
    """History row selection management.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    # FIXME: add a data structure tracking selected items to only deselect the one(s)
    for item in user_data:
        if item != sender:
            dpg.set_value(item, False)

    reset_mon()  # Reset Monitor to clear any spurious data from previous receive or selection

    # TODO: Decode as a static display aka ignore blink

    raw_message = dpg.get_value(
        dpg.get_item_children(
            dpg.get_item_parent(sender),
            slot=Slots.MOST
        )[6]
    )
    message = mido.Message.from_hex(raw_message)
    decode(message, static=True)


def add(timestamp: float, source: str, data: mido.Message) -> None:
    """Decodes and presents data received from the probe.

    :param timestamp: System timestamp
    :param source: Input name
    :param data: MIDI data

    """
    global previous_timestamp

    logger = Logger()

    logger.log_debug(f"Adding data from {source} to probe at {timestamp}: {data!r}")

    # Compute timestamp and delta ASAP
    time_stamp = (timestamp - START_TIME) * US2MS
    delta = "0.32"  # Minimum delay between MIDI messages on the wire is 320us
    # FIXME: data.time can also be 0 when using rtmidi time delta. How do we discriminate? Use another property in mido?
    if data.time:
        delta = data.time * US2MS
        logger.log_debug("Timing: Using rtmidi time delta")
    elif previous_timestamp is not None:
        logger.log_debug("Timing: Rtmidi time delta not available. Computing timestamp locally.")
        delta = (timestamp - previous_timestamp) * US2MS
    previous_timestamp = timestamp

    chan_val, data0_name, data0_val, data0_dec, data1_name, data1_val, data1_dec = decode(data)

    _add_data_history(data, source, time_stamp, delta, chan_val, data0_name, data0_val, data0_dec,
                      data1_name, data1_val, data1_dec)


def _add_data_history(data, source, time_stamp, delta, chan_val, data0_name, data0_val, data0_dec, data1_name,
                      data1_val, data1_dec):
    global probe_data_counter, selectables

    # TODO: insert new data at the top of the table
    previous_data = probe_data_counter

    # Flush data after a certain amount to avoid memory leak issues
    # TODO: add setting
    if probe_data_counter >= 250:
        # TODO: serialize chunk somewhere to allow unlimited scrolling when implemented
        _clear_probe_data_table()

    probe_data_counter += 1

    with dpg.table_row(parent='probe_data_table', label=f'probe_data_{probe_data_counter}',
                       before=f'probe_data_{previous_data}'):

        # Source
        target = f'selectable_{probe_data_counter}'
        dpg.add_selectable(label=source, span_columns=True, tag=target)
        selectables.append(target)
        dpg.configure_item(target, callback=_selection, user_data=selectables)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(source)

        # Timestamp (ms)
        dpg.add_text(f"{time_stamp:n}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{time_stamp}")

        # Delta (ms)
        dpg.add_text(f"{delta:n}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{delta}")

        # Raw message
        raw_label = data.hex()
        dpg.add_text(raw_label)
        tooltip_conv(raw_label, data.bin())

        # Decoded message
        if DEBUG:
            dec_label = repr(data)
            dpg.add_text(dec_label)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(dec_label)

        # Status
        status_byte = midiexplorer.midi.mido2standard.get_status_by_type(data.type)
        stat_label = midiexplorer.midi.constants.STATUS_BYTES[status_byte]
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
        dpg.add_text(chan_label)
        tooltip_conv(chan_label, chan_val, hlen=1, dlen=2, blen=4)

        # Helper function equivalent to str() but avoids displaying 'None'.
        xstr: Callable[[Any], str] = lambda s: '' if s is None else str(s)

        if data0_dec:
            dpg.add_text(str(data0_dec))
        else:
            dpg.add_text(xstr(data0_val))
        prefix0 = ""
        if data0_name:
            prefix0 = data0_name + ": "
        tooltip_conv(prefix0 + xstr(data0_dec if data0_dec else data0_val), data0_val, blen=7)

        dpg.add_text(xstr(data1_val))
        prefix1 = ""
        if data1_name:
            prefix1 = data1_name + ": "
        tooltip_conv(prefix1 + xstr(data1_dec if data1_dec else data1_val), data1_val, blen=7)

    # TODO: per message type color coding
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('probe_data_table_autoscroll'):
        dpg.set_y_scroll('hist_det', -1.0)

    # Single selection
    # FIXME: add a data structure tracking selected items to only deselect the one(s)
    for item in selectables:
        dpg.set_value(item, False)  # Deselect all items upon receiving new data


def decode(data: mido.Message, static: bool = False):
    """Decodes the data to display into the probe monitor.

    :param data: MIDI data.
    :param static: Live or static mode
    :return: Channel value, data 1 & 2 names, values and decoded.

    """

    reset_mon(static=True)  # Reset monitor before decoding to avoid keeping old data from selected history row.

    # Status
    _mon(data.type, static)

    # Channel
    chan_val = None
    if hasattr(data, 'channel'):
        _mon('c', static)  # CHANNEL
        _mon(data.channel, static)
        chan_val = data.channel
    else:
        _mon('s', static)  # SYSTEM

    # Data 1 & 2
    data0_name: str | False = False
    data0_val: int | tuple | None = None
    data0_dec: str | False = False
    data1_name: str | False = False
    data1_val: int | None = None
    data1_dec: str | False = False
    if 'note' in data.type:
        if dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY:
            _mon('note_off', static)
        # Keyboard
        if 'on' in data.type and not (
                dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY
        ):
            _note_on(data.note, static)
        else:
            _note_off(data.note, static)
        data0_name = "Note"
        data0_val: int = data.note
        data0_dec = notation_modes.get(dpg.get_value('notation_mode')).get(data.note)
        data1_name = "Velocity"
        data1_val: int = data.velocity
    elif 'polytouch' == data.type:
        if static:
            _note_on(data.note, static)
        data0_name = "Note"
        data0_val: int = data.note
        data0_dec = notation_modes.get(dpg.get_value('notation_mode')).get(data.note)
        data1_val: int = data.value
    elif 'control_change' == data.type:
        _mon(f'cc_{data.control}', static)
        data0_name = "Controller"
        data0_val: int = data.control
        data0_dec = midiexplorer.midi.constants.CONTROLLER_NUMBERS.get(data.control)
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
        decoded_sysex = DecodedSysEx(data.data)
        _update_sysex_gui(decoded_sysex)
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


def _set_value_preconv(source: str, value: int | tuple[int] | list[int]) -> None:
    """Set value and pre-converted values.

    :param source: Value source tag name
    :param value: Value to set
    """
    dpg.set_value(source, str(value))
    if source == 'syx_payload':
        dpg.set_value(f'{source}_char', conv2char(value))
    dpg.set_value(f'{source}_hex', conv2hex(value))
    dpg.set_value(f'{source}_bin', conv2bin(value))
    dpg.set_value(f'{source}_dec', conv2dec(value))


def _update_sysex_gui(decoded: DecodedSysEx):
    """Populate decoded system exclusive values in the GUI.

    :param decoded: Decoded system exclusive message from _decode_sysex().
    """

    dpg.set_value('syx_id_group', decoded.identifier.group)
    dpg.set_value('syx_id_region', decoded.identifier.region)
    dpg.set_value('syx_id_name', decoded.identifier.name)
    _set_value_preconv('syx_id_val', decoded.identifier.value)
    _set_value_preconv('syx_device_id', decoded.device_id)
    _set_value_preconv('syx_payload', decoded.payload.value)
    if isinstance(decoded.payload, DecodedUniversalSysExPayload):
        dpg.hide_item('syx_payload_container')
        if decoded.payload.sub_id1_value:
            dpg.set_value('syx_sub_id1_name', decoded.payload.sub_id1_name)
            _set_value_preconv('syx_sub_id1_val', decoded.payload.sub_id1_value if not None else "")
            dpg.show_item('syx_sub_id1')
        else:
            dpg.hide_item('syx_sub_id1')
        if decoded.payload.sub_id2_value:
            dpg.set_value('syx_sub_id2_name', decoded.payload.sub_id2_name)
            _set_value_preconv('syx_sub_id2_val', decoded.payload.sub_id2_value if not None else "")
            dpg.show_item('syx_sub_id2')
        else:
            dpg.hide_item('syx_sub_id2_value')
        dpg.show_item('syx_decoded_payload')
    else:
        dpg.hide_item('syx_decoded_payload')
        dpg.show_item('syx_payload_container')


def convert_to(unit: chr, values: int | tuple[int] | list[int], length, padding) -> str:
    """Converts a single integer or a group to a text representation in the specified unit.

    :param unit: Unit to convert to (Format specification type)
    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in unit format
    """
    unit_name = "Unknown"
    if unit == 'X':
        unit_name = "Hexadecimal"
    if unit == 'd':
        unit_name = "Decimal"
    if unit == 'b':
        unit_name = "Binary"
    if unit == 'c':
        unit_name = "Character"
    unit_name_padding = 12 - len(unit_name)

    converted_values = ""
    if values is not None:
        if isinstance(values, int):
            converted_values += f"{' ':{padding}}{values:0{length}{unit}}"
        else:
            for value in values:
                converted_values += f"{' ':{padding}}{value:0{length}{unit}}"
    return f"{unit_name}:{' ':{unit_name_padding}}{converted_values.rstrip()}"


def conv2hex(values: int | tuple[int] | list[int], length: int = 2, padding: int = 7) -> str:
    """Converts a group of integers or a single integer to its hexadecimal text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in hexadecimal format
    """
    return convert_to('X', values, length, padding)


def conv2dec(values: int | tuple[int] | list[int], length: int = 3, padding: int = 6) -> str:
    """Converts a group of integers or a single integer to its decimal text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in decimal format
    """
    return convert_to('d', values, length, padding)


def conv2bin(values: int | tuple[int] | list[int], length: int = 8, padding: int = 1) -> str:
    """Converts a group of integers or a single integer to its binary text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in binary format
    """
    return convert_to('b', values, length, padding)


def conv2char(values: int | tuple[int] | list[int]) -> str:
    """Converts a group of integers or a single integer to its ASCII text representation.

    :param values: Value(s) to convert
    :return: Text representation of value(s) in ASCII format
    """
    return convert_to('c', values, 1, 8)


def tooltip_conv(title: str, values: int | tuple[int] | list[int] | None = None,
                 hlen: int = 2, dlen: int = 3, blen: int = 8) -> None:
    """Adds a tooltip with data converted to hexadecimal, decimal and binary.

    :param title: Tooltip title.
    :param values: Tooltip value(s)
    :param hlen: Hexadecimal length
    :param dlen: Decimal length
    :param blen: Binary length

    """
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text(f"{title}")
        hconv = conv2hex(values, hlen, blen - hlen + 1)
        dconv = conv2dec(values, dlen, blen - dlen + 1)
        bconv = conv2bin(values, blen)
        if values is not None:
            dpg.add_text()
            dpg.add_text(f"{hconv}")
            dpg.add_text(f"{dconv}")
            dpg.add_text(f"{bconv}")


def tooltip_preconv(static_title: str | None = None, title_value_source: str | None = None,
                    values_source: str | None = None) -> None:
    """Adds a tooltip with pre-converted data.

    :param static_title: Tooltip static title.
    :param title_value_source: Tooltip title text value source.
    :param values_source: Tooltip value(s) source tag name
    """
    with dpg.tooltip(dpg.last_item()):
        if static_title:
            dpg.add_text(static_title)
        if title_value_source:
            dpg.add_text(source=title_value_source)
        dpg.add_text()
        if values_source == 'syx_payload':
            dpg.add_text(source=f'{values_source}_char')
        dpg.add_text(source=f'{values_source}_hex')
        dpg.add_text(source=f'{values_source}_dec')
        dpg.add_text(source=f'{values_source}_bin')


def _clear_probe_data_table(
        sender: None | int | str = None, app_data: Any = None, user_data: Optional[Any] = None) -> None:
    """Clears the data table.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    global selectables, probe_data_counter

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    selectables.clear()
    probe_data_counter = 0

    dpg.delete_item('probe_data_table', children_only=True, slot=Slots.MOST)
    _init_details_table_data()


def _init_details_table_data() -> None:
    """Initial table data for reverse scrolling.

    """
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass
