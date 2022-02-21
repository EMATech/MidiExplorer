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
from typing import Any, Optional, Tuple

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
            show=DEBUG
    ) as log_window:
        logger = mvLogger(log_window)
    if DEBUG:
        logger.log_level = 0  # TRACE
    else:
        logger.log_level = 2  # INFO


def _init_midi() -> None:
    mido.set_backend('mido.backends.rtmidi')
    logger.log_debug(f"Using {mido.backend.name}.")
    logger.log_debug(f"RtMidi APIs:{mido.backend.module.get_api_names()}")


def _sort_ports(names: list) -> list | None:
    # TODO: extract the ID
    # TODO: add option to sort by ID rather than name
    # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?
    return sorted(set(names))


def _nodes_labels(node1, node2) -> tuple[str | None, str | None, str | None, str | None]:
    node1_label = dpg.get_item_label(node1)
    node1_parent_label = dpg.get_item_label(dpg.get_item_parent(node1))
    node2_label = dpg.get_item_label(node2)
    node2_parent_label = dpg.get_item_label(dpg.get_item_parent(node2))
    return node1_parent_label, node1_label, node2_parent_label, node2_label


def _refresh_midi_ports() -> None:
    dpg.configure_item(refresh_midi_modal, show=False)  # Close popup

    midi_inputs = _sort_ports(mido.get_input_names())
    logger.log_debug(repr(midi_inputs))
    midi_outputs = _sort_ports(mido.get_output_names())
    logger.log_debug(repr(midi_outputs))

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
    logger.log_debug(f"Sender: {sender}  \t App data:{app_data} \t User data:{user_data}")


# callback runs when user attempts to connect attributes
def link_callback(sender: int | str, app_data: Any) -> None:
    logger.log_debug(f"Create link{app_data!r}")
    # app_data -> (link_id1, link_id2)
    dpg.add_node_link(app_data[0], app_data[1], parent=sender)
    dpg.configure_item(app_data[0], shape=dpg.mvNode_PinShape_TriangleFilled)
    dpg.configure_item(app_data[1], shape=dpg.mvNode_PinShape_TriangleFilled)

    # TODO: effective connection

    node1_parent_label, node1_label, node2_parent_label, node2_label = _nodes_labels(app_data[0], app_data[1])
    logger.log_info(f"Connect \"{node1_parent_label} {node1_label}\" to \"{node2_parent_label} {node2_label}\"")


# callback runs when user attempts to disconnect attributes
def delink_callback(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    # Get the nodes that this link was connected to
    conf = dpg.get_item_configuration(app_data)  # In attr_1 and attr_2

    # FIXME: only change shape if no other link is active on the node!
    dpg.configure_item(conf['attr_1'], shape=dpg.mvNode_PinShape_Triangle)
    dpg.configure_item(conf['attr_2'], shape=dpg.mvNode_PinShape_Triangle)

    node1_parent_label, node1_label, node2_parent_label, node2_label = _nodes_labels(conf['attr_1'], conf['attr_2'])
    logger.log_info(f"Disconnect \"{node1_parent_label} {node1_label}\" from \"{node2_parent_label} {node2_label}\"")

    logger.log_debug(f"Delete link {app_data!r}")

    # app_data -> link_id
    dpg.delete_item(app_data)

    # TODO: effective disconnection


def _toggle_log() -> None:
    dpg.configure_item(log_window, show=not dpg.is_item_visible(log_window))


def decode(sender: int | str, app_data: Any) -> None:
    try:
        decoded = repr(mido.Message.from_hex(app_data))
    except (TypeError, ValueError) as e:
        decoded = f"Warning: {e!s}"
        pass

    logger.log_debug(decoded)

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
                dpg.add_menu_item(label="Toggle Log (F12)", callback=_toggle_log())

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

            with dpg.node(label="PROBE",
                          pos=[360, 25]):
                with dpg.node_attribute(label="In",
                                        attribute_type=dpg.mvNode_Attr_Input,
                                        shape=dpg.mvNode_PinShape_Triangle):
                    dpg.add_text("In")

                with dpg.node_attribute(label="Thru",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle):
                    dpg.add_text("Thru")

            with dpg.node(label="GENERATOR",
                          pos=[360, 125]):
                with dpg.node_attribute(label="Out",
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        shape=dpg.mvNode_PinShape_Triangle):
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
    ):

        with dpg.table(header_row=True, policy=dpg.mvTable_SizingStretchProp) as probe_table:
            dpg.add_table_column(label="Timestamp")
            dpg.add_table_column(label="Source")
            dpg.add_table_column(label="Raw Message")
            dpg.add_table_column(label="Decoded Message")

            with dpg.table_row():
                # FIXME: sample message
                dpg.add_text("0,00")
                dpg.add_selectable(label="Sample input", span_columns=True)
                dpg.add_text("F0 XX YY F7")
                dpg.add_text("SySex")

    with dpg.window(
            label="Generator",
            width=960,
            height=100,
            no_close=True,
            collapsed=False,
            pos=[960, 715]
    ):

        message = dpg.add_input_text(label="Raw Message", hint="XXYYZZ", hexadecimal=True, callback=decode)
        dpg.add_input_text(label="Decoded", readonly=True, hint="Automatically decoded raw message",
                           source='generator_decoded_message')
        dpg.add_button(tag="generator_send_button", label="Send", enabled=False)

    _refresh_midi_ports()

    with dpg.handler_registry():
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=_toggle_log)

    dpg.create_viewport(title='MIDI Explorer', width=1920, height=1080)

    # must be called before showing viewport
    # TODO: icons
    # dpg.set_viewport_small_icon("path/to/icon.ico")
    # dpg.set_viewport_large_icon("path/to/icon.ico")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(main_window, True)
    dpg.start_dearpygui()
    dpg.destroy_context()
