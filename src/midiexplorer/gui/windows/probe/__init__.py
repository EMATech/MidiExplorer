# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Probe window.
"""

import sys
from typing import Any, Optional

from dearpygui import dearpygui as dpg

import midiexplorer.midi.constants
import midiexplorer.midi.mido2standard
import midiexplorer.midi.notes
from midiexplorer.gui.config import DEBUG
from midiexplorer.gui.logger import Logger
from midiexplorer.gui.windows.probe.blink import get_supported_indicators
from midiexplorer.gui.windows.probe.data import conv_tooltip


def _init_details_table_data() -> None:
    """Initial table data for reverse scrolling.

    """
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass


def _clear_probe_data_table(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Clears the data table.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    dpg.delete_item('probe_data_table', children_only=True, slot=1)
    _init_details_table_data()


def _update_eox_category(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Displays the EOX monitor in the appropriate category according to settings.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    if dpg.get_value('eox_category') == user_data[0]:
        dpg.hide_item('mon_end_of_exclusive_syx_grp')
        dpg.show_item('mon_end_of_exclusive_common_grp')
    else:
        dpg.hide_item('mon_end_of_exclusive_common_grp')
        dpg.show_item('mon_end_of_exclusive_syx_grp')


def create() -> None:
    """Creates the probe window.

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
        for indicator in get_supported_indicators():
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
        # -----
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
        # -------
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
                    conv_tooltip(f"Channel {channel + 1}", channel, hlen, dlen, blen)

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
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_note_on', label="N ON")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_polytouch', label="PKPR")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_control_change', label=" CC ")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_program_change', label=" PC ")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

                val += 1
                dpg.add_button(tag='mon_pitchwheel', label="PBCH")
                conv_tooltip(midiexplorer.midi.constants.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen, blen)

            if DEBUG:
                # TODO: Channel mode messages (page 20) (CC 120-127)
                # TODO: add preference to separate reserved CC120-127
                with dpg.table_row():
                    dpg.add_text()

                    dpg.add_text("Mode")

                    val = 120
                    dpg.add_button(tag='mon_all_sound_off', label="ASOF")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_reset_all_controllers', label="RAC ")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_local_control', label=" LC ")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_all_notes_off', label="ANOF")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_off', label="O OF")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_on', label="O ON")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_mono_on', label="M ON")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_poly_on', label="P ON")
                    conv_tooltip(midiexplorer.midi.constants.CHANNEL_MODE_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text("System Messages")

                dpg.add_text("Common")

                val = 0xF1
                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_songpos', label="SGPS")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_song_select', label="SGSL")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef1', label="UND ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef2', label="UND ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_tune_request', label=" TR ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val += 1
                with dpg.group(tag='mon_end_of_exclusive_common_grp'):
                    dpg.add_button(tag='mon_end_of_exclusive_common', label="EOX ")
                    conv_tooltip(midiexplorer.midi.constants.SYSTEM_COMMON_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Real-Time")

                # System real time messages (page 30)
                val = 0xF8
                dpg.add_button(tag='mon_clock', label="CLK ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef3', label="UND ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_start', label="STRT")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_continue', label="CTNU")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_stop', label="STOP")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef4', label="UND ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_reset', label="RST ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_REAL_TIME_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Exclusive")

                # System exclusive messages
                val = 0xF0
                dpg.add_button(tag='mon_sysex', label="SOX ")
                conv_tooltip(midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val = 0xF7
                with dpg.group(tag='mon_end_of_exclusive_syx_grp'):
                    dpg.add_button(tag='mon_end_of_exclusive_syx', label="EOX ")
                    conv_tooltip(midiexplorer.midi.constants.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

            _update_eox_category(sender=None, app_data=None, user_data=eox_categories)

        # ------
        # Notes
        # ------
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
        for index, name in midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN.items():
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
            conv_tooltip(
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
        # ---------------
        if DEBUG:
            # TODO: implement
            with dpg.collapsing_header(label="Running Status", default_open=False):
                dpg.add_child_window(tag='probe_running_status_container', height=20, border=False)
                # FIXME: unimplemented upstream (page A-1)
                dpg.add_text("Not implemented yet", parent='probe_running_status_container')

        # ------------
        # Controllers
        # ------------
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
                conv_tooltip(midiexplorer.midi.constants.CONTROLLER_NUMBERS[controller], controller, blen=7)
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
        # -----------------
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
                # TODO: dynamic conversion tooltip
                dpg.add_text(source='syx_id_label')
            with dpg.table_row():
                dpg.add_text("Device ID")
                dpg.add_text(source='syx_device_id')
                # TODO: dynamic conversion tooltip
                dpg.add_text()
            # FIXME: Optional. Don't display if N.A.
            with dpg.table_row():
                dpg.add_text("(Sub-ID#1)")
                dpg.add_text(source='syx_sub_id1')
                # TODO: dynamic conversion tooltip
                dpg.add_text(source='syx_sub_id1_label')
            # FIXME: Optional. Don't display if N.A.
            with dpg.table_row():
                dpg.add_text("(Sub-ID#2)")
                dpg.add_text(source='syx_sub_id2')
                # TODO: dynamic conversion tooltip
                dpg.add_text(source='syx_sub_id2_label')
            with dpg.table_row():
                dpg.add_text("Undecoded payload")
                dpg.add_text(source='syx_payload')
                # TODO: dynamic conversion tooltip
                dpg.add_text()

        # -------------------
        # Data history table
        # -------------------
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