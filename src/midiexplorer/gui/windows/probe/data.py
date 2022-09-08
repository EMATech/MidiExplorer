# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe data management.
"""

from typing import Tuple, Callable, Any

import mido
from dearpygui import dearpygui as dpg

import midiexplorer.midi
from midiexplorer.gui.config import START_TIME, DEBUG
from midiexplorer.gui.logger import Logger
from midiexplorer.gui.windows.probe.blink import _mon, _note_on, _note_off
from midiexplorer.midi.constants import NOTE_OFF_VELOCITY

US2MS = 1000  # microseconds to milliseconds ratio

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
probe_data_counter = 0
previous_timestamp = START_TIME


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
    if data.time is not None:
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
    global probe_data_counter

    # TODO: insert new data at the top of the table
    previous_data = probe_data_counter
    probe_data_counter += 1

    # TODO: Flush data after a certain amount to avoid memory leak issues
    with dpg.table_row(parent='probe_data_table', label=f'probe_data_{probe_data_counter}',
                       before=f'probe_data_{previous_data}'):

        # Source
        dpg.add_selectable(label=source, span_columns=True)
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
        conv_tooltip(raw_label, data.bin())

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
            conv_tooltip(stat_label, status_nibble, hlen=1, dlen=2, blen=4)
        else:
            conv_tooltip(stat_label, status_byte)

        # Channel
        chan_label = "Global"
        if chan_val is not None:
            chan_label = chan_val + 1  # Human-readable format
        dpg.add_text(chan_label)
        conv_tooltip(chan_label, chan_val, hlen=1, dlen=2, blen=4)

        # Helper function equivalent to str() but avoids displaying 'None'.
        xstr: Callable[[Any], str] = lambda s: '' if s is None else str(s)

        if data0_dec:
            dpg.add_text(str(data0_dec))
        else:
            dpg.add_text(xstr(data0_val))
        prefix0 = ""
        if data0_name:
            prefix0 = data0_name + ": "
        conv_tooltip(prefix0 + xstr(data0_dec if data0_dec else data0_val), data0_val, blen=7)

        dpg.add_text(xstr(data1_val))
        prefix1 = ""
        if data1_name:
            prefix1 = data1_name + ": "
        conv_tooltip(prefix1 + xstr(data1_dec if data1_dec else data1_val), data1_val, blen=7)

    # TODO: per message type color coding
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('probe_data_table_autoscroll'):
        dpg.set_y_scroll('act_det', -1.0)


def decode(data: mido.Message):
    """Decodes the data to display into the probe monitor.

    :param data: MIDI data.
    :return: Channel value, data 1 & 2 names, values and decoded.
    """

    # Status
    _mon(data.type)

    # Channel
    chan_val = None
    if hasattr(data, 'channel'):
        _mon('c')  # CHANNEL
        _mon(data.channel)
        chan_val = data.channel
    else:
        _mon('s')  # SYSTEM

    # Data 1 & 2
    data0_name: str | False = False
    data0_val: int | tuple | None = None
    data0_dec: str | False = False
    data1_name: str | False = False
    data1_val: int | None = None
    data1_dec: str | False = False
    if 'note' in data.type:
        if dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY:
            _mon('note_off')
        # Keyboard
        if 'on' in data.type and not (
                dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY
        ):
            _note_on(data.note)
        else:
            _note_off(data.note)
        data0_name = "Note"
        data0_val: int = data.note
        # TODO: add preference for syllabic / EN / DE
        data0_dec = midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN.get(data.note)
        data1_name = "Velocity"
        data1_val: int = data.velocity
    elif 'polytouch' == data.type:
        data0_val: int = data.note
        # TODO: add preference for syllabic / EN / DE
        data0_dec = midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN.get(data.note)
        data1_val: int = data.value
    elif 'control_change' == data.type:
        _mon(f'cc_{data.control}')
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
        decoded_sysex = _decode_sysex(data)
        _mon_update_sysex(decoded_sysex)
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


def _decode_sysex(data):
    """System exclusive decoding.

    """
    logger = Logger()

    id_type: str = ""
    id_group: str = ""
    id_region: None | str = None
    id_val: None | int | Tuple = None
    id_name: str = "Undefined"
    device_id: None | int = None
    sub_id1_val: None | int = None
    sub_id1_name: str = ""
    sub_id2_val: None | int = None
    sub_id2_name: str = ""
    payload: None | int | Tuple = None
    default_name = "Undefined"

    # --------------------------------
    # Decode 1 or 3 byte IDs (page 34)
    # --------------------------------

    # Extract ID
    id_val = data.data[0]  # 1-byte ID or first byte of 3-byte ID
    syx_id_len = 1

    # Decode group
    id_group = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_GROUPS.get(id_val)

    if id_val == 0:
        # 3-byte ID
        syx_id_len = 3
        id_val = data.data[0:3]
        syx_region_idx = 1
    logger.log_debug(f"[SysEx] ID: {id_val}")

    # Decode region
    if syx_id_len == 1:
        id_region = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_REGIONS.get(id_val, "")
    elif syx_id_len == 3:
        id_region = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_REGIONS.get(id_val[syx_region_idx], "")
    else:
        raise ValueError("SysEx IDs are either 1 or 3 bytes long")

    # Decode ID
    if syx_id_len == 1:
        id_name = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID.get(id_val, default_name)
    if syx_id_len == 3:
        # TODO: optimise?
        id_name = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID.get(id_val[0], default_name)
        if id_name != default_name:
            id_name = id_name.get(id_val[1], default_name)
        if id_name != default_name:
            id_name = id_name.get(id_val[2], default_name)
    logger.log_debug(f"[SysEx] Manufacturer or ID name: {id_name}")

    # -----------------
    # Extract device ID
    # -----------------
    next_byte = syx_id_len
    device_id = data.data[next_byte]
    logger.log_debug(f"[SysEx] Device ID: {device_id}")

    # -------
    # Sub IDs
    # -------

    # Defined Universal System Exclusive Messages

    #     Non-Real Time
    if id_val == 0x7E:
        next_byte += 1
        sub_id1_val = data.data[next_byte]
        logger.log_debug(f"[SysEx] Sub-ID#1: {sub_id1_val} ")
        sub_id1_name = midiexplorer.midi.constants. \
            DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_NON_REAL_TIME_SUB_ID_1.get(
            sub_id1_val, default_name)
        logger.log_debug(f"[SysEx] Sub-ID#1 name: {sub_id1_name}")
        if sub_id1_val in midiexplorer.midi.constants.NON_REAL_TIME_SUB_ID_2_FROM_1:
            next_byte += 1
            sub_id2_val = data.data[next_byte]
            logger.log_debug(f"[SysEx] Sub-ID#2: {sub_id2_val} ")
            sub_id2_name = midiexplorer.midi.constants.NON_REAL_TIME_SUB_ID_2_FROM_1.get(sub_id1_val).get(
                sub_id2_val, default_name)
            logger.log_debug(f"[SysEx] Sub-ID#2 name: {sub_id2_name}")

    #     Real Time
    if id_val == 0x7F:
        next_byte += 1
        sub_id1_val = data.data[next_byte]
        logger.log_debug(f"[SysEx] Sub-ID#1: {sub_id1_val} ")
        sub_id1_name = midiexplorer.midi.constants. \
            DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_REAL_TIME_SUB_ID_1.get(
            sub_id1_val, default_name)
        logger.log_debug(f"[SysEx] Sub-ID#1 name: {sub_id1_name}")
        if sub_id1_val in midiexplorer.midi.constants.REAL_TIME_SUB_ID_2_FROM_1:
            next_byte += 1
            sub_id2_val = data.data[next_byte]
            logger.log_debug(f"[SysEx] Sub-ID#2: {sub_id2_val} ")
            sub_id2_name = midiexplorer.midi.constants.REAL_TIME_SUB_ID_2_FROM_1.get(sub_id1_val).get(
                sub_id2_val, default_name)
            logger.log_debug(f"[SysEx] Sub-ID#2 name: {sub_id2_name}")

    # TODO: decode sample dump standard (page 35)
    # ACK, NAK, Wait, Cancel & EOF
    # TODO: decode device inquiry (page 40)
    # TODO: decode file dump (page 41)
    # TODO: decode midi tuning (page 47)
    # TODO: decode general midi system messages (page 52)
    # TODO: decode MTC full message, user bits and real time cueing (page 53 + dedicated spec)
    # TODO: decode midi show control (page 53 + dedicated spec)
    # TODO: decode notation information (page 54)
    # TODO: decode device control (page 57)
    # TODO: decode MMC (page 58 + dedicated spec)

    # -----------------
    # Undecoded payload
    # -----------------
    next_byte += 1
    payload = data.data[next_byte:]
    logger.log_debug(f"[SysEx] Payload: {payload}")

    # Build ID type string
    if id_region:
        id_type = f"{id_region} {id_group} ID"
    else:
        id_type = f"{id_group} ID"

    return [id_type, id_name, id_val, device_id,
            sub_id1_name, sub_id1_val, sub_id2_name, sub_id2_val, payload]


def _mon_update_sysex(decoded):
    """Populate decoded system exclusive values in the GUI.

    :param decoded: Decoded system exclusive message from _decode_sysex(). TODO: custom type?
    """

    dpg.set_value('syx_id_type', decoded[0])
    dpg.set_value('syx_id_label', decoded[1])
    dpg.set_value('syx_id', decoded[2])
    dpg.set_value('syx_device_id', decoded[3])
    dpg.set_value('syx_sub_id1_label', decoded[4])
    dpg.set_value('syx_sub_id1', decoded[5] if not None else "")
    dpg.set_value('syx_sub_id2_label', decoded[6])
    dpg.set_value('syx_sub_id2', decoded[7] if not None else "")
    dpg.set_value('syx_payload', decoded[8])


def conv_tooltip(title: str, values: int | tuple[int] | list[int] | None = None,
                 hlen: int = 2, dlen: int = 3, blen: int = 8) -> None:
    """Adds a tooltip with data converted to hexadecimal, decimal and binary.

    :param title: Tooltip title.
    :param values: Tooltip value(s)
    :param hlen: Hexadecimal length
    :param dlen: Decimal length
    :param blen: Binary length

    """
    if values is not None:
        hconv = ""
        dconv = ""
        bconv = ""
        if isinstance(values, int):
            value = values
            hconv += f"{' ':{blen - hlen}}{value:0{hlen}X}"
            dconv += f"{' ':{blen - dlen}}{value:0{dlen}d}"
            bconv += f"{value:0{blen}b}"
        else:
            for value in values:
                hconv += f"{' ':{blen - hlen}}{value:0{hlen}X} "
                dconv += f"{' ':{blen - dlen}}{value:0{dlen}d} "
                bconv += f"{value:0{blen}b} "

    text = f"{title}\n"
    if values is not None:
        text += \
            "\n" \
            f"Hexadecimal:\t{hconv.rstrip()}\n" \
            f"Decimal:{' ':4}\t{dconv.rstrip()}\n" \
            f"Binary:{' ':5}\t{bconv.rstrip()}\n"

    with dpg.tooltip(dpg.last_item()):
        dpg.add_text(f"{text}")
