# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe window and management
"""

import time
from dearpygui import dearpygui as dpg

import midi.constants
import midi.notes
import mido
from gui.config import DEBUG, START_TIME
from gui.logger import Logger
from midi.constants import NOTE_OFF_VELOCITY

US2MS = 1000

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
probe_data_counter = 0
previous_timestamp = START_TIME


def _add_tooltip_conv(title: str, value: int, hlen: int = 2, dlen: int = 3, blen: int = 8) -> None:
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text(
            f"{title}\n"
            "\n"
            f"Hexadecimal:\t{' ':{blen - hlen}}{value:0{hlen}X}\n"
            f"Decimal:{' ':4}\t{' ':{blen - dlen}}{value:0{dlen}d}\n"
            f"Binary:{' ':5}\t{value:0{blen}b}\n"
        )


def create() -> None:
    with dpg.value_registry():
        # Preferences
        dpg.add_float_value(tag='mon_blink_duration', default_value=.25)  # seconds
        # Per standard, consider note-on with velocity set to 0 as note-off
        dpg.add_bool_value(tag='zero_velocity_note_on_is_note_off', default_value=True)
        # Blink management
        dpg.add_float_value(tag='mon_c_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_s_active_until', default_value=0)  # seconds
        for channel in range(16):  # Monitoring status
            dpg.add_float_value(tag=f"mon_{channel}_active_until", default_value=0)  # seconds
        dpg.add_float_value(tag='mon_note_off_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_note_on_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_polytouch_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_control_change_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_program_change_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_aftertouch_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_pitchwheel_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_sysex_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_quarter_frame_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_songpos_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_song_select_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_tune_request_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_end_of_exclusive_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_clock_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_start_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_continue_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_stop_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_active_sensing_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_reset_active_until', default_value=0)  # seconds
        for controller in range(128):
            dpg.add_float_value(tag=f'mon_cc_{controller}_active_until', default_value=0)  # seconds

    ###
    # DEAR PYGUI THEME for red buttons
    ###
    with dpg.theme(tag='__red'):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))

    with dpg.window(
            tag='probe_win',
            label="Probe",
            width=1005,
            height=685,
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
                # TODO: implement
                with dpg.group(horizontal=True):
                    dpg.add_text("EOX is a:")
                    dpg.add_radio_button(
                        items=(
                            "System Common Message (default, MIDI specification compliant)",
                            "System Exclusive Message"
                        ),
                        source='eox_system_message'
                    )

        ###
        # Mode
        ###
        # TODO
        with dpg.collapsing_header(label="MIDI Mode", default_open=False):
            dpg.add_child_window(tag='probe_midi_mode', height=10, border=False)

            dpg.add_text("Not implemented yet")

            dpg.add_input_int(tag='mode_basic_chan', label="Basic Channel",
                              default_value=midi.constants.POWER_UP_DEFAULT['basic_channel'] + 1)

            dpg.add_radio_button(
                tag='modes',
                items=[
                    "1",  # Omni On - Poly
                    "2",  # Omni On - Mono
                    "3",  # Omni Off - Poly
                    "4",  # Omni Off - Mono
                ],
                default_value=midi.constants.POWER_UP_DEFAULT['mode'],
                horizontal=True, enabled=False,
            )

        ###
        # Messages
        ###
        with dpg.collapsing_header(label="Messages", default_open=True):
            dpg.add_child_window(tag='probe_messages_container', height=180, border=False)

        with dpg.table(parent='probe_messages_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
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

        with dpg.table(parent='probe_messages_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")
            for channel in range(17):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel")

                for channel in range(16):
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1:2d}")
                    _add_tooltip_conv(f"Channel {channel + 1}", channel, hlen, dlen, blen)

        with dpg.table(parent='probe_messages_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(9):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel Messages")

                dpg.add_text("Voice")

                # Channel voice messages (page 9)
                dpg.add_button(tag='mon_note_off', label="N OF")
                val = 8
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_note_on', label="N ON")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_polytouch', label="PKPR")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_control_change', label=" CC ")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_program_change', label=" PC ")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                dpg.add_button(tag='mon_pitchwheel', label="PBCH")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

            # TODO: Channel mode messages (page 20) (CC 120-127)
            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Mode")

                dpg.add_button(tag='mon_all_sound_off', label="ASOF")
                val = 120
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_reset_all_controllers', label="RAC ")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_local_control', label=" LC ")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_all_notes_off', label="ANOF")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_omni_off', label="O OF")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_omni_on', label="O ON")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_mono_on', label="M ON")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                dpg.add_button(tag='mon_poly_on', label="P ON")
                val += 1
                _add_tooltip_conv(midi.constants.CHANNEL_MODE_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text("System Messages")

                dpg.add_text("Exclusive")

                # System exclusive messages
                dpg.add_button(tag='mon_sysex', label="SOX ")
                val = 0xF0
                _add_tooltip_conv(midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                # TODO: display according to settings
                dpg.add_button(tag='mon_end_of_exclusive', label="EOX ")
                val = 0xF7
                _add_tooltip_conv(midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Common")

                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                val = 0xF1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                dpg.add_button(tag='mon_songpos', label="SGPS")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                dpg.add_button(tag='mon_song_select', label="SGSL")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                dpg.add_button(tag='undef1', label="UND ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                dpg.add_button(tag='undef2', label="UND ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                dpg.add_button(tag='mon_tune_request', label=" TR ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # Moved to Exclusive System Messages for now
                # TODO: display according to settings
                # dpg.add_button(tag='mon_end_of_exclusive', label="EOX ")
                # val += 1
                # _add_tooltip_conv(midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Real-Time")

                # System real time messages (page 30)
                dpg.add_button(tag='mon_clock', label="CLK ")
                val = 0xF8
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='undef3', label="UND ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='mon_start', label="STRT")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='mon_continue', label="CTNU")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='mon_stop', label="STOP")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='undef4', label="UND ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                dpg.add_button(tag='mon_reset', label="RST ")
                val += 1
                _add_tooltip_conv(midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

        ###
        # Controllers
        ###
        with dpg.collapsing_header(label="Controllers", default_open=False):
            dpg.add_child_window(tag='probe_controllers_container', height=200, border=False)

        with dpg.table(tag='probe_controllers', parent='probe_controllers_container', header_row=False,
                       policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(17):
                dpg.add_table_column()

            rownum = 0
            with dpg.table_row(tag=f'ctrls_{rownum}'):
                dpg.add_text("Controllers")
                dpg.add_text("")

            for controller in range(128):
                dpg.add_button(tag=f'mon_cc_{controller}', label=f"{controller:3d}", parent=f'ctrls_{rownum}')
                _add_tooltip_conv(midi.constants.CONTROLLER_NUMBERS[controller], controller)
                newrownum = int((controller + 1) / 16)
                if newrownum > rownum and newrownum != 8:
                    rownum = newrownum
                    dpg.add_table_row(tag=f'ctrls_{rownum}', parent='probe_controllers')
                    dpg.add_text("", parent=f'ctrls_{rownum}')
                    dpg.add_text("", parent=f'ctrls_{rownum}')
            del rownum

        ###
        # System Exclusive
        ###
        with dpg.collapsing_header(label="System Exclusive", default_open=False):
            dpg.add_child_window(tag='probe_sysex_container', height=20, border=False)

        with dpg.table(tag='probe_sysex', parent='probe_sysex_container', header_row=False,
                       policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(17):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Not implemented yet")
                # TODO: decode 1 or 3 byte IDs (page 34)
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

        ###
        # Running Status
        ###
        with dpg.collapsing_header(label="Running Status", default_open=False):
            dpg.add_child_window(tag='probe_running_status_container', height=20, border=False)
            # FIXME: unimplemented upstream (page A-1)
            dpg.add_text("Not implemented yet", parent='probe_running_status_container')

        ###
        # Notes
        ###
        with dpg.collapsing_header(label="Notes", default_open=False):
            dpg.add_child_window(tag='probe_notes_container', height=120, border=False)

        # TODO: Staff?
        # dpg.add_child_window(parent='probe_notes_container', tag='staff', label="Staff", height=120, border=False)

        # Keyboard
        dpg.add_child_window(parent='probe_notes_container', tag='keyboard', label="Keyboard", height=120, border=False)

        width = 12
        height = 60
        bxpos = width / 2
        wxpos = 0

        for index in midi.notes.MIDI_NOTES_ALPHA_EN:
            name = midi.notes.MIDI_NOTES_ALPHA_EN[index]
            xpos = wxpos
            ypos = height
            if "#" in midi.notes.MIDI_NOTES_ALPHA_EN[index]:
                height = ypos
                xpos = bxpos
                ypos = 0
            label = "\n".join(name)  # Vertical text

            dpg.add_button(tag=f'note_{index}', label=label, parent='keyboard', width=width, height=height,
                           pos=(xpos, ypos))
            _add_tooltip_conv(
                f"Syllabic:{' ':9}\t{midi.notes.MIDI_NOTES_SYLLABIC[index]}\n"
                f"Alphabetical (EN):\t{name}\n"
                f"Alphabetical (DE):\t{midi.notes.MIDI_NOTES_ALPHA_DE[index]}",
                index, blen=7
            )

            if "#" not in name:
                wxpos += width + 1
            elif "D#" in name or "A#" in name:
                bxpos += (width + 1) * 2
            else:
                bxpos += width + 1

        ###
        # Data history table
        ###
        with dpg.collapsing_header(label="Data History", default_open=True):
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


def _clear_probe_data_table() -> None:
    dpg.delete_item('probe_data_table', children_only=True, slot=1)
    _init_details_table_data()


def _init_details_table_data() -> None:
    # Initial data for reverse scrolling
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass


def _add_probe_data(timestamp: float, source: str, data: mido.Message) -> None:
    """
    Decodes and presents data received from the probe.

    :param timestamp:
    :param source:
    :param data:
    :return:
    """
    global probe_data_counter, previous_timestamp

    logger = Logger()

    logger.log_debug(f"Adding data from {source} to probe at {timestamp}: {data!r}")

    # TODO: insert new data at the top of the table
    previous_data = probe_data_counter
    probe_data_counter += 1

    with dpg.table_row(parent='probe_data_table', label=f'probe_data_{probe_data_counter}',
                       before=f'probe_data_{previous_data}'):

        # Source
        dpg.add_selectable(label=source, span_columns=True)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(source)

        # Timestamp (ms)
        ts_label = str((timestamp - START_TIME) * US2MS)
        dpg.add_text(ts_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(ts_label)

        # Delta (ms)
        delta = "0.0"
        if data.time:
            delta = data.time * US2MS
            logger.log_debug("Using rtmidi time delta")
        elif previous_timestamp is not None:
            logger.log_debug("Rtmidi time delta not available. Computing timestamp locally.")
            delta = (timestamp - previous_timestamp) * US2MS
        previous_timestamp = timestamp
        delta_label = str(delta)
        dpg.add_text(delta_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(delta_label)

        # Raw message
        raw_label = data.hex()
        dpg.add_text(raw_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(raw_label)

        # Decoded message
        if DEBUG:
            dec_label = repr(data)
            dpg.add_text(dec_label)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(dec_label)

        # Status
        _mon_blink(data.type)
        stat_label = data.type
        dpg.add_text(stat_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(stat_label)

        # Channel
        if hasattr(data, 'channel'):
            _mon_blink('c')
            _mon_blink(data.channel)
            chan_label = data.channel + 1  # Human-readable format
        else:
            _mon_blink('s')
            chan_label = "Global"
        dpg.add_text(chan_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(chan_label)

        # Data 1 & 2
        data0 = ""
        data0_dec: str | False = False
        data1 = ""
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
            data0 = data.note
            data0_dec = midi.notes.MIDI_NOTES_ALPHA_EN[data.note]  # TODO: add preference for syllabic / EN / DE
            data1 = data.velocity
        elif 'polytouch' == data.type:
            data0 = data.note
            data0_dec = midi.notes.MIDI_NOTES_ALPHA_EN[data.note]  # TODO: add preference for syllabic / EN / DE
            data1 = data.value
        elif 'control_change' == data.type:
            _mon_blink(f'cc_{data.control}')
            data0 = data.control
            data0_dec = midi.constants.CONTROLLER_NUMBERS[data.control]
            data1 = data.value
        elif 'program_change' == data.type:
            data0 = data.program
        elif 'aftertouch' == data.type:
            data0 = data.value
        elif 'pitchwheel' == data.type:
            data0 = data.pitch
        elif 'sysex' == data.type:
            data0 = data.data  # TODO: decode device ID, Universal system exclusive messages…
        elif 'quarter_frame' == data.type:
            data0 = data.frame_type  # TODO: decode
            data1 = data.frame_value  # TODO: decode
        elif 'songpos' == data.type:
            data0 = data.pos
        elif 'song_select' == data.type:
            data0 = data.song

        if data0_dec:
            dpg.add_text(data0_dec)
        else:
            dpg.add_text(data0)
        _add_tooltip_conv(data0_dec if data0_dec else data0, data0)

        dpg.add_text(data1)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(data1)

    # TODO: per message type color coding
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('probe_data_table_autoscroll'):
        dpg.set_y_scroll('act_det', -1.0)


def _mon_blink(indicator: int | str) -> None:
    now = time.time() - START_TIME
    delay = dpg.get_value('mon_blink_duration')
    target = f'mon_{indicator}_active_until'
    until = now + delay
    dpg.set_value(target, until)
    dpg.bind_item_theme(f'mon_{indicator}', '__red')
    # logger.log_debug(f"Current time:{time.time() - START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def _note_on(number: int | str) -> None:
    dpg.bind_item_theme(f'note_{number}', '__red')


def _note_off(number: int | str) -> None:
    dpg.bind_item_theme(f'note_{number}', None)


def update_blink_status() -> None:
    now = time.time() - START_TIME
    if dpg.get_value('mon_c_active_until') < now:
        dpg.bind_item_theme('mon_c', None)
    if dpg.get_value('mon_s_active_until') < now:
        dpg.bind_item_theme('mon_s', None)
    for channel in range(16):
        if dpg.get_value(f'mon_{channel}_active_until') < now:
            dpg.bind_item_theme(f"mon_{channel}", None)
    if dpg.get_value('mon_active_sensing_active_until') < now:
        dpg.bind_item_theme('mon_active_sensing', None)
    if dpg.get_value('mon_note_off_active_until') < now:
        dpg.bind_item_theme('mon_note_off', None)
    if dpg.get_value('mon_note_on_active_until') < now:
        dpg.bind_item_theme('mon_note_on', None)
    if dpg.get_value('mon_polytouch_active_until') < now:
        dpg.bind_item_theme('mon_polytouch', None)
    if dpg.get_value('mon_control_change_active_until') < now:
        dpg.bind_item_theme('mon_control_change', None)
    if dpg.get_value('mon_program_change_active_until') < now:
        dpg.bind_item_theme('mon_program_change', None)
    if dpg.get_value('mon_aftertouch_active_until') < now:
        dpg.bind_item_theme('mon_aftertouch', None)
    if dpg.get_value('mon_pitchwheel_active_until') < now:
        dpg.bind_item_theme('mon_pitchwheel', None)
    if dpg.get_value('mon_sysex_active_until') < now:
        dpg.bind_item_theme('mon_sysex', None)
    if dpg.get_value('mon_quarter_frame_active_until') < now:
        dpg.bind_item_theme('mon_quarter_frame', None)
    if dpg.get_value('mon_songpos_active_until') < now:
        dpg.bind_item_theme('mon_songpos', None)
    if dpg.get_value('mon_song_select_active_until') < now:
        dpg.bind_item_theme('mon_song_select', None)
    if dpg.get_value('mon_tune_request_active_until') < now:
        dpg.bind_item_theme('mon_tune_request', None)
    if dpg.get_value('mon_end_of_exclusive_active_until') < now:
        dpg.bind_item_theme('mon_end_of_exclusive', None)
    if dpg.get_value('mon_clock_active_until') < now:
        dpg.bind_item_theme('mon_clock', None)
    if dpg.get_value('mon_start_active_until') < now:
        dpg.bind_item_theme('mon_start', None)
    if dpg.get_value('mon_continue_active_until') < now:
        dpg.bind_item_theme('mon_continue', None)
    if dpg.get_value('mon_stop_active_until') < now:
        dpg.bind_item_theme('mon_stop', None)
    if dpg.get_value('mon_reset_active_until') < now:
        dpg.bind_item_theme('mon_reset', None)
    for controller in range(128):
        if dpg.get_value(f'mon_cc_{controller}_active_until') < now:
            dpg.bind_item_theme(f'mon_cc_{controller}', None)
