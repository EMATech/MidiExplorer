# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
`MIDI Explorer`
===============

* Author(s): Raphaël Doursenaud <rdoursenaud@free.fr>
"""
import multiprocessing
import sys
import threading
import time
from abc import ABC
from typing import Any, Optional

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/
import mido  # https://mido.readthedocs.io/en/latest/
import mido.backends.rtmidi  # For PyInstaller
from dearpygui.demo import show_demo
from dearpygui_ext.logger import mvLogger  # https://dearpygui-ext.readthedocs.io/en/latest/index.html

from midi.constants import NOTE_OFF_VELOCITY

###
# PROGRAM CONSTANTS
###
START_TIME = time.time()  # Initialize ASAP
US2MS = 1000
INIT_FILENAME = "midiexplorer.ini"
DEBUG = True

###
# GLOBAL VARIABLES
#
# FIXME: global variables should ideally be eliminated as they are a poor programming style
###
global logger, log_win, previous_timestamp, probe_data_counter
previous_timestamp = START_TIME
probe_data_counter = 0
input_lock = threading.Lock()
input_queue = multiprocessing.SimpleQueue()


class MidiPort(ABC):
    # FIXME: is this cross-platform compatible?
    port: mido.ports.BasePort

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

    @property
    def num(self):
        return self.name.split()[-1]

    @property
    def label(self):
        return self.name[0:-len(self.num) - 1]


class MidiInPort(MidiPort):
    port: mido.ports.BaseInput
    pass


class MidiOutPort(MidiPort):
    port: mido.ports.BaseOutput
    pass


###
# DEAR PYGUI CALLBACKS
###
def callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """
    Generic Dear PyGui callback for debug purposes
    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.
    :return:
    """
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")


def link_node_callback(sender: int | str,
                       app_data: (dpg.mvNodeAttribute, dpg.mvNodeAttribute),
                       user_data: Optional[Any]) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    pin1: dpg.mvNodeAttribute = app_data[0]
    pin2: dpg.mvNodeAttribute = app_data[1]
    node1_label, pin1_label, node2_label, pin2_label = _pins_nodes_labels(pin1, pin2)

    logger.log_debug(f"Connection between pins: '{pin1}' & '{pin2}'.")

    # Only allow one link per pin for now
    # TODO: Automatically add merger node when linked to multiple nodes.
    for children in dpg.get_item_children(dpg.get_item_parent(dpg.get_item_parent(pin1)), 0):
        if dpg.get_item_info(children)['type'] == 'mvAppItemType::mvNodeLink':
            link_conf = dpg.get_item_configuration(children)
            if pin1 == link_conf['attr_1'] or pin2 == link_conf['attr_1'] or \
                    pin1 == link_conf['attr_2'] or pin2 == link_conf['attr_2']:
                logger.log_warning("Only one connection per pin is allowed at the moment.")
                return

    pin1_user_data = dpg.get_item_user_data(pin1)
    pin2_user_data = dpg.get_item_user_data(pin2)

    # FIXME: This only works for I/O port to probe
    # TODO: Handle port to port
    # TODO: Handle I/O port to any module

    # Connection
    probe_target_port = None
    probe_pin = None
    if type(pin1_user_data) is MidiInPort:
        logger.log_info(f"Opening MIDI input: {pin1_user_data}.")
        pin1_user_data.port = mido.open_input(pin1_user_data.name)
        if dpg.get_value('input_mode') == 'Callback':
            with input_lock:
                pin1_user_data.port.callback = midi_receive_callback
                logger.log_info("Attached MIDI receive callback!")
        probe_target_port = pin1_user_data
        probe_pin = pin2
    elif type(pin2_user_data) is MidiOutPort:
        logger.log_info(f"Opening MIDI output: {pin2_user_data.name}.")
        pin2_user_data.port = mido.open_output(pin2_user_data.name)
        probe_target_port = pin2_user_data
        probe_pin = pin1
    else:
        logger.log_warning(f"{pin1_label} or {pin2_label} is not a hardware port!")

    if probe_target_port:
        logger.log_debug(f"Successfully opened {probe_target_port!r}. Attaching it to the probe.")
        dpg.set_item_user_data(probe_pin, probe_target_port)
        logger.log_debug(f"Attached {dpg.get_item_user_data(probe_pin)} to the {probe_pin} pin user data.")

        dpg.add_node_link(pin1, pin2, parent=sender)
        dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_TriangleFilled)
        dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_TriangleFilled)

        logger.log_info(f"Connected \"{node1_label}: {_get_pin_text(pin1)}\" to "
                        f"\"{node2_label}: {_get_pin_text(pin2)}\".")


# callback runs when user attempts to disconnect attributes
def delink_node_callback(sender: int | str,
                         app_data: dpg.mvNodeLink,
                         user_data: Optional[Any]) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    # Get the pins that this link was connected to
    conf = dpg.get_item_configuration(app_data)
    pin1: dpg.mvNodeAttribute = conf['attr_1']
    pin2: dpg.mvNodeAttribute = conf['attr_2']
    node1_label, pin1_label, node2_label, pin2_label = _pins_nodes_labels(pin1, pin2)

    logger.log_debug(f"Disconnection between pins: '{pin1}' & '{pin2}'.")

    # Disconnection
    pin1_user_data = dpg.get_item_user_data(pin1)
    pin2_user_data = dpg.get_item_user_data(pin2)

    logger.log_debug(f"Found user data: '{pin1_user_data}' & '{pin2_user_data}'.")

    if type(pin1_user_data) is MidiInPort:
        logger.log_info(f"Detaching & closing MIDI port {pin1_user_data.label} from the probe In.")
        with input_lock:
            pin1_user_data.port.callback = None  # Needed to prevent threads from locking and crashing
            pin1_user_data.port.close()
            dpg.set_item_user_data(pin2, None)

    if type(pin2_user_data) is MidiOutPort:
        logger.log_info(f"Detaching & closing MIDI port {pin2_user_data.label} from the probe Out.")
        pin2_user_data.port.close()
        dpg.set_item_user_data(pin1, None)

    logger.log_debug(f"Deleting link {app_data!r}.")
    dpg.delete_item(app_data)

    dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_Triangle)
    dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_Triangle)

    logger.log_info(f"Disconnected \"{node1_label}: {_get_pin_text(pin1)}\" from "
                    f"\"{node2_label}: {_get_pin_text(pin2)}\".")


def toggle_log_callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    dpg.configure_item(log_win, show=not dpg.is_item_visible(log_win))


def decode_callback(sender: int | str, app_data: Any) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)


def input_mode_callback(sender: int | str, app_data: bool, user_data: Optional[Any]) -> None:
    """
    Sets/unsets the MIDI receive callback based off the widget checkbox's status

    :param sender: Polling checkbox widget
    :param app_data: Checkbox status
    :param user_data: Polling checkbox user data
    :return: None
    """
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    pin_user_data = dpg.get_item_user_data(probe_in)
    if pin_user_data:
        if app_data == 'Polling':
            with input_lock:
                pin_user_data.port.callback = None
                logger.log_info("Removed MIDI receive callback!")
        else:
            with input_lock:
                pin_user_data.port.callback = midi_receive_callback
                logger.log_info("Attached MIDI receive callback!")

    dpg.set_value('input_mode', app_data)


###
# PROGRAM FUNCTIONS
###
def _init_logger() -> None:
    # TODO: allow logging to file
    # TODO: append/overwrite

    global logger, log_win

    with dpg.window(
            tag='log_win',
            label="Log",
            width=1920,
            height=225,
            pos=[0, 815],
            show=DEBUG,
    ) as log_win:
        logger = mvLogger(log_win)
    if DEBUG:
        logger.log_level = 0  # TRACE
    else:
        logger.log_level = 2  # INFO

    logger.log_debug(f"Application started at {START_TIME}")


def _init_midi() -> None:
    mido.set_backend('mido.backends.rtmidi')

    logger.log_debug(f"Using {mido.backend.name}")
    logger.log_debug(f"RtMidi APIs: {mido.backend.module.get_api_names()}")


def _extract_pin_node_labels(pin: dpg.mvNodeCol_Pin) -> tuple[str | None, str | None]:
    """
    Extracts pin and parent node labels from pin object
    """
    pin_label = dpg.get_item_label(pin)
    node_label = dpg.get_item_label(dpg.get_item_parent(pin))
    return node_label, pin_label


def _pins_nodes_labels(pin1: dpg.mvNodeCol_Pin,
                       pin2: dpg.mvNodeCol_Pin) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Extracts pins and nodes labels from two pin objects
    """
    node1_label, pin1_label = _extract_pin_node_labels(pin1)
    node2_label, pin2_label = _extract_pin_node_labels(pin2)
    return node1_label, pin1_label, node2_label, pin2_label


