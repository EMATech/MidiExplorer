# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Monitor window.
"""

from typing import Any, Optional

import midi_const
from dearpygui import dearpygui as dpg

import midiexplorer.midi.mido2standard
import midiexplorer.midi.notes
from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers.callbacks.debugging import (
    enable as enable_dpg_cb_debugging
)
from midiexplorer.gui.helpers.convert import (
    add_string_value_preconv, tooltip_conv, tooltip_preconv
)
from midiexplorer.gui.windows.mon.blink import get_supported_indicators
from midiexplorer.gui.windows.mon.settings import eox_categories, notation_modes


def _verticalize(text: str) -> str:
    """Converts text to a vertical representation.

    :param text: text to convert
    :return: verticalized text
    """
    v_text = "\n".join(text)
    return v_text


def _update_eox_category(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Displays the EOX monitor in the appropriate category according to settings.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    if dpg.get_value('eox_category') == user_data[0]:
        dpg.hide_item('mon_end_of_exclusive_syx_grp')
        dpg.show_item('mon_end_of_exclusive_common_grp')
    else:
        dpg.hide_item('mon_end_of_exclusive_common_grp')
        dpg.show_item('mon_end_of_exclusive_syx_grp')


def _update_notation_mode(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Changes the way notes are displayed.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    # Update keyboard
    for index in range(0, 128):  # All MIDI notes
        dpg.configure_item(
            f'note_{index}',
            format=_verticalize(
                user_data.get(dpg.get_value('notation_mode')).get(index)
            )
        )


def create() -> None:
    """Creates the monitor window.

    """
    # -------------------------
    # DEAR PYGUI VALUE REGISTRY
    # -------------------------
    with dpg.value_registry():
        # ------------
        # Preferences
        # ------------
        dpg.add_float_value(tag='mon_blink_duration', default_value=.25)  # seconds
        # Per standard, consider note-on with velocity set to 0 as note-off
        dpg.add_bool_value(tag='zero_velocity_note_on_is_note_off', default_value=True)
        dpg.add_string_value(tag='eox_category', default_value=eox_categories[0])
        dpg.add_string_value(tag='notation_mode', default_value=next(iter(notation_modes.keys())))  # First key
        # ----------------------------
        # Indicators blink management
        # ----------------------------
        for indicator in get_supported_indicators():
            dpg.add_float_value(tag=f'{indicator}_active_until', default_value=0)  # seconds
        # ---------------
        # SysEx decoding
        # ---------------
        dpg.add_string_value(tag='syx_id_group')
        dpg.add_string_value(tag='syx_id_region')
        dpg.add_string_value(tag='syx_id_name')
        add_string_value_preconv(tag='syx_id_val')
        add_string_value_preconv(tag='syx_device_id')
        add_string_value_preconv(tag='syx_payload')
        # Defined Universal SysEx
        dpg.add_string_value(tag='syx_sub_id1_name')
        add_string_value_preconv(tag='syx_sub_id1_val')
        dpg.add_string_value(tag='syx_sub_id2_name')
        add_string_value_preconv(tag='syx_sub_id2_val')

    # ---------------------------------------
    # DEAR PYGUI THEME for activated buttons
    # ---------------------------------------
    with dpg.theme(tag='__act'):
        red = (255, 0, 0)
        light_red = (128, 0, 0)
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                tag='__act_but_col',
                target=dpg.mvThemeCol_Button,
                value=red,
            )
        with dpg.theme_component(dpg.mvSliderInt):
            dpg.add_theme_color(
                tag='__act_sli_col',  # TODO: allow customizing
                target=dpg.mvThemeCol_SliderGrab,
                value=red,
            )
            dpg.add_theme_color(
                tag='__act_sli_bg_col',  # TODO: allow customizing
                target=dpg.mvThemeCol_FrameBg,
                value=light_red,
            )
    with dpg.theme(tag='__force_act'):
        magenta = (170, 0, 170)
        light_magenta = (85, 0, 85)
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(
                tag='__force_act_col',
                target=dpg.mvThemeCol_Button,
                value=magenta,  # light magenta
            )
        with dpg.theme_component(dpg.mvSliderInt):
            dpg.add_theme_color(
                tag='__force_act_sli_col',  # TODO: allow customizing
                target=dpg.mvThemeCol_SliderGrab,
                value=magenta,
            )
            dpg.add_theme_color(
                tag='__force_act_sli_bg_col',  # TODO: allow customizing
                target=dpg.mvThemeCol_FrameBg,
                value=light_magenta,
            )

    # -------------------
    # Monitor window size
    # -------------------
    # TODO: compute dynamically?
    mon_win_height = 910
    if DEBUG:
        mon_win_height = 685

    # --------------
    # Monitor window
    # --------------
    with dpg.window(
            tag='mon_win',
            label="Monitor",
            width=1005,
            height=mon_win_height,
            no_close=True,
            collapsed=False,
            pos=[900, 20]
    ):

        with dpg.menu_bar():
            # --------
            # Settings
            # --------
            with dpg.menu(label="Settings"):
                with dpg.group():
                    dpg.add_text("Live color:")
                    dpg.add_color_picker(source='__act_but_col')
                with dpg.group():
                    dpg.add_text("Selected color:")
                    dpg.add_color_picker(source='__force_act_col')
                with dpg.group(horizontal=True):
                    dpg.add_text("Persistence:")
                    dpg.add_slider_float(
                        tag='mon_blink_duration_slider',
                        label="seconds",
                        min_value=1 / 120, max_value=2 / 3, source='mon_blink_duration',  # Min is one frame@120FPS
                        callback=lambda:
                        dpg.set_value('mon_blink_duration', dpg.get_value('mon_blink_duration_slider'))
                    )
                with dpg.group(horizontal=True):
                    dpg.add_text("Zero (0) velocity Note On is Note Off:")
                    dpg.add_checkbox(label="(default, MIDI specification compliant)",
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
                with dpg.group(horizontal=True):
                    dpg.add_text("Notation:")
                    dpg.add_radio_button(
                        items=list(notation_modes.keys()),
                        default_value=next(iter(notation_modes.values())),  # First value
                        source='notation_mode',
                        callback=_update_notation_mode,
                        user_data=notation_modes
                    )

        # TODO: Panic button to reset all monitored states.

        # -----
        # Mode
        # -----
        if DEBUG:
            # TODO: implement
            with dpg.collapsing_header(label="MIDI Mode", default_open=False):
                dpg.add_child_window(tag='mon_midi_mode', height=10, border=False)

                dpg.add_text("Not implemented yet")

                # FIXME: move to settings?
                dpg.add_input_int(
                    tag='mode_basic_chan', label="Basic Channel",
                    default_value=midi_const.POWER_UP_DEFAULT[
                                      'basic_channel'] + 1
                    )

                dpg.add_radio_button(
                    tag='modes',
                    items=[
                        "1",  # Omni On - Poly
                        "2",  # Omni On - Mono
                        "3",  # Omni Off - Poly
                        "4",  # Omni Off - Mono
                    ],
                    default_value=midi_const.POWER_UP_DEFAULT['mode'],
                    horizontal=True, enabled=False,
                )

        # -------
        # Status
        # -------
        status_height = 154
        if DEBUG:
            status_height = 180
        with dpg.collapsing_header(label="Status", default_open=True):
            dpg.add_child_window(tag='mon_status_container', height=status_height, border=False)

        with dpg.table(parent='mon_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
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

        with dpg.table(parent='mon_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")
            for channel in range(17):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel")

                for channel in range(16):
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1:2d}")
                    tooltip_conv(f"Channel {channel + 1}", channel, hlen, dlen, blen)

        with dpg.table(parent='mon_status_container', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(9):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channel Messages")

                dpg.add_text("Voice")

                # Channel voice messages (page 9)
                val = 8
                dpg.add_button(tag='mon_note_off', label="N OF")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_note_on', label="N ON")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_polytouch', label="PKPR")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_control_change', label=" CC ")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_program_change', label=" PC ")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

                val += 1
                dpg.add_button(tag='mon_pitchwheel', label="PBCH")
                tooltip_conv(
                    midi_const.CHANNEL_VOICE_MESSAGES[val], val, hlen, dlen,
                    blen
                    )

            if DEBUG:
                # TODO: Channel mode messages (page 20) (CC 120-127)
                # TODO: add preference to separate reserved CC120-127
                with dpg.table_row():
                    dpg.add_text()

                    dpg.add_text("Mode")

                    val = 120
                    dpg.add_button(tag='mon_all_sound_off', label="ASOF")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(
                        tag='mon_reset_all_controllers', label="RAC "
                        )
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_local_control', label=" LC ")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_all_notes_off', label="ANOF")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_off', label="O OF")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_omni_on', label="O ON")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_mono_on', label="M ON")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

                    val += 1
                    dpg.add_button(tag='mon_poly_on', label="P ON")
                    tooltip_conv(midi_const.CHANNEL_MODE_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text("System Messages")

                dpg.add_text("Common")

                val = 0xF1
                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_songpos', label="SGPS")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_song_select', label="SGSL")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef1', label="UND ")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef2', label="UND ")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_tune_request', label=" TR ")
                tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val += 1
                with dpg.group(tag='mon_end_of_exclusive_common_grp'):
                    dpg.add_button(
                        tag='mon_end_of_exclusive_common', label="EOX "
                        )
                    tooltip_conv(midi_const.SYSTEM_COMMON_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Real-Time")

                # System real time messages (page 30)
                val = 0xF8
                dpg.add_button(tag='mon_clock', label="CLK ")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef3', label="UND ")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_start', label="STRT")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_continue', label="CTNU")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_stop', label="STOP")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                # FIXME: unsupported by mido
                val += 1
                dpg.add_button(tag='mon_undef4', label="UND ")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

                val += 1
                dpg.add_button(tag='mon_reset', label="RST ")
                tooltip_conv(midi_const.SYSTEM_REAL_TIME_MESSAGES[val], val)

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("Exclusive")

                # System exclusive messages
                val = 0xF0
                dpg.add_button(tag='mon_sysex', label="SOX ")
                tooltip_conv(midi_const.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

                # FIXME: mido is missing EOX (TODO: send PR)
                val = 0xF7
                with dpg.group(tag='mon_end_of_exclusive_syx_grp'):
                    dpg.add_button(tag='mon_end_of_exclusive_syx', label="EOX ")
                    tooltip_conv(midi_const.SYSTEM_EXCLUSIVE_MESSAGES[val], val)

            _update_eox_category(sender=None, app_data=None, user_data=eox_categories)

        # ---------------
        # Running Status
        # ---------------
        if DEBUG:
            # TODO: implement
            with dpg.collapsing_header(label="Running Status", default_open=False):
                dpg.add_child_window(tag='mon_running_status_container', height=20, border=False)
                # FIXME: unimplemented upstream (page A-1)
                dpg.add_text("Not implemented yet", parent='mon_running_status_container')

        # ------
        # Notes
        # ------
        with dpg.collapsing_header(label="Notes", default_open=True):
            dpg.add_child_window(tag='mon_notes_container', height=180, border=False)

        # TODO: Staff?
        # dpg.add_child_window(parent='mon_notes_container', tag='staff', label="Staff", height=120, border=False)

        # Keyboard
        # TODO: Graphical
        dpg.add_child_window(parent='mon_notes_container', tag='keyboard', label="Keyboard", height=180,
                             border=False)

        # TODO: add an intensity display for velocity?

        width = 12  # Key width
        height = 90  # Key height
        margin = 1  # Margin between keys
        bxpos = width / 2  # Black key X position
        wxpos = 0  # White key X position

        for index, name in notation_modes.get(dpg.get_value('notation_mode')).items():
            # Compute actual key position
            xpos = wxpos
            ypos = height
            if "#" in name:
                height = ypos
                xpos = bxpos
                ypos = 0

            label = _verticalize(name)

            dpg.add_slider_int(
                tag=f'note_{index}', parent='keyboard', width=width, height=height,
                format=label,  # Used instead of label to display properly
                pos=(xpos, ypos),
                vertical=True,
                min_value=0, max_value=127,
                enabled=True,  # Required for theme color to apply properly
            )

            tooltip_conv(
                f"English Alphabetical:\t{midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN[index]}\n"
                f"Syllabic:{' ':12}\t{midiexplorer.midi.notes.MIDI_NOTES_SYLLABIC[index]}\n"
                f"German Alphabetical: \t{midiexplorer.midi.notes.MIDI_NOTES_ALPHA_DE[index]}",
                index, blen=7
            )

            # Next key position computation
            if "#" not in name:
                wxpos += width + margin
            elif "D#" in name or "A#" in name:
                bxpos += (width + margin) * 2
            else:
                bxpos += width + margin

        # ------------
        # Controllers
        # ------------
        with dpg.collapsing_header(label="Controllers", default_open=True):
            dpg.add_child_window(tag='mon_controllers_container', height=400, border=False)

        with dpg.table(tag='mon_controllers', parent='mon_controllers_container', header_row=False,
                       policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")

            for _i in range(17):
                dpg.add_table_column()

            num_controllers = 128
            group_controllers_by = 8
            rownum = 0
            dpg.add_table_row(tag=f'ctrls_{rownum}', parent='mon_controllers')
            #    dpg.add_text("Controllers")
            #    dpg.add_text("")
            # TODO: add preference to separate reserved CC120-127
            for controller in range(num_controllers):
                with dpg.group(horizontal=True, parent=f'ctrls_{rownum}'):
                    dpg.add_button(
                        tag=f'mon_cc_{controller}', label=f"{controller:3d}"
                        )
                    tooltip_conv(
                        midi_const.CONTROLLER_NUMBERS[controller], controller,
                        blen=7
                        )
                    dpg.add_input_text(
                        tag=f'mon_cc_val_{controller}', enabled=False, width=50
                        )
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text(
                            f"{midi_const.CONTROLLER_NUMBERS[controller]} Value:"
                            )
                        dpg.add_text(source=f'mon_cc_val_{controller}')
                        # TODO: hex and bin realtime conversions
                newrownum = (controller + 1) // group_controllers_by
                if newrownum > rownum:
                    rownum = newrownum
                    dpg.add_table_row(
                        tag=f'ctrls_{rownum}', parent='mon_controllers'
                        )
                    # dpg.add_text("", parent=f'ctrls_{rownum}')
                    # dpg.add_text("", parent=f'ctrls_{rownum}')
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
        # TODO: Polyphonic Key Pressure (Aftertouch)
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
        # TODO: Channel Pressure (Aftertouch)
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

            with dpg.child_window(tag='mon_sysex_container', height=120, border=False):
                with dpg.group():
                    with dpg.group(horizontal=True):
                        title = "ID"
                        dpg.add_text(title)
                        dpg.add_input_text(source='syx_id_region', readonly=True, width=200)
                        tooltip_preconv(f"{title} (Region)", 'syx_id_region', 'syx_id_val')
                        dpg.add_input_text(source='syx_id_group', readonly=True, width=200)
                        tooltip_preconv(f"{title} (Group)", 'syx_id_group', 'syx_id_val')
                        dpg.add_input_text(source='syx_id_name', readonly=True, width=200)
                        tooltip_preconv(f"{title} (Name)", 'syx_id_name', 'syx_id_val')
                    with dpg.group(horizontal=True):
                        title = "Device ID"
                        source = 'syx_device_id'
                        dpg.add_text(title)
                        dpg.add_input_text(source=source, readonly=True, width=50)
                        tooltip_preconv(static_title=title, values_source=source)
                    with dpg.group(horizontal=True, tag='syx_payload_container'):
                        title = "Undecoded Payload"
                        dpg.add_text(title)
                        source = 'syx_payload'
                        dpg.add_input_text(source=source, readonly=True, width=500)
                        tooltip_preconv(static_title=title, values_source=source)

                with dpg.group(tag='syx_decoded_payload', show=False):
                    title = "Decoded Payload"
                    dpg.add_text(title)
                    tooltip_preconv(static_title=title, values_source='syx_payload')

        # TODO: generate dynamically?
        with dpg.group(parent='syx_decoded_payload'):
            with dpg.group(horizontal=True, tag='syx_sub_id1'):
                title = "Sub-ID#1"
                dpg.add_text(title)
                dpg.add_input_text(source='syx_sub_id1_name', readonly=True, width=250)
                tooltip_preconv(title, 'syx_sub_id1_name', 'syx_sub_id1_val')
            with dpg.group(horizontal=True, tag='syx_sub_id2'):
                title = "Sub-ID#2"
                dpg.add_text(title)
                dpg.add_input_text(source='syx_sub_id2_name', readonly=True, width=250)
                tooltip_preconv(title, 'syx_sub_id2_name', 'syx_sub_id2_val')


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

    dpg.configure_item('mon_win', show=not dpg.is_item_visible('mon_win'))
