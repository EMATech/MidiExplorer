# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe window and data management.

TODO: separate presentation from processing logic
TODO: factorize into smaller pieces
"""
import functools
import sys
import time
from typing import Any, Optional, Tuple

import mido
from dearpygui import dearpygui as dpg

import midiexplorer.midi.constants
import midiexplorer.midi.mido2standard
import midiexplorer.midi.notes
from midiexplorer.gui.config import DEBUG, START_TIME
from midiexplorer.gui.logger import Logger
from midiexplorer.midi.constants import NOTE_OFF_VELOCITY

US2MS = 1000  # microseconds to milliseconds ratio

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
probe_data_counter = 0
previous_timestamp = START_TIME


def _init_details_table_data() -> None:
    """
    Initial table data for reverse scrolling.
    """
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass


def _clear_probe_data_table(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """
    Clears the data table.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.
    :return:
    """
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    dpg.delete_item('probe_data_table', children_only=True, slot=1)
    _init_details_table_data()


def _add_probe_data(timestamp: float, source: str, data: mido.Message) -> None:
    """
    Decodes and presents data received from the probe.

    :param timestamp: System timestamp
    :param source: Input name
    :param data: MIDI data
    :return:
    """
    global probe_data_counter, previous_timestamp

    logger = Logger()

    logger.log_debug(f"Adding data from {source} to probe at {timestamp}: {data!r}")

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
        ts = (timestamp - START_TIME) * US2MS
        dpg.add_text(f"{ts:n}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{ts}")

        # Delta (ms)
        delta = "0.32"  # Minimum delay between MIDI messages on the wire is 320us
        if data.time is not None:
            delta = data.time * US2MS
            logger.log_debug("Timing: Using rtmidi time delta")
        elif previous_timestamp is not None:
            logger.log_debug("Timing: Rtmidi time delta not available. Computing timestamp locally.")
            delta = (timestamp - previous_timestamp) * US2MS
        previous_timestamp = timestamp
        dpg.add_text(f"{delta:n}")
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(f"{delta}")

        # Raw message
        raw_label = data.hex()
        dpg.add_text(raw_label)
        _add_tooltip_conv(raw_label, data.bin())

        # Decoded message
        if DEBUG:
            dec_label = repr(data)
            dpg.add_text(dec_label)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(dec_label)

        # Status
        _mon_blink(data.type)
        status_byte = midiexplorer.midi.mido2standard.get_status_by_type(data.type)
        stat_label = midiexplorer.midi.constants.STATUS_BYTES[status_byte]
        dpg.add_text(stat_label)
        if hasattr(data, 'channel'):
            status_nibble = int((status_byte - data.channel) / 16)
            _add_tooltip_conv(stat_label, status_nibble, hlen=1, dlen=2, blen=4)
        else:
            _add_tooltip_conv(stat_label, status_byte)

        # Channel
        chan_val = None
        if hasattr(data, 'channel'):
            _mon_blink('c')
            _mon_blink(data.channel)
            chan_label = data.channel + 1  # Human-readable format
            chan_val = data.channel
        else:
            _mon_blink('s')
            chan_label = "Global"
        dpg.add_text(chan_label)
        _add_tooltip_conv(chan_label, chan_val, hlen=1, dlen=2, blen=4)

        # Data 1 & 2
        data0_name: str | False = False
        data0: int | tuple | None = None
        data0_dec: str | False = False
        data1_name: str | False = False
        data1: int | None = None
        data1_dec: str | False = False
        if 'note' in data.type:
            if dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY:
                _mon_blink('note_off')
            # Keyboard
            if 'on' in data.type and not (
                    dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY
            ):
                _note_on(data.note)
            else:
                _note_off(data.note)
            data0_name = "Note"
            data0: int = data.note
            data0_dec = midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN.get(
                data.note)  # TODO: add preference for syllabic / EN / DE
            data1_name = "Velocity"
            data1: int = data.velocity
        elif 'polytouch' == data.type:
            data0: int = data.note
            data0_dec = midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN.get(
                data.note)  # TODO: add preference for syllabic / EN / DE
            data1: int = data.value
        elif 'control_change' == data.type:
            _mon_blink(f'cc_{data.control}')
            data0_name = "Controller"
            data0: int = data.control
            data0_dec = midiexplorer.midi.constants.CONTROLLER_NUMBERS.get(data.control)
            data1_name = "Value"
            data1: int = data.value
        elif 'program_change' == data.type:
            data0_name = "Program"
            data0: int = data.program
        elif 'aftertouch' == data.type:
            data0_name = "Value"
            data0: int = data.value
        elif 'pitchwheel' == data.type:
            data0_name = "Pitch"
            data0: int = data.pitch
        elif 'sysex' == data.type:
            data0_name = "Data"
            data0: tuple = data.data

            ###
            # System Exclusive decoding
            ###
            syx_id_type: str = ""
            syx_id_group: str = ""
            syx_id_region: None | str = None
            syx_id: None | int | Tuple = None
            syx_id_label: str = ""
            syx_device_id: None | int = None
            syx_sub_id1: None | int = None
            syx_sub_id1_label: str = ""
            syx_sub_id2: None | int = None
            syx_sub_id2_label: str = ""
            syx_payload: None | int | Tuple = None

            # decode 1 or 3 byte IDs (page 34)

            # Extract ID
            syx_id = data0[0]  # 1-byte ID or first byte of 3-byte ID
            syx_id_len = 1
            # Decode group
            syx_id_group = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_GROUPS[syx_id]
            if syx_id == 0:
                # 3-byte ID
                syx_id_len = 3
                syx_id = data0[0:3]
                syx_region_idx = 1
            logger.log_debug(f"[SysEx] ID: {syx_id}")

            # Decode region
            if syx_id_len == 1:
                syx_id_region = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_REGIONS.get(syx_id)
            elif syx_id_len == 3:
                syx_id_region = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID_REGIONS.get(syx_id[1])
            else:
                raise ValueError("SysEx IDs are either 1 or 3 bytes long")

            # Decode ID
            default_syx_label = "Undefined"
            if syx_id_len == 1:
                syx_id_label = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID.get(
                    syx_id, default_syx_label)
            if syx_id_len == 3:
                # TODO: optimise?
                syx_id_label = midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_ID.get(
                    syx_id[0], default_syx_label)
                if syx_id_label != default_syx_label:
                    syx_id_label = syx_id_label.get(syx_id[1], default_syx_label)
                if syx_id_label != default_syx_label:
                    syx_id_label = syx_id_label.get(syx_id[2], default_syx_label)
            logger.log_debug(f"[SysEx] Manufacturer or ID name: {syx_id_label}")

            # Extract device ID
            next_byte = syx_id_len
            syx_device_id = data0[next_byte]
            logger.log_debug(f"[SysEx] Device ID: {syx_device_id}")

            # Defined Universal System Exclusive Messages
            #     Non-Real Time
            if syx_id == 0x7E:
                next_byte += 1
                syx_sub_id1 = data[next_byte]
                logger.log_debug(f"[SysEx] Sub-ID#1: {syx_sub_id1} ")
                syx_sub_id1_label = midiexplorer.midi.constants. \
                    DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_NON_REAL_TIME_SUB_ID_1.get(
                    syx_sub_id1, default_syx_label)
                logger.log_debug(f"[SysEx] Sub-ID#1 name: {syx_sub_id1_label}")
                if syx_sub_id1 in midiexplorer.midi.constants.NON_REAL_TIME_SUB_ID_2_FROM_1:
                    next_byte += 1
                    syx_sub_id2 = data0[next_byte]
                    logger.log_debug(f"[SysEx] Sub-ID#2: {syx_sub_id2} ")
                    syx_sub_id2_label = midiexplorer.midi.constants.NON_REAL_TIME_SUB_ID_2_FROM_1.get(syx_sub_id1).get(
                        syx_sub_id2, default_syx_label)
                    logger.log_debug(f"[SysEx] Sub-ID#2 name: {syx_sub_id2_label}")
            #     Real Time
            if syx_id == 0x7F:
                next_byte += 1
                syx_sub_id1 = data0[next_byte]
                logger.log_debug(f"[SysEx] Sub-ID#1: {syx_sub_id1} ")
                syx_sub_id1_label = midiexplorer.midi.constants. \
                    DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_REAL_TIME_SUB_ID_1.get(
                    syx_sub_id1, default_syx_label)
                logger.log_debug(f"[SysEx] Sub-ID#1 name: {syx_sub_id1_label}")
                if syx_sub_id1 in midiexplorer.midi.constants.REAL_TIME_SUB_ID_2_FROM_1:
                    next_byte += 1
                    syx_sub_id2 = data0[next_byte]
                    logger.log_debug(f"[SysEx] Sub-ID#2: {syx_sub_id2} ")
                    syx_sub_id2_label = midiexplorer.midi.constants.REAL_TIME_SUB_ID_2_FROM_1.get(syx_sub_id1).get(
                        syx_sub_id2, default_syx_label)
                    logger.log_debug(f"[SysEx] Sub-ID#2 name: {syx_sub_id2_label}")

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

            # Undecoded payload
            next_byte += 1
            syx_payload = data0[next_byte:]
            logger.log_debug(f"[SysEx] Payload: {syx_payload}")

            if syx_id_region:
                syx_id_type = f"{syx_id_region} {syx_id_group} ID"
            else:
                syx_id_type = f"{syx_id_group} ID"

            # Populate values used by the GUI
            dpg.set_value('syx_id_type', syx_id_type)
            dpg.set_value('syx_id', syx_id)
            dpg.set_value('syx_id_label', syx_id_label)
            dpg.set_value('syx_device_id', syx_device_id)
            dpg.set_value('syx_sub_id1', syx_sub_id1)
            dpg.set_value('syx_sub_id1_label', syx_sub_id1_label)
            dpg.set_value('syx_sub_id2', syx_sub_id2)
            dpg.set_value('syx_sub_id2_label', syx_sub_id2_label)
            dpg.set_value('syx_payload', syx_payload)

        elif 'quarter_frame' == data.type:
            data0_name = "Frame type"
            data0 = data.frame_type  # TODO: decode
            data1_name = "Frame value"
            data1 = data.frame_value  # TODO: decode
        elif 'songpos' == data.type:
            data0_name = "Position Pointer"
            data0 = data.pos
        elif 'song_select' == data.type:
            data0_name = "Song #"
            data0 = data.song

        if data0_dec:
            dpg.add_text(str(data0_dec))
        else:
            dpg.add_text(str(data0))
        prefix0 = ""
        if data0_name:
            prefix0 = data0_name + ": "
        _add_tooltip_conv(prefix0 + str(data0_dec if data0_dec else data0), data0, blen=7)

        dpg.add_text(str(data1))
        prefix1 = ""
        if data1_name:
            prefix1 = data1_name + ": "
        _add_tooltip_conv(prefix1 + str(data1_dec if data1_dec else data1), data1, blen=7)

    # TODO: per message type color coding
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('probe_data_table_autoscroll'):
        dpg.set_y_scroll('act_det', -1.0)


def _mon_blink(indicator: int | str) -> None:
    """
    Illuminates an indicator in the monitor panel and prepare metadata for its lifetime management.

    :param indicator: Name of the indicator to blink
    :return:
    """
    # logger = midiexplorer.gui.logger.Logger()
    # logger.log_debug(f"blink {indicator}")

    now = time.time() - START_TIME
    delay = dpg.get_value('mon_blink_duration')
    target = f'mon_{indicator}_active_until'
    until = now + delay
    dpg.set_value(target, until)
    theme = '__act'
    # EOX special case since we have two alternate representations.
    if indicator != 'end_of_exclusive':
        dpg.bind_item_theme(f'mon_{indicator}', theme)
    else:
        dpg.bind_item_theme(f'mon_{indicator}_common', theme)
        dpg.bind_item_theme(f'mon_{indicator}_syx', theme)
    # logger.log_debug(f"Current time:{time.time() - START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def _note_on(number: int | str) -> None:
    """
    Illuminates the note.

    :param number: MIDI note number
    :return:
    """
    dpg.bind_item_theme(f'note_{number}', '__act')


def _note_off(number: int | str) -> None:
    """
    Darken the note.

    :param number:
    :return:
    """
    dpg.bind_item_theme(f'note_{number}', None)


def _update_eox_category(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """
    Displays the EOX monitor in the appropriate category according to settings.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.
    :return:
    """
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    if dpg.get_value('eox_category') == user_data[0]:
        dpg.hide_item('mon_end_of_exclusive_syx')
        dpg.show_item('mon_end_of_exclusive_common')
    else:
        dpg.hide_item('mon_end_of_exclusive_common')
        dpg.show_item('mon_end_of_exclusive_syx')


def _add_tooltip_conv(title: str, values: int | tuple[int] | list[int] | None = None, hlen: int = 2, dlen: int = 3,
                      blen: int = 8) -> None:
    if values is not None:
        hconv = ""
        dconv = ""
        bconv = ""
        if type(values) is int:
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


@functools.lru_cache()
def _get_supported_indicators() -> list:
    mon_indicators = [
        'mon_c',
        'mon_s',
        'mon_note_off',
        'mon_note_on',
        'mon_polytouch',
        'mon_control_change',
        'mon_program_change',
        'mon_aftertouch',
        'mon_pitchwheel',
        'mon_sysex',
        'mon_quarter_frame',
        'mon_songpos',
        'mon_song_select',
        'mon_tune_request',
        'mon_end_of_exclusive',
        'mon_clock',
        'mon_start',
        'mon_continue',
        'mon_stop',
        'mon_active_sensing',
        'mon_reset'
    ]
    for channel in range(16):
        mon_indicators.append(f'mon_{channel}')
    for controller in range(128):
        mon_indicators.append(f'mon_cc_{controller}')
    if DEBUG:  # Experimental
        mon_indicators.append([
            'mon_undef1',
            'mon_undef2',
            'mon_undef3',
            'mon_undef4',
            'mon_all_sound_off',
            'mon_reset_all_controllers',
            'mon_local_control',
            'mon_all_notes_off',
            'mon_omni_off',
            'mon_omni_on',
            'mon_mono_on',
            'mon_poly_on'
        ])

    return mon_indicators


def create() -> None:
    """
    Creates the probe window.
    """
    with dpg.value_registry():
        # ------------
        # Preferences
        # ------------
        dpg.add_float_value(tag='mon_blink_duration', default_value=.25)  # seconds
        # Per standard, consider note-on with velocity set to 0 as note-off
        dpg.add_bool_value(tag='zero_velocity_note_on_is_note_off', default_value=True)
        # TODO: add both?
        eox_categories = (
            "System Common Message (default, MIDI specification compliant)",
            "System Exclusive Message"
        )
        dpg.add_string_value(tag='eox_category', default_value=eox_categories[0])
        # ----------------------------
        # Indicators blink management
        # ----------------------------
        for indicator in _get_supported_indicators():
            dpg.add_float_value(tag=f'{indicator}_active_until', default_value=0)  # seconds
        # ---------------
        # SysEx decoding
        # ---------------
        dpg.add_string_value(tag='syx_id_type', default_value="ID")
        dpg.add_string_value(tag='syx_id')
        dpg.add_string_value(tag='syx_id_label')
        dpg.add_string_value(tag='syx_device_id')
        dpg.add_string_value(tag='syx_sub_id1')
        dpg.add_string_value(tag='syx_sub_id1_label')
        dpg.add_string_value(tag='syx_sub_id2')
        dpg.add_string_value(tag='syx_sub_id2_label')
        dpg.add_string_value(tag='syx_payload')

    # ---------------------------------------
    # DEAR PYGUI THEME for activated buttons
    # ---------------------------------------
    with dpg.theme(tag='__act'):
        with dpg.theme_component(dpg.mvButton):
            # TODO: add preference
            color = (255, 0, 0)  # red
            dpg.add_theme_color(dpg.mvThemeCol_Button, color)

    # ------------------
    # Probe window size
    # ------------------
    # TODO: compute dynamically?
    probe_win_height = 1020
    if DEBUG:
        probe_win_height = 685

    # -------------
    # Probe window
    # -------------
    with dpg.window(
            tag='probe_win',
            label="Probe",
            width=1005,
            height=probe_win_height,
            no_close=True,
            collapsed=False,
            pos=[900, 20]
    ):

        with dpg.menu_bar():
            with dpg.menu(label="Settings"):
                dpg.add_slider_float(
                    tag='mon_blink_duration_slider',
                    label="Persistence (s)",
                    min_value=0, max_value=0.5, source='mon_blink_duration',
                    callback=lambda:
                    dpg.set_value('mon_blink_duration', dpg.get_value('mon_blink_duration_slider'))
                )
                dpg.add_checkbox(label="0 velocity note-on is note-off (default, MIDI specification compliant)",
                                 source='zero_velocity_note_on_is_note_off')
                with dpg.group(horizontal=True):
                    dpg.add_text("EOX is a:")
                    dpg.add_radio_button(
                        items=eox_categories,
                        default_value=eox_categories[0],
                        source='eox_category',
                        callback=_update_eox_category,
                        user_data=eox_categories
                    )

        # -----
        # Mode
        #-----
        if DEBUG:
            # TODO: implement
            with dpg.collapsing_header(label="MIDI Mode", default_open=False):
                dpg.add_child_window(tag='probe_midi_mode', height=10, border=False)

                dpg.add_text("Not implemented yet")

                # FIXME: move to settings?
                dpg.add_input_int(tag='mode_basic_chan', label="Basic Channel",
                                  default_value=midiexplorer.midi.constants.POWER_UP_DEFAULT['basic_channel'] + 1)

                dpg.add_radio_button(
                    tag='modes',
                    items=[
                        "1",  # Omni On - Poly
                        "2",  # Omni On - Mono
                        "3",  # Omni Off - Poly
                        "4",  # Omni Off - Mono
                    ],
                    default_value=midiexplorer.midi.constants.POWER_UP_DEFAULT['mode'],
                    horizontal=True, enabled=False,
                )

        # -------
        # Status
        #-------
        status_height = 154
        if DEBUG:
            status_height = 180
        with dpg.collapsing_header(label="Status", default_open=True):
            dpg.add_child_window(tag='probe_status_container', height=status_height, border=False)

        with dpg.table(parent='probe_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(3):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Type")

                dpg.add_button(tag='mon_c', label="CHANNEL")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Channel Message")

                dpg.add_button(tag='mon_s', label="SYSTEM")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Message")

        hlen = 1  # Hexadecimal
        dlen = 3  # Decimal
        blen = 4  # Binary

        with dpg.table(parent='probe_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")
            for channel in range(17):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel")

                for channel in range(16):
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1:2d}")
                    _add_tooltip_conv(f"Channel {channel + 1}", channel, hlen, dlen, blen)

        with dpg.table(parent='probe_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(9):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel Messages")

                dpg.add_text("Voice")

                # Channel voice messages (page 9)
                val = 8
                dpg.add_button(tag='mon_note_off', label="N OF")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_note_on', label="N ON")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_polytouch', label="PKPR")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_control_change', label=" CC ")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_program_change', label=" PC ")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_pitchwheel', label="PBCH")
                _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

            if DEBUG:
                # TODO: Channel mode messages (page 20) (CC 120-127)
                # TODO: add preference to separate reserved CC120-127
                with dpg.table_row():
                    dpg.add_text()

                    dpg.add_text("Mode")

                    val = 120
                    dpg.add_button(tag='mon_all_sound_off', label="ASOF")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_reset_all_controllers', label="RAC ")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_local_control', label=" LC ")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_all_notes_off', label="ANOF")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_off', label="O OF")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_on', label="O ON")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_mono_on', label="M ON")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_poly_on', label="P ON")
                    _add_tooltip_conv(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text("System Messages")

                dpg.add_text("Common")

                val = 0xF1
                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_songpos', label="SGPS")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_song_select', label="SGSL")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef1', label="UND ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef2', label="UND ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_tune_request', label=" TR ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val += 1
                dpg.add_button(tag='mon_end_of_exclusive_common', label="EOX ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Real-Time")

                # System real time messages (page 30)
                val = 0xF8
                dpg.add_button(tag='mon_clock', label="CLK ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef3', label="UND ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_start', label="STRT")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_continue', label="CTNU")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_stop', label="STOP")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef4', label="UND ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_reset', label="RST ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Exclusive")

                # System exclusive messages
                val = 0xF0
                dpg.add_button(tag='mon_sysex', label="SOX ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val = 0xF7
                dpg.add_button(tag='mon_end_of_exclusive_syx', label="EOX ")
                _add_tooltip_conv(midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

            _update_eox_category(sender=None, app_data=None, user_data=eox_categories)

        # ------
        # Notes
        #------
        with dpg.collapsing_header(label="Notes", default_open=True):
            dpg.add_child_window(tag='probe_notes_container', height=120, border=False)

        # TODO: Staff?
        # dpg.add_child_window(parent='probe_notes_container', tag='staff', label="Staff", height=120, border=False)

        # Keyboard
        dpg.add_child_window(parent='probe_notes_container', tag='keyboard', label="Keyboard", height=120,
                             border=False)

        # TODO: add an intensity display for velocity?

        width = 12  # Key width
        height = 60  # Key height
        margin = 1  # Margin between keys
        bxpos = width / 2  # Black key X position
        wxpos = 0  # White key X position

        # TODO: add preference for default notes notation?
        for index in midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN:
            name = midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN[index]

            # Compute actual key position
            xpos = wxpos
            ypos = height
            if "#" in name:
                height = ypos
                xpos = bxpos
                ypos = 0

            label = "\n".join(name)  # Vertical text

            dpg.add_button(tag=f'note_{index}', label=label, parent='keyboard', width=width, height=height,
                           pos=(xpos, ypos))
            _add_tooltip_conv(
                f"Syllabic:{' ':9}\t{midiexplorer.midi.notes.MIDI_NOTES_SYLLABIC[index]}\n"
                f"Alphabetical (EN):\t{name}\n"
                f"Alphabetical (DE):\t{midiexplorer.midi.notes.MIDI_NOTES_ALPHA_DE[index]}",
                index, blen=7
            )

            # Next key position computation
            if "#" not in name:
                wxpos += width + margin
            elif "D#" in name or "A#" in name:
                bxpos += (width + margin) * 2
            else:
                bxpos += width + margin

        # ---------------
        # Running Status
        #---------------
        if DEBUG:
            # TODO: implement
            with dpg.collapsing_header(label="Running Status", default_open=False):
                dpg.add_child_window(tag='probe_running_status_container', height=20, border=False)
                # FIXME: unimplemented upstream (page A-1)
                dpg.add_text("Not implemented yet", parent='probe_running_status_container')

        # ------------
        # Controllers
        #------------
        with dpg.collapsing_header(label="Controllers", default_open=True):
            dpg.add_child_window(tag='probe_controllers_container', height=192, border=False)

        with dpg.table(tag='probe_controllers', parent='probe_controllers_container', header_row=False,
                       policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(17):
                dpg.add_table_column()

            rownum = 0
            with dpg.table_row(tag=f'ctrls_{rownum}'):
                dpg.add_text("Controllers")
                dpg.add_text("")

            # TODO: add preference to separate reserved CC120-127
            for controller in range(128):
                dpg.add_button(tag=f'mon_cc_{controller}', label=f"{controller:3d}", parent=f'ctrls_{rownum}')
                _add_tooltip_conv(midiexplorer.midi.constants.CONTROLLER_NUMBERS[controller], controller)
                newrownum = int((controller + 1) / 16)
                if newrownum > rownum and newrownum != 8:
                    rownum = newrownum
                    dpg.add_table_row(tag=f'ctrls_{rownum}', parent='probe_controllers')
                    dpg.add_text("", parent=f'ctrls_{rownum}')
                    dpg.add_text("", parent=f'ctrls_{rownum}')
            del rownum

        ###
        # TODO: Per controller status
        ###
        # Value timegraph

        ###
        # TODO: Registered parameter decoding?
        ###
        # Value timegraph

        ###
        # TODO: Program change status? (+ Bank Select?)
        ###
        # Value timegraph

        ###
        # TODO: Pitch bend change
        ###
        # Value timegraph

        ###
        # TODO: Aftertouch
        ###
        # Value timegraph

        ###
        # TODO: System common
        ###
        # MTC Quarter Frame (Fully decode MTC status)
        # Song Pos Pointer
        # Song Select
        # Tune Request
        # EOX

        ###
        # TODO: System Realtime
        ###
        # Timing Clock (Compute BPM)
        # Start
        # Continue
        # Stop
        # Active Sensing
        # System Reset

        # -----------------
        # System Exclusive
        #-----------------
        with dpg.collapsing_header(label="System Exclusive", default_open=True):
            dpg.add_child_window(tag='probe_sysex_container', height=130, border=False)

        with dpg.table(tag='probe_sysex', parent='probe_sysex_container', header_row=False,
                       policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(2):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text(source='syx_id_type')
                dpg.add_text(source='syx_id')
                dpg.add_text(source='syx_id_label')
            with dpg.table_row():
                dpg.add_text("Device ID")
                dpg.add_text(source='syx_device_id')
                dpg.add_text()
            with dpg.table_row():
                dpg.add_text("Sub-ID#1")
                dpg.add_text(source='syx_sub_id1')
                dpg.add_text(source='syx_sub_id1_label')
            with dpg.table_row():
                dpg.add_text("Sub-ID#2")
                dpg.add_text(source='syx_sub_id2')
                dpg.add_text(source='syx_sub_id2_label')
            with dpg.table_row():
                dpg.add_text("Undecoded payload")
                dpg.add_text(source='syx_payload')
                dpg.add_text()

        # -------------------
        # Data history table
        #-------------------
        with dpg.collapsing_header(label="History", default_open=True):
            dpg.add_child_window(tag='probe_table_container', height=390, border=False)

        # Details buttons
        # FIXME: separated to not scroll with table child window until table scrolling is supported
        dpg.add_child_window(parent='probe_table_container', tag='act_det_btns', label="Buttons", height=45,
                             border=False)
        with dpg.group(parent='act_det_btns', horizontal=True):
            dpg.add_checkbox(tag='probe_data_table_autoscroll', label="Auto-Scroll", default_value=True)
            dpg.add_button(label="Clear", callback=_clear_probe_data_table)

        # Details
        # FIXME: workaround table scrolling not implemented upstream yet to have static headers
        # dpg.add_child_window(tag='act_det_headers', label="Details headers", height=5, border=False)
        with dpg.table(parent='act_det_btns',
                       tag='probe_data_table_headers',
                       header_row=True,
                       freeze_rows=1,
                       policy=dpg.mvTable_SizingStretchSame):
            dpg.add_table_column(label="Source")
            dpg.add_table_column(label="Timestamp (ms)")
            dpg.add_table_column(label="Delta (ms)")
            dpg.add_table_column(label="Raw Message (HEX)")
            if DEBUG:
                dpg.add_table_column(label="Decoded Message")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Channel")
            dpg.add_table_column(label="Data 1")
            dpg.add_table_column(label="Data 2")

        # TODO: Allow sorting
        # TODO: Show/hide columns
        # TODO: timegraph?
        # TODO: selecting an item shows it decoded values above
        dpg.add_child_window(parent='probe_table_container', tag='act_det', label="Details", height=340, border=False)
        with dpg.table(parent='act_det',
                       tag='probe_data_table',
                       header_row=False,  # FIXME: True when table scrolling will be implemented upstream
                       freeze_rows=0,  # FIXME: 1 when table scrolling will be implemented upstream
                       policy=dpg.mvTable_SizingStretchSame,
                       # scrollY=True,  # FIXME: Scroll the table instead of the window when available upstream
                       ):
            dpg.add_table_column(label="Timestamp (ms)")
            dpg.add_table_column(label="Delta (ms)")
            dpg.add_table_column(label="Source")
            dpg.add_table_column(label="Raw Message (HEX)")
            if DEBUG:
                dpg.add_table_column(label="Decoded Message")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Channel")
            dpg.add_table_column(label="Data 1")
            dpg.add_table_column(label="Data 2")

            _init_details_table_data()


def update_mon_blink_status() -> None:
    """
    Handles monitor indicators blinking status update each frame.

    Checks for the time it should stay illuminated and darkens it if expired.
    """
    now = time.time() - START_TIME
    for indicator in _get_supported_indicators():
        if dpg.get_value(f'{indicator}_active_until') < now:
            # EOX is a special case since we have two alternate representations.
            if indicator != 'mon_end_of_exclusive':
                dpg.bind_item_theme(f'{indicator}', None)
            else:
                dpg.bind_item_theme(f'{indicator}_common', None)
                dpg.bind_item_theme(f'{indicator}_syx', None)
