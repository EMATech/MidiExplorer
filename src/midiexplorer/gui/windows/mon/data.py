# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Monitor data management.
"""

import mido
from dearpygui import dearpygui as dpg

from midiexplorer.gui.helpers.convert import set_value_preconv
from midiexplorer.gui.windows.mon.blink import mon, note_on, note_off, reset_mon, cc
from midiexplorer.midi.constants import NOTE_OFF_VELOCITY
from midiexplorer.midi.decoders.sysex import DecodedUniversalSysExPayload, DecodedSysEx


def _update_gui_sysex(decoded: DecodedSysEx):
    """Populate decoded system exclusive values in the GUI.

    :param decoded: Decoded system exclusive message from _decode_sysex().
    """

    dpg.set_value('syx_id_group', decoded.identifier.group)
    dpg.set_value('syx_id_region', decoded.identifier.region)
    dpg.set_value('syx_id_name', decoded.identifier.name)
    set_value_preconv('syx_id_val', decoded.identifier.value)
    set_value_preconv('syx_device_id', decoded.device_id)
    set_value_preconv('syx_payload', decoded.payload.value)
    if isinstance(decoded.payload, DecodedUniversalSysExPayload):
        dpg.hide_item('syx_payload_container')
        if decoded.payload.sub_id1_value:
            dpg.set_value('syx_sub_id1_name', decoded.payload.sub_id1_name)
            set_value_preconv('syx_sub_id1_val', decoded.payload.sub_id1_value if not None else "")
            dpg.show_item('syx_sub_id1')
        else:
            dpg.hide_item('syx_sub_id1')
        if decoded.payload.sub_id2_value:
            dpg.set_value('syx_sub_id2_name', decoded.payload.sub_id2_name)
            set_value_preconv('syx_sub_id2_val', decoded.payload.sub_id2_value if not None else "")
            dpg.show_item('syx_sub_id2')
        else:
            dpg.hide_item('syx_sub_id2_value')
        dpg.show_item('syx_decoded_payload')
    else:
        dpg.hide_item('syx_decoded_payload')
        dpg.show_item('syx_payload_container')


def update_gui_monitor(data: mido.Message, static: bool = False) -> None:
    """Updates the monitor.

    :param data: MIDI data.
    :param static: Live or static mode.

    """

    reset_mon(static=True)  # Reset monitor before decoding to avoid keeping old data from selected history row.

    # Status
    mon(data.type, static)

    # Channel
    chan_val = None
    if hasattr(data, 'channel'):
        mon('c', static)  # CHANNEL
        mon(data.channel, static)
    else:
        mon('s', static)  # SYSTEM

    # Data 1 & 2
    if 'note' in data.type:
        if dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY:
            mon('note_off', static)
        # Keyboard
        if 'on' in data.type and not (
                dpg.get_value('zero_velocity_note_on_is_note_off') and data.velocity == NOTE_OFF_VELOCITY
        ):
            note_on(data.note, static, data.velocity)
        else:
            note_off(data.note, static)
    elif 'polytouch' == data.type:
        if static:
            note_on(data.note, static)
    elif 'control_change' == data.type:
        cc(data.control, data.value, static)
    elif 'program_change' == data.type:
        # TODO: Optionally decode General MIDI names.
        pass
    elif 'aftertouch' == data.type:
        # TODO: display
        pass
    elif 'pitchwheel' == data.type:
        # TODO: display
        pass
    elif 'sysex' == data.type:
        decoded_sysex = DecodedSysEx(data.data)
        _update_gui_sysex(decoded_sysex)
    elif 'quarter_frame' == data.type:
        # TODO: display
        pass
    elif 'songpos' == data.type:
        # TODO: display
        pass
    elif 'song_select' == data.type:
        # TODO: display
        pass


