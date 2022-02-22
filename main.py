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
from dearpygui_ext.logger import mvLogger  # https://dearpygui-ext.readthedocs.io/en/latest/index.html

global logger, log_win, previous_timestamp, probe_data_counter

DEBUG = False
INIT_FILENAME = "midiexplorer.ini"
START_TIME = time.time()

previous_timestamp = START_TIME
probe_data_counter = 0


###
# Callbacks
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


def link_callback(sender: int | str,
                  app_data: (dpg.mvNodeAttribute, dpg.mvNodeAttribute),
                  user_data: Optional[Any]) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    pin1: dpg.mvNodeAttribute = app_data[0]
    pin2: dpg.mvNodeAttribute = app_data[1]
    node1_label, pin1_label, node2_label, pin2_label = _nodes_labels(pin1, pin2)

    logger.log_debug(f"Connection between pins: '{pin1}' & '{pin2}'.")

    # Only allow one link per pin for now
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
def delink_callback(sender: int | str, app_data: dpg.mvNodeLink, user_data: Optional[Any]) -> None:
    # Debug
    logger.log_debug(f"Entering {sys._getframe().f_code.co_name}:")
    logger.log_debug(f"\tSender: {sender!r}")
    logger.log_debug(f"\tApp data: {app_data!r}")
    logger.log_debug(f"\tUser data: {user_data!r}")

    # Get the pins that this link was connected to
    conf = dpg.get_item_configuration(app_data)
    pin1: dpg.mvNodeAttribute = conf['attr_1']
    pin2: dpg.mvNodeAttribute = conf['attr_2']
    node1_label, pin1_label, node2_label, pin2_label = _nodes_labels(pin1, pin2)

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
        port.close()

        logger.log_debug(f"Deleting link {app_data!r}.")

        dpg.delete_item(app_data)

        dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_Triangle)
        dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_Triangle)

        logger.log_info(f"Disconnected \"{node1_label}: {_get_pin_text(pin1)}\" from "
                        f"\"{node2_label}: {_get_pin_text(pin2)}\".")


def _toggle_log() -> None:
    dpg.configure_item(log_win, show=not dpg.is_item_visible(log_win))


def _decode(sender: int | str, app_data: Any) -> None:
    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)


###
# Functions
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


def _sort_ports(names: list) -> list | None:
    # TODO: extract the ID
    # TODO: add option to sort by ID rather than name
    # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?
    return sorted(set(names))


def _nodes_labels(pin1, pin2) -> tuple[str | None, str | None, str | None, str | None]:
    pin1_label = dpg.get_item_label(pin1)
    node1_label = dpg.get_item_label(dpg.get_item_parent(pin1))
    pin2_label = dpg.get_item_label(pin2)
    node2_label = dpg.get_item_label(dpg.get_item_parent(pin2))

    logger.log_debug(f"Identified pin1 '{pin1}' as '{pin1_label}' from '{node1_label}' node and "
                     f"pin2 '{pin2}' as '{pin2_label}' from '{node2_label}'.")

    return node1_label, pin1_label, node2_label, pin2_label


def _refresh_midi_ports() -> None:
    dpg.configure_item(refresh_midi_modal, show=False)  # Close popup

    midi_inputs = _sort_ports(mido.get_input_names())

    logger.log_debug(f"Available MIDI inputs: {midi_inputs}")

    midi_outputs = _sort_ports(mido.get_output_names())

    logger.log_debug(f"Available MIDI outputs: {midi_outputs}")

    # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?
    # Delete links
    dpg.delete_item(connections_editor, children_only=True, slot=0)

    # Delete ports
    dpg.delete_item(inputs_node, children_only=True)
    dpg.delete_item(outputs_node, children_only=True)

    for midi_in in midi_inputs:
        with dpg.node_attribute(label="IN_" + midi_in,
                                attribute_type=dpg.mvNode_Attr_Output,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=inputs_node):
            dpg.add_text(midi_in)
            with dpg.popup(dpg.last_item()):
                dpg.add_button(label=f"Remove {midi_in} input")  # TODO

    for midi_out in midi_outputs:
        with dpg.node_attribute(label="OUT_" + midi_out,
                                attribute_type=dpg.mvNode_Attr_Input,
                                shape=dpg.mvNode_PinShape_Triangle,
                                parent=outputs_node):
            dpg.add_text(midi_out)
            with dpg.popup(dpg.last_item()):
                dpg.add_button(label=f"Remove {midi_out} output")  # TODO


