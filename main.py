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
import sys
import time
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
NS2MS = 1000
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

    # Connection
    port = None
    direction = None
    probe_pin = None
    if "IN_" in pin1_label:
        direction = pin1_label[:2]  # Extract 'IN'
        port_name = pin1_label[3:]  # Filter out 'IN_'
        logger.log_info(f"Opening MIDI input: {port_name}.")
        port = mido.open_input(port_name)
        if not dpg.get_value('polling'):
            port.callback = midi_receive_callback
            logger.log_info("Attached MIDI receive callback!")
        probe_pin = pin2
    elif "OUT_" in pin2_label:
        direction = pin2_label[:3]  # Extract 'OUT'
        port_name = pin2_label[4:]  # Filter out 'OUT_'
        logger.log_info(f"Opening MIDI output: {port_name}.")
        port = mido.open_output(port_name)
        probe_pin = pin1
    else:
        logger.log_warning(f"{pin1_label} or {pin2_label} is not a hardware port!")
    if port:
        logger.log_debug(f"Successfully opened {port!r}. Attaching it to the probe.")
        pin_user_data = {direction: port}
        dpg.set_item_user_data(probe_pin, pin_user_data)
        logger.log_debug(f"Attached {dpg.get_item_user_data(probe_pin)} to the {probe_pin} pin user data.")

        dpg.add_node_link(pin1, pin2, parent=sender)
        dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_TriangleFilled)
        dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_TriangleFilled)

        logger.log_info(f"Connected \"{node1_label}: {_get_pin_text(pin1)}\" to "
                        f"\"{node2_label}: {_get_pin_text(pin2)}\".")


# callback runs when user attempts to disconnect attributes
def delink_node_callback(sender: int | str, app_data: dpg.mvNodeLink, user_data: Optional[Any]) -> None:
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
    direction = None
    probe_pin = None
    if "IN_" in pin1_label:
        direction = pin1_label[:2]  # Extract 'IN'
        probe_pin = pin2
    elif "OUT_" in pin2_label:
        direction = pin2_label[:3]  # Extract 'OUT'
        probe_pin = pin1
    else:
        logger.log_warning(f"{pin1_label} or {pin2_label} is not a hardware port!")
    if direction:
        pin_user_data = dpg.get_item_user_data(probe_pin)
        port = pin_user_data[direction]

        logger.log_info(f"Closing & Detaching MIDI port {port} from the probe {direction} pin.")

        del pin_user_data[direction]
        dpg.set_item_user_data(probe_pin, pin_user_data)
        port.callback = None  # Needed to prevent threads from locking and crashing
        port.close()

        logger.log_debug(f"Deleting link {app_data!r}.")

        dpg.delete_item(app_data)

        dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_Triangle)
        dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_Triangle)

        logger.log_info(f"Disconnected \"{node1_label}: {_get_pin_text(pin1)}\" from "
                        f"\"{node2_label}: {_get_pin_text(pin2)}\".")


def toggle_log_callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    dpg.configure_item(log_win, show=not dpg.is_item_visible(log_win))


def decode_callback(sender: int | str, app_data: Any) -> None:
    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)


def polling_callback(sender: int | str, app_data: bool, user_data: Optional[Any]) -> None:
    """
    Sets/unsets the MIDI receive callback based off the widget checkbox's status

    :param sender: Polling checkbox widget
    :param app_data: Checkbox status
    :param user_data: Polling checkbox user data
    :return: None
    """
    pin = dpg.get_item_parent(sender)
    pin_user_data = dpg.get_item_user_data(pin)
    if pin_user_data:
        port = pin_user_data["IN"]

        if app_data:
            port.callback = None
            logger.log_info("Removed MIDI receive callback!")
        else:
            port.callback = midi_receive_callback
            logger.log_info("Attached MIDI receive callback!")

    dpg.set_value('polling', app_data)


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


def _extract_port_infos(name: str) -> dict:
    """
    Extracts ID and label from an rtmidi port name
    """
    # FIXME: is this cross-platform compatible?
    port_id = name.split()[-1]
    port_label = name[0:-len(port_id) - 1]
    logger.log_debug(f"Found port #{port_id}: {port_label}")
    return {
        'id': port_id,
        'label': port_label,
        'name': name,
    }


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


def _extract_ports_infos(names: list[str]) -> list[dict] | None:
    ports = []
    for name in names:
        ports.append(_extract_port_infos(name))
    return ports


