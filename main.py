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
import math
import sys
import time
from typing import Any, Optional

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/
import mido  # https://mido.readthedocs.io/en/latest/
import mido.backends.rtmidi  # For PyInstaller

from dearpygui_ext.logger import mvLogger

global logger, log_window
DEBUG = True
INIT_FILENAME = "midiexplorer.ini"


def _init_logger() -> None:
    # TODO: allow logging to file
    # TODO: append/overwrite

    global logger, log_window

    with dpg.window(
            label="Log",
            width=1920,
            height=225,
            pos=[0, 815],
            show=DEBUG,
    ) as log_window:
        logger = mvLogger(log_window)
    if DEBUG:
        logger.log_level = 0  # TRACE
    else:
        logger.log_level = 2  # INFO


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


def save_init() -> None:
    dpg.save_init_file(INIT_FILENAME)


def _get_pin_text(pin: int | str) -> None:
    return dpg.get_value(dpg.get_item_children(pin, 1)[0])


def add_probe_data(timestamp: float, source: str, raw_msg: str) -> None:
    # TODO: insert new data at the top of the table
    with dpg.table_row(parent=probe_data_table):
        dpg.add_text(timestamp)
        dpg.add_selectable(label="source", span_columns=True)
        dpg.add_text(midi_data.hex())
        dpg.add_text(repr(midi_data))

    dpg.set_y_scroll(probe_data, -1.0)  # Autoscroll


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
    dpg.configure_item(log_window, show=not dpg.is_item_visible(log_window))


def decode(sender: int | str, app_data: Any) -> None:
    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(f"Raw message {app_data} decoded to: {decoded}.")

    dpg.set_value('generator_decoded_message', decoded)


if __name__ == '__main__':
    dpg.create_context()

    _init_logger()

    if not DEBUG:
        dpg.configure_app(init_file=INIT_FILENAME)

    with dpg.value_registry():
        dpg.add_string_value(tag="generator_decoded_message", default_value="")

    with dpg.window(
            label="MIDI Explorer",
            width=1920,
            height=1080,
            no_close=True,
            collapsed=False,
    ) as main_window:

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
                dpg.add_menu_item(label="Save configuration", callback=save_init)

            with dpg.menu(label="Display"):
                dpg.add_menu_item(label="Toggle Fullscreen (F11)", callback=dpg.toggle_viewport_fullscreen)
                dpg.add_menu_item(label="Toggle Log (F12)", callback=_toggle_log)

            dpg.add_menu_item(label="About")  # TODO

    with dpg.window(
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
            label="Probe",
            width=960,
            height=695,
            no_close=True,
            collapsed=False,
            pos=[960, 20]
    ) as probe_data:

        # TODO: Add auto-scrolling option
        # TODO: Add clear option
        # TODO: Allow sorting

        with dpg.table(header_row=True,
                       freeze_rows=1,
                       policy=dpg.mvTable_SizingFixedFit,
                       resizable=True,  # FIXME: Scroll the table instead of the window when available upstream
                       # scrollY=True,
                       clipper=True) as probe_data_table:
            dpg.add_table_column(label="Timestamp (ms)")
            dpg.add_table_column(label="Source")
            dpg.add_table_column(label="Raw Message (HEX)")
            dpg.add_table_column(label="Decoded Message", width_stretch=True)

    with dpg.window(
            label="Generator",
            width=960,
            height=100,
            no_close=True,
            collapsed=False,
            pos=[960, 715]
    ) as gen_data:

        message = dpg.add_input_text(label="Raw Message", hint="XXYYZZ", hexadecimal=True, callback=decode)
        dpg.add_input_text(label="Decoded", readonly=True, hint="Automatically decoded raw message",
                           source='generator_decoded_message')
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)

    _refresh_midi_ports()

    with dpg.handler_registry():
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=_toggle_log)  # Log on F12

    dpg.create_viewport(title='MIDI Explorer', width=1920, height=1080)

    # must be called before showing viewport
    # TODO: icons
    # dpg.set_viewport_small_icon("path/to/icon.ico")
    # dpg.set_viewport_large_icon("path/to/icon.ico")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(main_window, True)
    # dpg.start_dearpygui()
    while dpg.is_dearpygui_running():
        ###
        # MIDI Data receive & handling: Polling mode
        ###
        # FIXME: Use callback mode to avoid framerate dependency
        probe_in_user_data = dpg.get_item_user_data(probe_in)
        if probe_in_user_data:
            # logger.log_debug(f"Probe input has user data: {probe_in_user_data}")
            midi_data = probe_in_user_data["IN"].poll()
            if midi_data:
                logger.log_debug(f"Received MIDI data from probe input: {midi_data}")
                probe_thru_user_data = dpg.get_item_user_data(probe_thru)
                if probe_thru_user_data:
                    # logger.log_debug(f"Probe thru has user data: {probe_thru_user_data}")
                    logger.log_debug(f"Sending MIDI data to probe thru")
                    probe_thru_user_data["OUT"].send(midi_data)
                add_probe_data(int(round(time.time() * 1000)), probe_in, midi_data)
        dpg.render_dearpygui_frame()
    dpg.destroy_context()