def _extract_input_ports_infos(names: list[str]) -> list[MidiInPort] | None:
    ports = []
    for name in names:
        ports.append(MidiInPort(name))
    return ports


def _extract_output_ports_infos(names: list[str]) -> list[MidiOutPort] | None:
    ports = []
    for name in names:
        ports.append(MidiOutPort(name))
    return ports


def _refresh_midi_ports() -> None:
    dpg.configure_item(refresh_midi_modal, show=False)  # Close popup

    midi_inputs = _extract_input_ports_infos(mido.get_input_names())
    logger.log_debug(f"Available MIDI inputs: {midi_inputs}")

    midi_outputs = _extract_output_ports_infos(mido.get_output_names())
    logger.log_debug(f"Available MIDI outputs: {midi_outputs}")

    # Delete links
    dpg.delete_item(connections_editor, children_only=True, slot=0)

    # Delete ports
    dpg.delete_item(inputs_node, children_only=True)
    dpg.delete_item(outputs_node, children_only=True)

    # Input ports
    with dpg.node_attribute(parent=inputs_node,
                            tag='inputs_settings',
                            label="Settings",
                            attribute_type=dpg.mvNode_Attr_Static):

        with dpg.group(label="Sort", horizontal=True):
            dpg.add_text("Sorting:")
            dpg.add_radio_button(items=("None", "by ID", "by Name"),
                                 default_value="None")  # TODO:, callback=sort_inputs_callback)
            # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?

    for midi_in in midi_inputs:
        with dpg.node_attribute(label=midi_in.name,
                                attribute_type=dpg.mvNode_Attr_Output,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=inputs_node,
                                user_data=midi_in):
            with dpg.group(horizontal=True):
                dpg.add_text(midi_in.num)
                dpg.add_text(midi_in.label)
                # with dpg.popup(dpg.last_item()):
                #    dpg.add_button(label=f"Hide {midi_in.label} input")  # TODO
                #    dpg.add_button(label=f"Remove {midi_in.label} input")  # TODO: for virtual ports only

    with dpg.popup(inputs_node):
        dpg.add_button(label="Add virtual input")

    # Outputs ports
    with dpg.node_attribute(parent=outputs_node,
                            tag='outputs_settings',
                            label="Settings",
                            attribute_type=dpg.mvNode_Attr_Static):
        with dpg.group(label="Sort", horizontal=True):
            dpg.add_text("Sorting:")
            dpg.add_radio_button(items=("None", "by ID", "by Name"),
                                 default_value="None")  # TODO:, callback=sort_outputs_callback)
            # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?

    for midi_out in midi_outputs:
        with dpg.node_attribute(label=midi_out.name,
                                attribute_type=dpg.mvNode_Attr_Input,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=outputs_node,
                                user_data=midi_out):
            with dpg.group(horizontal=True):
                dpg.add_text(midi_out.num)
                dpg.add_text(midi_out.label)
                # with dpg.popup(dpg.last_item()):
                #    dpg.add_button(label=f"Hide {midi_out.label} output")  # TODO
                #    dpg.add_button(label=f"Remove {midi_out.label} output")  # TODO: for virtual ports only

    with dpg.popup(parent=outputs_node):
        dpg.add_button(label="Add virtual output")


