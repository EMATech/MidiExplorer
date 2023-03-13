# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Monitoring blinking buttons.
"""
import functools
import time

from dearpygui import dearpygui as dpg

from midiexplorer.__config__ import DEBUG
from midiexplorer.midi.timestamp import Timestamp


@functools.lru_cache()  # Only compute once
def get_supported_indicators() -> list:
    """Cached list of supported indicators.

    :return: list of indicators.
    """
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
        mon_indicators.extend([
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


def get_supported_decoders() -> list:
    decoders = [
        'syx_id_group',
        'syx_id_region',
        'syx_id_name',
        'syx_id_val',
        'syx_device_id',
        'syx_payload',
        'syx_sub_id1_name',
        'syx_sub_id1_val',
        'syx_sub_id2_name',
        'syx_sub_id2_val',
    ]
    return decoders


def get_theme(static, disable: bool = False):
    if not static and not disable:
        theme = '__act'
    elif not static and disable:
        theme = None
    else:
        theme = '__force_act'
    return theme


def mon(indicator: int | str, static: bool = False) -> None:
    """Illuminates an indicator in the monitor panel and prepare metadata for its lifetime management.

    :param indicator: Name of the indicator to blink.
    :param static: Live or static mode.

    """
    # logger = midiexplorer.gui.logger.Logger()
    # logger.log_debug(f"blink {indicator}")

    now = time.perf_counter() - Timestamp.START_TIME
    delay = dpg.get_value('mon_blink_duration')
    target = f'mon_{indicator}_active_until'
    if not static:
        until = now + delay
    else:
        until = float('inf')
    dpg.set_value(target, until)
    theme = get_theme(static)
    # EOX special case since we have two alternate representations.
    if indicator != 'end_of_exclusive':
        dpg.bind_item_theme(f'mon_{indicator}', theme)
    else:
        dpg.bind_item_theme(f'mon_{indicator}_common', theme)
        dpg.bind_item_theme(f'mon_{indicator}_syx', theme)
    # logger.log_debug(f"Current time:{time.perf_counter() - Timestamp.START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def note_on(number: int | str, static: bool = False, velocity: int = None) -> None:
    """Illuminates the note.

    :param number: MIDI note number.
    :param static: Live or static mode.
    :param velocity: Note velocity

    """
    theme = get_theme(static)
    dpg.bind_item_theme(f'note_{number}', theme)
    if velocity is not None:
        dpg.set_value(f'note_{number}', velocity)


def note_off(number: int | str, static: bool = False) -> None:
    """Darken the note.

    :param number: MIDI note number.
    :param static: Live or static mode.

    """
    theme = get_theme(static, disable=True)
    dpg.bind_item_theme(f'note_{number}', theme)
    dpg.set_value(f'note_{number}', 0)


def cc(number: int | str, value: int | str, static: bool = False) -> None:
    mon(f'cc_{number}', static)
    dpg.set_value(f'mon_cc_val_{number}', value)


def _reset_indicator(indicator):
    # EOX is a special case since we have two alternate representations.
    if indicator != 'mon_end_of_exclusive':
        dpg.bind_item_theme(f'{indicator}', None)
    else:
        dpg.bind_item_theme(f'{indicator}_common', None)
        dpg.bind_item_theme(f'{indicator}_syx', None)
    dpg.set_value(f'{indicator}_active_until', 0.0)


def update_mon_status() -> None:
    """Handles monitor indicators blinking status update each frame.

    Checks for the time it should stay illuminated and darkens it if expired.

    """
    now = time.perf_counter() - Timestamp.START_TIME
    for indicator in get_supported_indicators():
        value = dpg.get_value(f'{indicator}_active_until')
        if value:  # Prevent resetting theme when not needed.
            if value < now:
                _reset_indicator(indicator)


def reset_mon(static: bool = False) -> None:
    # FIXME: add a data structure caching the currently lit indicators to only process those needed
    for indicator in get_supported_indicators():
        if not static or dpg.get_value(f'{indicator}_active_until') == float('inf'):
            _reset_indicator(indicator)

    for index in range(0, 128):  # All MIDI notes
        if not static or dpg.get_item_theme(f'note_{index}') == '__force_act':
            note_off(index)

    if not static:
        for decoder in get_supported_decoders():
            dpg.set_value(f'{decoder}', "")
        # SysEx dynamic display
        dpg.hide_item('syx_decoded_payload')
        dpg.show_item('syx_payload_container')
