# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe window and management
"""

import time

import mido
from dearpygui import dearpygui as dpg

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

    ###
    # DEAR PYGUI THEME for red buttons
    ###
    with dpg.theme(tag='__red'):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))

    with dpg.window(
            tag='probe_win',
            label="Probe",
            width=960,
            height=685,
            no_close=True,
            collapsed=False,
            pos=[960, 20]
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

        # Activity Monitor
        with dpg.collapsing_header(label="Activity Monitor", default_open=True):
            dpg.add_child_window(tag='act_mon', height=180, border=False)

        with dpg.table(parent='act_mon', header_row=False, policy=dpg.mvTable_SizingFixedFit):
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

        with dpg.table(parent='act_mon', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")
            for channel in range(17):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel")

                for channel in range(16):
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1:2d}")
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text(f"Channel {channel + 1}\n"
                                     "\n"
                                     f"Hexadecimal:\t{' ':2}{channel:01X}\n"
                                     f"Decimal:\t\t{channel:03d}\n"
                                     f"Binary:\t\t{channel:04b}\n")

        with dpg.table(parent='act_mon', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(9):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel Messages")

                dpg.add_text("Voice")

                # Channel voice messages (page 9)
                dpg.add_button(tag='mon_note_off', label="OFF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note-Off\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{8:01X}\n"
                                 f"Decimal:\t\t{8:03d}\n"
                                 f"Binary:\t\t{8:04b}\n")

                dpg.add_button(tag='mon_note_on', label=" ON ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note-On\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{9:01X}\n"
                                 f"Decimal:\t\t{9:03d}\n"
                                 f"Binary:\t\t{9:04b}\n")

                dpg.add_button(tag='mon_polytouch', label="PKPR")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Poly Key Pressure (Note Aftertouch)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{10:01X}\n"
                                 f"Decimal:\t\t{10:03d}\n"
                                 f"Binary:\t\t{10:04b}\n")

                dpg.add_button(tag='mon_control_change', label=" CC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Control Change""\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{11:01X}\n"
                                 f"Decimal:\t\t{11:03d}\n"
                                 f"Binary:\t\t{11:04b}\n")

                dpg.add_button(tag='mon_program_change', label=" PC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Program Change\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{12:01X}\n"
                                 f"Decimal:\t\t{12:03d}\n"
                                 f"Binary:\t\t{12:04b}\n")

                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Channel Pressure (Channel Aftertouch)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{13:01X}\n"
                                 f"Decimal:\t\t{13:03d}\n"
                                 f"Binary:\t\t{13:04b}\n")

                dpg.add_button(tag='mon_pitchwheel', label="PBC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Pitch Bend Change\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':2}{14:01X}\n"
                                 f"Decimal:\t\t{14:03d}\n"
                                 f"Binary:\t\t{14:04b}\n")

            # TODO: Channel mode messages (page 20) (CC 120-127)
            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Mode")

            with dpg.table_row():
                dpg.add_text("System Messages")

                dpg.add_text("Exclusive")

                # System exclusive messages
                dpg.add_button(tag='mon_sysex', label="SOX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Exclusive aka SysEx\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF0:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF0:03d}\n"
                                 f"Binary:\t\t{0xF0:08b}\n")

                # FIXME: mido is missing EOX (TODO: send PR)
                # TODO: display according to settings
                dpg.add_button(tag='mon_end_of_exclusive', label="EOX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("End of Exclusive\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF7:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF7:03d}\n"
                                 f"Binary:\t\t{0xF7:08b}\n")

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Common")

                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("MIDI Time Code Quarter Frame\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF1:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF1:03d}\n"
                                 f"Binary:\t\t{0xF1:08b}\n")

                dpg.add_button(tag='mon_songpos', label="SGPS")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Song Position Pointer\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF2:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF2:03d}\n"
                                 f"Binary:\t\t{0xF2:08b}\n")

                dpg.add_button(tag='mon_song_select', label="SGSL")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Song Select\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF3:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF3:03d}\n"
                                 f"Binary:\t\t{0xF3:08b}\n")

                dpg.add_button(tag='undef1', label="UND ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Undefined. (Reserved)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF4:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF4:03d}\n"
                                 f"Binary:\t\t{0xF4:08b}\n")

                dpg.add_button(tag='undef2', label="UND ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Undefined. (Reserved)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF5:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF5:03d}\n"
                                 f"Binary:\t\t{0xF5:08b}\n")

                dpg.add_button(tag='mon_tune_request', label=" TR ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Tune Request\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF6:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF6:03d}\n"
                                 f"Binary:\t\t{0xF6:08b}\n")

                # Moved to Exclusive System Messages for now
                # TODO: display according to settings
                # dpg.add_button(tag='mon_end_of_exclusive', label="EOX ")
                # with dpg.tooltip(dpg.last_item()):
                #     dpg.add_text("End of Exclusive\n"
                #                  "\n"
                #                  f"Hexadecimal:\t{' ':5}{0xF7:01X}\n"
                #                  f"Decimal:\t\t{' ':4}{0xF7:03d}\n"
                #                  f"Binary:\t\t{0xF7:08b}\n")

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Real-Time")

                # System real time messages (page 30)
                dpg.add_button(tag='mon_clock', label="CLK ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Timing Clock\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF8:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF8:03d}\n"
                                 f"Binary:\t\t{0xF8:08b}\n")

                dpg.add_button(tag='undef3', label="UND ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Undefined. (Reserved)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF9:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF9:03d}\n"
                                 f"Binary:\t\t{0xF9:08b}\n")

                dpg.add_button(tag='mon_start', label="STRT")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Start\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFA:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFA:03d}\n"
                                 f"Binary:\t\t{0xFA:08b}\n")

                dpg.add_button(tag='mon_continue', label="CTNU")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Continue\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFB:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFB:03d}\n"
                                 f"Binary:\t\t{0xFB:08b}\n")

                dpg.add_button(tag='mon_stop', label="STOP")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Stop\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFC:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFC:03d}\n"
                                 f"Binary:\t\t{0xFC:08b}\n")

                dpg.add_button(tag='undef4', label="UND ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Undefined. (Reserved)\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFD:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFD:03d}\n"
                                 f"Binary:\t\t{0xFD:08b}\n")

                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Active Sensing\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFE:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFE:03d}\n"
                                 f"Binary:\t\t{0xFE:08b}\n")

                dpg.add_button(tag='mon_reset', label="RST ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Reset\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xFF:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xFF:03d}\n"
                                 f"Binary:\t\t{0xFF:08b}\n")

            with dpg.table_row():
                dpg.add_text("Controllers")
                # TODO: Control Changes (page 11)
                for controller in range(120):
                    if controller % 16:
                        # TODO: change row
                        pass
                    dpg.add_text("")

            with dpg.table_row():
                dpg.add_text()
                dpg.add_text("Channel Mode")
                # TODO: Channel modes (page 20)
                for mode in range(120, 128):
                    dpg.add_text("")

            with dpg.table_row():
                dpg.add_text("System Exclusive")
                # TODO: decode 1 or 3 byte IDs (page 34)
                dpg.add_text("")
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

            with dpg.table_row():
                dpg.add_text("Running Status")
                # FIXME: unimplemented upstream (page A-1)

        # Data table
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
    Decodes and present data received from the probe.

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
        stat_label = data.type
        _mon_blink(stat_label)
        dpg.add_text(stat_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(stat_label)

        # Channel
        if hasattr(data, 'channel'):
            chan_label = data.channel + 1
            _mon_blink('c')
            _mon_blink(data.channel)
        else:
            chan_label = "Global"
            _mon_blink('s')
        dpg.add_text(chan_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(chan_label)

        # Data 1 & 2
        data0 = ""
        data1 = ""
        if 'note' in data.type:
            data0 = data.note  # TODO: decode to human readable
            data1 = data.velocity
            if dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY:
                _mon_blink('note_off')
        elif 'polytouch' == data.type:
            data0 = data.note
            data1 = data.value
        elif 'control_change' == data.type:
            data0 = data.control  # TODO: decode to human readable
            data1 = data.value
        elif 'program_change' == data.type:
            data0 = data.program
        elif 'aftertouch' == data.type:
            data0 = data.value
        elif 'pitchwheel' == data.type:
            data0 = data.pitch
        elif 'sysex' == data.type:
            data0 = data.data  # TODO: decode device ID
        elif 'quarter_frame' == data.type:
            data0 = data.frame_type  # TODO: decode
            data1 = data.frame_value  # TODO: decode
        elif 'songpos' == data.type:
            data0 = data.pos
        elif 'song_select' == data.type:
            data0 = data.song
        dpg.add_text(data0)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(data0)
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
    target = f"mon_{indicator}_active_until"
    until = now + delay
    dpg.set_value(target, until)
    dpg.bind_item_theme(f"mon_{indicator}", '__red')
    # logger.log_debug(f"Current time:{time.time() - START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def update_blink_status() -> None:
    now = time.time() - START_TIME
    if dpg.get_value('mon_c_active_until') < now:
        dpg.bind_item_theme('mon_c', None)
    if dpg.get_value('mon_s_active_until') < now:
        dpg.bind_item_theme('mon_s', None)
    for channel in range(16):
        if dpg.get_value(f"mon_{channel}_active_until") < now:
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
    if dpg.get_value("mon_reset_active_until") < now:
        dpg.bind_item_theme('mon_reset', None)