def _refresh_midi_ports() -> None:
    dpg.configure_item(refresh_midi_modal, show=False)  # Close popup

    midi_inputs = _extract_ports_infos(mido.get_input_names())
    logger.log_debug(f"Available MIDI inputs: {midi_inputs}")

    midi_outputs = _extract_ports_infos(mido.get_output_names())
    logger.log_debug(f"Available MIDI outputs: {midi_outputs}")

    # TODO: add option to sort by ID or by name?
    # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?

    # Delete links
    dpg.delete_item(connections_editor, children_only=True, slot=0)

    # Delete ports
    dpg.delete_item(inputs_node, children_only=True)
    dpg.delete_item(outputs_node, children_only=True)

    for midi_in in midi_inputs:
        with dpg.node_attribute(label="IN_" + midi_in['name'],
                                attribute_type=dpg.mvNode_Attr_Output,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=inputs_node):
            with dpg.group(horizontal=True):
                dpg.add_text(midi_in['id'])
                dpg.add_text(midi_in['label'])
            with dpg.popup(dpg.last_item()):
                dpg.add_button(label=f"Hide {midi_in['label']} input")  # TODO
                dpg.add_button(label=f"Remove {midi_in['label']} input")  # TODO: for virtual ports only

    for midi_out in midi_outputs:
        with dpg.node_attribute(label="OUT_" + midi_out['name'],
                                attribute_type=dpg.mvNode_Attr_Input,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=outputs_node):
            with dpg.group(horizontal=True):
                dpg.add_text(midi_out['id'])
                dpg.add_text(midi_out['label'])
            with dpg.popup(dpg.last_item()):
                dpg.add_button(label=f"Hide {midi_out['label']} output")  # TODO
                dpg.add_button(label=f"Remove {midi_out['label']} output")  # TODO: for virtual ports only


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
    # TODO: color coding by event type
    global previous_timestamp, probe_data_counter

    previous_data = probe_data_counter
    probe_data_counter += 1

    with dpg.table_row(parent='probe_data_table', label=f'probe_data_{probe_data_counter}',
                       before=f'probe_data_{previous_data}'):
        # Timestamp (ms)
        dpg.add_text(str((timestamp - START_TIME) * NS2MS))

        # Delta (ms)
        delta = "0.0"
        if data.time:
            delta = data.time * NS2MS
            # logger.log_debug("Using rtmidi time delta")
        elif previous_timestamp is not None:
            delta = (timestamp - previous_timestamp) * NS2MS
        dpg.add_text(str(delta))
        previous_timestamp = timestamp

        # Source
        dpg.add_selectable(label="source", span_columns=True)

        # Raw message
        dpg.add_text(data.hex())

        # Decoded message
        if DEBUG:
            dpg.add_text(repr(data))

        # Channel
        if hasattr(data, 'channel'):
            dpg.add_text(data.channel)
            _mon_blink(data.channel)
        else:
            dpg.add_text("Global")
            _mon_blink('s')

        # Status
        dpg.add_text(data.type)
        _mon_blink(data.type)

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
        dpg.add_text(data1)

    # TODO: per message type color
    # dpg.highlight_table_row(table_id, i, [255, 0, 0, 100])

    # Autoscroll
    if dpg.get_value('probe_data_table_autoscroll'):
        dpg.set_y_scroll('act_det', -1.0)


def _mon_blink(channel: int | str) -> None:
    global START_TIME
    now = time.time() - START_TIME
    delay = dpg.get_value('blink_duration')
    target = f"mon_{channel}_active_until"
    until = now + delay
    dpg.set_value(target, until)
    dpg.bind_item_theme(f"mon_{channel}", '__red')
    # logger.log_debug(f"Current time:{time.time() - START_TIME}")
    # logger.log_debug(f"Blink {delay} until: {dpg.get_value(target)}")


def _update_blink_status() -> None:
    for channel in range(16):
        now = time.time() - START_TIME
        if dpg.get_value(f"mon_{channel}_active_until") < now:
            dpg.bind_item_theme(f"mon_{channel}", None)
    if dpg.get_value('mon_s_active_until') < now:
        dpg.bind_item_theme('mon_s', None)
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
        probe_thru_user_data["OUT"].send(midi_data)
    _add_probe_data(timestamp=timestamp,
                    source=probe_in,
                    data=midi_data)


def midi_receive_callback(midi_data: mido.Message) -> None:
    """
    MIDI data receive in "callback" mode.
    """
    timestamp = time.time()
    logger.log_debug(f"Callback data: {midi_data}")
    _handle_received_data(timestamp, midi_data)