def _save_init() -> None:
    dpg.save_init_file(INIT_FILENAME)


def _get_pin_text(pin: int | str) -> None:
    return dpg.get_value(dpg.get_item_children(pin, 1)[0])


def _add_probe_data(timestamp: float, source: str, data: mido.Message) -> None:
    """
    Decodes and present data received from the probe.

    :param timestamp:
    :param source:
    :param data:
    :return:
    """
    # TODO: insert new data at the top of the table
    global previous_timestamp, probe_data_counter

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

        # Channel
        if hasattr(data, 'channel'):
            chan_label = data.channel
            _mon_blink('c')
            _mon_blink(chan_label)
        else:
            chan_label = "Global"
            _mon_blink('s')
        dpg.add_text(chan_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(chan_label)

        # Status
        stat_label = data.type
        _mon_blink(stat_label)
        dpg.add_text(stat_label)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(stat_label)

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
    global START_TIME
    now = time.time() - START_TIME
    delay = dpg.get_value('blink_duration')
    target = f"mon_{indicator}_active_until"
    until = now + delay
    dpg.set_value(target, until)
    dpg.bind_item_theme(f"mon_{indicator}", '__red')
    # logger.log_debug(f"Current time:{time.time() - START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def _update_blink_status() -> None:
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


def _clear_probe_data_table() -> None:
    dpg.delete_item('probe_data_table', children_only=True, slot=1)
    _init_details_table_data()


def _init_details_table_data() -> None:
    # Initial data for reverse scrolling
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass


def _handle_received_data(timestamp: float, midi_data: mido.Message) -> None:
    """
    Handle received MIDI data and echoes "Soft Thru" messages.
    """
    logger.log_debug(f"Received MIDI data from probe input: {midi_data}")
    probe_thru_user_data = dpg.get_item_user_data(probe_thru)
    if probe_thru_user_data:
        # logger.log_debug(f"Probe thru has user data: {probe_thru_user_data}")
        logger.log_debug(f"Echoing MIDI data to probe thru")
        probe_thru_user_data.port.send(midi_data)
    _add_probe_data(timestamp=timestamp,
                    source=probe_in,
                    data=midi_data)


def poll_processing() -> None:
    """
    MIDI data receive in "Polling" mode.

    Shorter MIDI message (1-byte) interval is 320us (10 symbols: 1 start bit, 8 data bits, 1 stop bit).
    In polling mode we are bound to the frame rendering time.
    At 60 FPS frame time is about 16.7 ms
    This amounts to up to 53 MIDI bytes per frame (52.17)!
    That's why callback mode is to be preferred
    For reference: 60 FPS ~= 16.7 ms, 120 FPS ~= 8.3 ms
    """
    probe_in_user_data = dpg.get_item_user_data(probe_in)
    if probe_in_user_data:
        # logger.log_debug(f"Probe input has user data: {probe_in_user_data}")
        for midi_message in probe_in_user_data.port.iter_pending():
            timestamp = time.time()
            input_queue.put((timestamp, midi_message))


###
# MIDO callback
###
def midi_receive_callback(midi_message: mido.Message) -> None:
    """
    MIDI data receive in "Callback" mode.

    Recommended.
    """
    with input_lock:
        timestamp = time.time()
        # logger.log_debug(f"Callback data: {midi_message}")
        input_queue.put((timestamp, midi_message))


###
#  MAIN PROGRAM
###
if __name__ == '__main__':
    dpg.create_context()

    _init_logger()

    if DEBUG:
        logger.log_debug(f"Using MIDO:")
        logger.log_debug(f"\t - version: {mido.__version__}")
        logger.log_debug(f"\t - backend: {mido.backend}")

    if not DEBUG:
        dpg.configure_app(init_file=INIT_FILENAME)

    ###
    # DEAR PYGUI VALUES
    ###
    with dpg.value_registry():
        dpg.add_string_value(tag='input_mode', default_value='Callback')
        dpg.add_string_value(tag='generator_decoded_message', default_value='')
        dpg.add_float_value(tag='blink_duration', default_value=.25)  # seconds
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
        # Per standard, consider note-on with velocity set to 0 as note-off
        dpg.add_bool_value(tag='zero_velocity_note_on_is_note_off', default_value=True)

    ###
    # DEAR PYGUI THEMES
    ###
    with dpg.theme(tag='__red'):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))

    with dpg.window(
            tag='main_win',
            label="MIDI Explorer",
            width=1920,
            height=1080,
            no_close=True,
            collapsed=False,
    ) as main_win:

        with dpg.menu_bar():
            if DEBUG:
                with dpg.menu(label="Debug"):
                    dpg.add_menu_item(label="Show About", callback=lambda: dpg.show_tool(dpg.mvTool_About))
                    dpg.add_menu_item(label="Show Metrics", callback=lambda: dpg.show_tool(dpg.mvTool_Metrics))
                    dpg.add_menu_item(label="Show Documentation", callback=lambda: dpg.show_tool(dpg.mvTool_Doc))
                    dpg.add_menu_item(label="Show Debug", callback=lambda: dpg.show_tool(dpg.mvTool_Debug))
                    dpg.add_menu_item(label="Show Style Editor", callback=lambda: dpg.show_tool(dpg.mvTool_Style))
                    dpg.add_menu_item(label="Show Font Manager", callback=lambda: dpg.show_tool(dpg.mvTool_Font))
                    dpg.add_menu_item(label="Show Item Registry",
                                      callback=lambda: dpg.show_tool(dpg.mvTool_ItemRegistry))
                    dpg.add_menu_item(label="Show ImGui Demo", callback=lambda: dpg.show_imgui_demo())
                    dpg.add_menu_item(label="Show ImPlot Demo", callback=lambda: dpg.show_implot_demo())
                    dpg.add_menu_item(label="Show Dear PyGui Demo", callback=lambda: show_demo())

            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Save configuration", callback=_save_init)

            with dpg.menu(label="Display"):
                dpg.add_menu_item(label="Toggle Fullscreen (F11)", callback=dpg.toggle_viewport_fullscreen)
                dpg.add_menu_item(label="Toggle Log (F12)", callback=toggle_log_callback)

            dpg.add_menu_item(label="About")  # TODO

    with dpg.window(
            tag="conn_win",
            label="Connections",
            width=960,
            height=795,
            no_close=True,
            collapsed=False,
            pos=[0, 20]
    ):
        # TODO: connection presets management

        with dpg.menu_bar():
            with dpg.window(label="Refresh MIDI ports", show=False, popup=True) as refresh_midi_modal:
                dpg.add_text("Warning: All links will be removed.")
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="OK", width=75, callback=_refresh_midi_ports)
                    dpg.add_button(label="Cancel", width=75,
                                   callback=lambda: dpg.configure_item(refresh_midi_modal, show=False))

            dpg.add_menu_item(label="Refresh MIDI ports",
                              callback=lambda: dpg.configure_item(refresh_midi_modal, show=True))

            dpg.add_menu_item(label="Add probe")  # TODO

        with dpg.node_editor(callback=link_node_callback,
                             delink_callback=delink_node_callback) as connections_editor:
            with dpg.node(tag='inputs_node',
                          label="INPUTS",
                          pos=[10, 10]) as inputs_node:
                # Dynamically populated
                pass

            with dpg.node(tag='probe_node',
                          label="PROBE",
                          pos=[360, 25]) as probe:
                with dpg.node_attribute(tag='probe_settings',
                                        label="Settings",
                                        attribute_type=dpg.mvNode_Attr_Static):
                    with dpg.group(horizontal=True):
                        dpg.add_text("Mode:")
                        dpg.add_radio_button(items=("Callback", "Polling"),
                                             source='input_mode',
                                             callback=input_mode_callback)

                with dpg.node_attribute(tag='probe_in',
                                        label="In",
                                        attribute_type=dpg.mvNode_Attr_Input,
                                        shape=dpg.mvNode_PinShape_Triangle) as probe_in:
                    dpg.add_text("In")

                with dpg.node_attribute(tag='probe_thru',
                                        label="Thru",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle) as probe_thru:
                    dpg.add_text("Thru")

            with dpg.node(label="GENERATOR",
                          pos=[360, 165]):
                with dpg.node_attribute(label="Out",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle) as gen_out:
                    dpg.add_text("Out", indent=2)

            with dpg.node(label="FILTER/TRANSLATOR",
                          pos=[360, 250]):
                with dpg.node_attribute(label="In",
                                        attribute_type=dpg.mvNode_Attr_Input,
                                        shape=dpg.mvNode_PinShape_Triangle):
                    dpg.add_text("In")
                with dpg.node_attribute(label="Out",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle):
                    dpg.add_text("Out", indent=2)

            with dpg.node(label="OUTPUTS",
                          pos=[610, 10]) as outputs_node:
                # Dynamically populated
                pass

    with dpg.window(
            tag='probe_win',
            label="Probe",
            width=960,
            height=695,
            no_close=True,
            collapsed=False,
            pos=[960, 20]
    ) as probe_data:

        with dpg.menu_bar():
            with dpg.menu(label="Settings"):
                dpg.add_slider_float(tag='blink_duration_slider',
                                     label="Persistence (s)",
                                     min_value=0, max_value=0.5, source='blink_duration',
                                     callback=lambda:
                                     dpg.set_value('blink_duration', dpg.get_value('blink_duration_slider')))
                dpg.add_checkbox(label="0 velocity note-on is note-off (default, MIDI specification compliant)",
                                 source='zero_velocity_note_on_is_note_off')

        # Input Activity Monitor
        dpg.add_child_window(tag='act_mon', label="Input activity monitor", height=210, border=False)

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
                dpg.add_text("Messages")

                dpg.add_text("Channel Voice")

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

                dpg.add_text("Channel Mode")

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("System Common")

                # System exclusive messages
                dpg.add_button(tag='mon_sysex', label="SYX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Exclusive aka SysEx\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF0:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF0:03d}\n"
                                 f"Binary:\t\t{0xF0:08b}\n")

                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("MIDI Time Code (MTC) SMPTE Quarter Frame\n"
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

                # FIXME: mido is missing EOX (TODO: send PR)
                dpg.add_button(tag='mon_end_of_exclusive', label="EOX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("End of Exclusive\n"
                                 "\n"
                                 f"Hexadecimal:\t{' ':5}{0xF7:01X}\n"
                                 f"Decimal:\t\t{' ':4}{0xF7:03d}\n"
                                 f"Binary:\t\t{0xF7:08b}\n")

            with dpg.table_row():
                dpg.add_text()

                dpg.add_text("System Real-Time")

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

        dpg.add_child_window(tag='probe_table_container', height=425)

        # Details buttons
        # FIXME: separated to not scroll with table child window until table scrolling is supported
        dpg.add_child_window(parent='probe_table_container', tag='act_det_btns', label="Buttons", height=40,
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
            dpg.add_table_column(label="Channel")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Data 1")
            dpg.add_table_column(label="Data 2")

        # TODO: Allow sorting
        # TODO: Show/hide columns
        # TODO: timegraph?

        dpg.add_child_window(parent='probe_table_container', tag='act_det', label="Details", height=370, border=False)
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
            dpg.add_table_column(label="Channel")
            dpg.add_table_column(label="Status")
            dpg.add_table_column(label="Data 1")
            dpg.add_table_column(label="Data 2")

            _init_details_table_data()

    with dpg.window(
            tag='gen_win',
            label="Generator",
            width=960,
            height=100,
            no_close=True,
            collapsed=False,
            pos=[960, 715]
    ) as gen_data:

        message = dpg.add_input_text(label="Raw Message", hint="XXYYZZ (HEX)", hexadecimal=True,
                                     callback=decode_callback)
        dpg.add_input_text(label="Decoded", readonly=True, hint="Automatically decoded raw message",
                           source='generator_decoded_message')
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)

    _refresh_midi_ports()

    with dpg.handler_registry():
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=toggle_log_callback)  # Log on F12

    ###
    # DEAR PYGUI SETUP
    ###
    dpg.create_viewport(title='MIDI Explorer', width=1920, height=1080)

    # Icons must be called before showing viewport
    # TODO: icons
    # dpg.set_viewport_small_icon("path/to/icon.ico")
    # dpg.set_viewport_large_icon("path/to/icon.ico")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(main_win, True)

    ###
    # MAIN LOOP
    ###
    while dpg.is_dearpygui_running():  # Replaces dpg.start_dearpygui()
        if dpg.get_value('input_mode') == 'Polling':
            with input_lock:
                poll_processing()

        while not input_queue.empty():
            _handle_received_data(*input_queue.get())

        _update_blink_status()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()