def _save_init() -> None:
    dpg.save_init_file(INIT_FILENAME)


def _get_pin_text(pin: int | str) -> None:
    return dpg.get_value(dpg.get_item_children(pin, 1)[0])


def _add_probe_data(timestamp: float, source: str, data: mido.Message) -> None:
    # TODO: insert new data at the top of the table
    # TODO: color coding by event type
    global previous_timestamp, probe_data_counter

    previous_data = probe_data_counter
    probe_data_counter += 1

    with dpg.table_row(parent='probe_data_table', label=f'probe_data_{probe_data_counter}',
                       before=f'probe_data_{previous_data}'):
        # Timestamp (ms)
        dpg.add_text((timestamp - START_TIME) * 1000)
        # Delta (ms)
        # In polling mode we are bound to the frame rendering time.
        # For reference: 60 FPS ~= 16.7 ms, 120 FPS ~= 8.3 ms
        if previous_timestamp is not None:
            dpg.add_text((timestamp - previous_timestamp) * 1000)
        else:
            dpg.add_text("0.0")
        previous_timestamp = timestamp
        # Source
        dpg.add_selectable(label="source", span_columns=True)
        # Raw message
        dpg.add_text(data.hex())
        # Decoded message
        if DEBUG:
            dpg.add_text(repr(midi_data))
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
        if 'note' in data.type:
            dpg.add_text(data.note)  # TODO: decode to human readable
            dpg.add_text(data.velocity)
            if data.velocity == 0:  # This is equivalent to a note_off message
                _mon_blink('note_off')
        elif 'control' in data.type:
            dpg.add_text(data.control)  # TODO: decode to human readable
            dpg.add_text(data.value)
        elif 'pitchwheel' in data.type:
            dpg.add_text(data.pitch)
            dpg.add_text("")
        elif 'sysex' in data.type:
            dpg.add_text(data.data)
            dpg.add_text("")  # TODO: decode device ID
        else:
            # TODO: decode other types
            dpg.add_text("")
            dpg.add_text("")

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


def _update_blink_status():
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


def _clear_probe_data_table():
    dpg.delete_item('probe_data_table', children_only=True, slot=1)
    _init_details_table_data()


def _init_details_table_data():
    # Initial data for reverse scrolling
    with dpg.table_row(parent='probe_data_table', label='probe_data_0'):
        pass