def poll_processing() -> None:
    """
    MIDI data receive in "polling" mode.

    Shorter MIDI message (1-byte) interval is 320us.
    In polling mode we are bound to the frame rendering time.
    At 60FPS frame time is about 16.7ms
    This amounts to up to 53 MIDI bytes per frame (52.17)!
    That's why callback mode is to be preferred
    For reference: 60 FPS ~= 16.7 ms, 120 FPS ~= 8.3 ms
    """
    probe_in_user_data = dpg.get_item_user_data(probe_in)
    if probe_in_user_data:
        # logger.log_debug(f"Probe input has user data: {probe_in_user_data}")
        while True:
            timestamp = time.time()
            midi_data = probe_in_user_data["IN"].poll()
            if not midi_data:  # Could also use iter_pending() instead.
                break
            _handle_received_data(timestamp, midi_data)


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
        dpg.add_bool_value(tag='polling', default_value=False)
        dpg.add_string_value(tag='generator_decoded_message', default_value='')
        dpg.add_float_value(tag='blink_duration', default_value=.25)  # seconds
        for channel in range(16):  # Monitoring status
            dpg.add_float_value(tag=f"mon_{channel}_active_until", default_value=0)  # seconds
        dpg.add_float_value(tag='mon_s_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_active_sensing_active_until', default_value=0)  # seconds
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
        dpg.add_float_value(tag='mon_clock_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_start_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_continue_active_until', default_value=0)  # seconds
        dpg.add_float_value(tag='mon_stop_active_until', default_value=0)  # seconds
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
            with dpg.node(label="INPUTS",
                          pos=[10, 10]) as inputs_node:
                # Dynamically populated
                with dpg.popup(dpg.last_item()):
                    dpg.add_button(label="Add virtual input")

            with dpg.node(tag='probe_node',
                          label="PROBE",
                          pos=[360, 25]) as probe:
                with dpg.node_attribute(tag='probe_in',
                                        label="In",
                                        attribute_type=dpg.mvNode_Attr_Input,
                                        shape=dpg.mvNode_PinShape_Triangle) as probe_in:
                    dpg.add_text("In")

                with dpg.node_attribute(tag='probe_settings',
                                        label="Settings",
                                        attribute_type=dpg.mvNode_Attr_Static):
                    dpg.add_checkbox(tag='polling_checkbox',
                                     label="Polling",
                                     source='polling',
                                     callback=polling_callback)

                with dpg.node_attribute(tag='probe_thru',
                                        label="Thru",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle) as probe_thru:
                    dpg.add_text("Thru")

            with dpg.node(label="GENERATOR",
                          pos=[360, 125]):
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
                with dpg.popup(dpg.last_item()):
                    dpg.add_button(label="Add virtual output")

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
        dpg.add_child_window(tag='act_mon', label="Input activity monitor", height=50, border=False)

        with dpg.table(parent='act_mon', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(label="Title")
            for channel in range(18):
                dpg.add_table_column()

            with dpg.table_row():
                dpg.add_text("Channels:")
                for channel in range(16):  # Channel messages
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1}")
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text(f"Channel {channel + 1}")
                dpg.add_button(tag='mon_s', label="S")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Message")
            with dpg.table_row():
                dpg.add_text("Types:")

                # Channel voice messages (page 9)
                dpg.add_button(tag='mon_note_off', label="OFF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note-Off")
                dpg.add_button(tag='mon_note_on', label=" ON ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note-On")
                dpg.add_button(tag='mon_polytouch', label="PKPR")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Poly Key Pressure (Note Aftertouch)")
                dpg.add_button(tag='mon_control_change', label=" CC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Control Change")
                dpg.add_button(tag='mon_program_change', label=" PC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Program Change")
                dpg.add_button(tag='mon_aftertouch', label="CHPR")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Channel Pressure (Channel Aftertouch)")
                dpg.add_button(tag='mon_pitchwheel', label="PBC")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Pitch Bend Change")

                # TODO: Channel mode messages (page 20) (CC 120-127)

                # System exclusive messages
                dpg.add_button(tag='mon_sysex', label="SYX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Exclusive (aka SysEx)")

                # System common messages (page 27)
                dpg.add_button(tag='mon_quarter_frame', label=" QF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("MTC SMPTE Quarter Frame")
                dpg.add_button(tag='mon_songpos', label="SGPS")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Song Position")
                dpg.add_button(tag='mon_song_select', label="SGSL")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Song Select")
                dpg.add_button(tag='mon_tune_request', label=" TR ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Tune Request")
                # FIXME: mido is missing EOX
                dpg.add_button(tag='mon_eox', label="EOX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("End of Exclusive")

                # System real time messages (page 30)
                dpg.add_button(tag='mon_clock', label="CLK ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Clock")
                dpg.add_button(tag='mon_start', label="STRT")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Start")
                dpg.add_button(tag='mon_continue', label="CTNU")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Continue")
                dpg.add_button(tag='mon_stop', label="STOP")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Stop")
                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Active Sensing")
                dpg.add_button(tag='mon_reset', label="RST ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Reset")

            with dpg.table_row():
                dpg.add_text("Controllers:")
                # TODO: Control Changes (page 11)
                for controller in range(120):
                    if controller % 16:
                        # TODO: change row
                        pass
                    dpg.add_text("")

            with dpg.table_row():
                dpg.add_text("Channel mode:")
                # TODO: Channel modes (page 20)
                for mode in range(120, 128):
                    dpg.add_text("")

            with dpg.table_row():
                dpg.add_text("System exclusive:")
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
                dpg.add_text("Running status:")
                # FIXME: unimplemented upstream (page A-1)

        dpg.add_child_window(tag='probe_table_container', height=585)

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

        # TODO: Allow sorting
        # TODO: Show/hide columns
        # TODO: timegraph?

        dpg.add_child_window(parent='probe_table_container', tag='act_det', label="Details", height=525, border=False)
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
        _update_blink_status()

        if dpg.get_value('polling'):
            poll_processing()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()
