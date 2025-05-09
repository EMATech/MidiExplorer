# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Monitor data management.
"""
import midi_const
import mido
from dearpygui import dearpygui as dpg
from midi_const import NOTE_OFF_VELOCITY

from midiexplorer.gui.helpers.convert import set_value_preconv
from midiexplorer.gui.windows.mon.blink import cc, mon, note_off, note_on, \
    reset_mon
from midiexplorer.midi.decoders.sysex import DecodedSysEx, \
    DecodedUniversalSysExPayload


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
    if hasattr(data, 'channel'):
        mon('c', static)  # CHANNEL
        mon(data.channel, static)  # Channel #
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
        # TODO: display
        if static:
            note_on(data.note, static)
    elif 'control_change' == data.type:
        cc(data.control, data.value, static)
        # TODO: track CC0 & CC32 for bank select detection just before a Program Change message
    elif 'program_change' == data.type:
        # FIXME: should only be set when both have been received just before the Program Change
        bank_select_msb = dpg.get_value('mon_cc_val_0')
        bank_select_lsb = dpg.get_value('mon_cc_val_32')
        dpg.set_value(
            'pc_bank_num',
            int(127 * bank_select_lsb + bank_select_msb)
        )
        # FIXME: decode depending on the selected standard
        dpg.set_value('pc_bank_name', "TODO")
        set_value_preconv('pc_num', data.program)
        # Decode General MIDI names.
        # FIXME: decode depending on the selected standard
        dpg.set_value('pc_group_name', midi_const.GENERAL_MIDI_SOUND_SET_GROUPINGS[data.program])
        dpg.set_value('pc_name', midi_const.GENERAL_MIDI_SOUND_SET[data.program])
        # TODO: Optionally decode other modes names.
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