if __name__ == '__main__':
    dpg.create_context()

    _init_logger()

    if not DEBUG:
        dpg.configure_app(init_file=INIT_FILENAME)

    with dpg.value_registry():
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

            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Save configuration", callback=_save_init)

            with dpg.menu(label="Display"):
                dpg.add_menu_item(label="Toggle Fullscreen (F11)", callback=dpg.toggle_viewport_fullscreen)
                dpg.add_menu_item(label="Toggle Log (F12)", callback=_toggle_log)

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

            # TODO: Add a toggle between input polling and callback modes

        with dpg.node_editor(callback=link_callback,
                             delink_callback=delink_callback) as connections_editor:
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

        # TODO: Allow sorting
        # TODO: Show/hide columns
        # TODO: timegraph?

        # Input Activity Monitor
        dpg.add_child_window(tag='act_mon', label="Input activity monitor", height=65, border=False)

        with dpg.table(parent='act_mon', header_row=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(width_stretch=True)  # Blink duration slider
            for channel in range(17):
                dpg.add_table_column()

            with dpg.theme(tag='__red'):
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 0, 0))

            with dpg.table_row():
                dpg.add_slider_float(tag='blink_duration_slider',
                                     min_value=0, max_value=0.5, source='blink_duration',
                                     callback=lambda:
                                     dpg.set_value('blink_duration', dpg.get_value('blink_duration_slider')))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Persistence (s)")
                for channel in range(16):  # Channel messages
                    dpg.add_button(tag=f"mon_{channel}", label=f"{channel + 1}")
                    with dpg.tooltip(dpg.last_item()):
                        dpg.add_text(f"Channel {channel + 1}")
                dpg.add_button(tag='mon_s', label="S")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Message")
            with dpg.table_row():
                dpg.add_button(tag='mon_active_sensing', label=" AS ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Active Sensing")
                dpg.add_button(tag='mon_note_off', label="OFF ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note Off")
                dpg.add_button(tag='mon_note_on', label=" ON ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Note On")
                dpg.add_button(tag='mon_polytouch', label="POLY")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Polytouch (aka Pressure)")
                dpg.add_button(tag='mon_control_change', label=" CC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Control Change")
                dpg.add_button(tag='mon_program_change', label=" PC ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Program Change")
                dpg.add_button(tag='mon_aftertouch', label="AFTT")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("After Touch (aka Channel Pressure)")
                dpg.add_button(tag='mon_pitchwheel', label="PTCH")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Pitch Wheel")
                dpg.add_button(tag='mon_sysex', label="SYX ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("System Exclusive (aka SysEx)")
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
                dpg.add_button(tag='mon_reset', label="RST ")
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Reset")

        dpg.add_child_window(tag='probe_table_container')

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

        dpg.add_child_window(parent='probe_table_container', tag='act_det', label="Details", height=530, border=False)
        with dpg.table(parent='act_det',
                       tag='probe_data_table',
                       header_row=False,  # FIXME: True when table scrolling will be implemented upstream
                       freeze_rows=0,  # FIXME: 1 when table scrolling will be implemented upstream
                       policy=dpg.mvTable_SizingStretchSame,
                       # scrollY=True,  # FIXME: Scroll the table instead of the window when available upstream
                       clipper=True):
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

        message = dpg.add_input_text(label="Raw Message", hint="XXYYZZ (HEX)", hexadecimal=True, callback=_decode)
        dpg.add_input_text(label="Decoded", readonly=True, hint="Automatically decoded raw message",
                           source='generator_decoded_message')
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)

    _refresh_midi_ports()

    with dpg.handler_registry():
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=_toggle_log)  # Log on F12

    dpg.create_viewport(title='MIDI Explorer', width=1920, height=1080)

    # Icons must be called before showing viewport
    # TODO: icons
    # dpg.set_viewport_small_icon("path/to/icon.ico")
    # dpg.set_viewport_large_icon("path/to/icon.ico")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(main_win, True)
    while dpg.is_dearpygui_running():  # Replaces dpg.start_dearpygui()
        _update_blink_status()
        ###
        # MIDI Data receive & handling: Polling mode
        ###
        # FIXME: Use callback mode to avoid framerate dependency
        probe_in_user_data = dpg.get_item_user_data(probe_in)
        if probe_in_user_data:
            # logger.log_debug(f"Probe input has user data: {probe_in_user_data}")
            while True:
                timestamp = time.time()
                midi_data = probe_in_user_data["IN"].poll()
                if not midi_data:
                    break
                logger.log_debug(f"Received MIDI data from probe input: {midi_data}")
                probe_thru_user_data = dpg.get_item_user_data(probe_thru)
                if probe_thru_user_data:
                    # logger.log_debug(f"Probe thru has user data: {probe_thru_user_data}")
                    logger.log_debug(f"Sending MIDI data to probe thru")
                    probe_thru_user_data["OUT"].send(midi_data)
                _add_probe_data(timestamp=timestamp,
                                source=probe_in,
                                data=midi_data)
        dpg.render_dearpygui_frame()
    dpg.destroy_context()
