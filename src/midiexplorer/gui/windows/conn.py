# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Connections window and management.

TODO: separate presentation from processing logic
"""
import platform
import time
from collections import OrderedDict
from typing import Optional, Any

import mido
from dearpygui import dearpygui as dpg

from midiexplorer.dpg_helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.dpg_helpers.constants.slots import MOST, SPECIAL
from midiexplorer.gui.config import DEBUG
from midiexplorer.gui.logger import Logger
from midiexplorer.gui.windows.probe.data import add
from midiexplorer.midi.ports import MidiInPort, MidiOutPort, midi_in_queue, midi_in_lock


def _install_input_callback(in_port: MidiInPort, dest: MidiOutPort | str):
    """Opens a MIDI Input Port and set its callback if required.

    :param in_port: MIDI Input Port
    :param dest: Destination module or MIDI Output Port

    """
    logger = Logger()

    logger.log_info(f"Opening MIDI input: {in_port}.")
    in_port.open(dest)

    if dpg.get_value('input_mode') == 'Callback':
        in_port.callback()
        logger.log_info(f"Attached MIDI receive callback to {in_port.name}!")


def _link_nodes(pin1, pin2, sender):
    """Links two DPG nodes and updates visual cues.

    :param pin1: Pin of the first node
    :param pin2: Pin of the second node
    :param sender: DPG sender element

    """
    logger = Logger()

    node1_label, _, node2_label, _ = _pins_nodes_labels(pin1, pin2)

    dpg.add_node_link(pin1, pin2, parent=sender)

    dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_TriangleFilled)
    dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_TriangleFilled)

    logger.log_info(f"Connected \"{node1_label}: {_get_pin_text(pin1)}\" to "
                    f"\"{node2_label}: {_get_pin_text(pin2)}\".")


def _extract_pin_node_labels(pin: dpg.mvNodeCol_Pin) -> tuple[str | None, str | None]:
    """Extracts pin and parent node labels from pin object.

    :param pin: The pin from which to extract data.
    :return: Node and pin labels

    """
    pin_label = dpg.get_item_label(pin)
    node_label = dpg.get_item_label(dpg.get_item_parent(pin))
    return node_label, pin_label


def _pins_nodes_labels(pin1: dpg.mvNodeCol_Pin,
                       pin2: dpg.mvNodeCol_Pin) -> tuple[str | None, str | None, str | None, str | None]:
    """Extracts pins and nodes labels from two pin objects.

    :param pin1: First pin.
    :param pin2: Second pin.
    :return: First and second Node and Pin labels.

    """
    node1_label, pin1_label = _extract_pin_node_labels(pin1)
    node2_label, pin2_label = _extract_pin_node_labels(pin2)
    return node1_label, pin1_label, node2_label, pin2_label


def _dedupe_port_names(names: list[str]) -> list[str]:
    """Removes duplicates in a port names list.

    Needed in Mac OS X because every port is listed twice for some reason
    and in Linux because the Through port is also listed twice.

    TODO: test more. May have adverse effects in the presence of multiple identical yet distinct devices.

    :param: names: List of port names to deduplicate.
    :return: Deduplicated list of port names.

    """
    names = list(OrderedDict.fromkeys(names))
    return names


def _extract_input_ports_infos(names: list[str]) -> list[MidiInPort] | None:
    """Get a list of MIDI Input Port objects for a list of port names.

    :param names: Input ports names
    :return: MIDI Input Port objects list

    """
    names = _dedupe_port_names(names)
    ports = []
    for name in names:
        ports.append(MidiInPort(name))
    return ports


def _extract_output_ports_infos(names: list[str]) -> list[MidiOutPort] | None:
    """Get a list of MIDI Output Port objects for a list of port names.

    :param names: Output ports names
    :return: MIDI Output Port objects list

    """
    names = _dedupe_port_names(names)
    ports = []
    for name in names:
        ports.append(MidiOutPort(name))
    return ports


def _get_pin_text(pin: int | str) -> str:
    """Get the main label of a pin.

    :param pin: DPG node pin to get the label from
    :return: Main label of the pin

    """
    text = dpg.get_value(dpg.get_item_children(pin, slot=MOST)[0])
    if text is None:
        # Extract from I/O
        mvgroup = dpg.get_item_children(pin, slot=MOST)[0]
        mvtext_index = 0
        if platform.system() == "Windows":  # We have port indexe numbers
            mvtext_index = 1
        mvtext = dpg.get_item_children(mvgroup, slot=MOST)[mvtext_index]
        text = dpg.get_value(mvtext)
    return text


def link_node_callback(sender: int | str,
                       app_data: (dpg.mvNodeAttribute, dpg.mvNodeAttribute),
                       user_data: Optional[Any]) -> None:
    """Callback called when a link between two nodes is created.

    Sets up the underlying data flow, updates DPG internal state and  visual cues.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    # Get the pins we are connecting to and related metadata
    pin1: dpg.mvNodeAttribute = app_data[0]
    pin2: dpg.mvNodeAttribute = app_data[1]
    _, pin1_label, _, pin2_label = _pins_nodes_labels(pin1, pin2)

    logger.log_debug(f"Connection between pins: '{pin1}' & '{pin2}'.")

    # Only allow one link per pin for now
    # TODO: Automatically add merger node when linked to multiple nodes.
    for children in dpg.get_item_children(dpg.get_item_parent(dpg.get_item_parent(pin1)), slot=SPECIAL):
        if dpg.get_item_info(children)['type'] == 'mvAppItemType::mvNodeLink':
            link_conf = dpg.get_item_configuration(children)
            if pin1 == link_conf['attr_1'] or pin2 == link_conf['attr_1'] or \
                    pin1 == link_conf['attr_2'] or pin2 == link_conf['attr_2']:
                logger.log_warning("Only one connection per pin is allowed at the moment.")
                return

    # Retrieve associated MIDI ports if any
    pin1_user_data = dpg.get_item_user_data(pin1)
    pin2_user_data = dpg.get_item_user_data(pin2)

    # TODO: Handle I/O port to any module
    # TODO: Handle module to module

    # Connection
    module_target = None
    module_pin = None
    if isinstance(pin1_user_data, MidiInPort) and isinstance(pin2_user_data, MidiOutPort):
        # Handles port to port
        logger.log_info(f"Opening MIDI output: {pin2_user_data.name}.")
        pin2_user_data.open()
        _install_input_callback(pin1_user_data, pin2)
        _link_nodes(pin1, pin2, sender)
    elif isinstance(pin1_user_data, MidiInPort):
        # Handles port to module
        _install_input_callback(pin1_user_data, pin2)
        module_target = pin1_user_data
        module_pin = pin2
    elif isinstance(pin2_user_data, MidiOutPort):
        # Handles module to port
        logger.log_info(f"Opening MIDI output: {pin2_user_data.name}.")
        pin2_user_data.open()
        module_pin = pin1
        module_target = pin2_user_data
    else:
        logger.log_warning(f"{pin1_label} and/or {pin2_label} is not a hardware port!")

    if module_target:
        logger.log_debug(f"Successfully opened {module_target!r}. Attaching it to the module.")
        dpg.set_item_user_data(module_pin, module_target)
        logger.log_debug(f"Attached {dpg.get_item_user_data(module_pin)} to the {module_pin} pin user data.")
        _link_nodes(pin1, pin2, sender)


def delink_node_callback(sender: int | str,
                         app_data: dpg.mvNodeLink,
                         user_data: Optional[Any]) -> None:
    """Callback called when a link between two nodes is removed.

    Shuts down the underlying data flow, update DPG internal state and visual cues.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    logger = Logger()

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    # Retrieve the pins that this link was connected to
    conf = dpg.get_item_configuration(app_data)
    pin1: dpg.mvNodeAttribute = conf['attr_1']
    pin2: dpg.mvNodeAttribute = conf['attr_2']
    node1_label, _, node2_label, _ = _pins_nodes_labels(pin1, pin2)

    logger.log_debug(f"Disconnection between pins: '{pin1}' & '{pin2}'.")

    # Retrieve associated MIDI ports if any
    pin1_user_data = dpg.get_item_user_data(pin1)
    pin2_user_data = dpg.get_item_user_data(pin2)

    logger.log_debug(f"Found user data: '{pin1_user_data}' & '{pin2_user_data}'.")
    if isinstance(pin1_user_data, MidiInPort) and isinstance(pin2_user_data, MidiOutPort):
        # Handles port to port
        pin1_user_data: MidiInPort
        pin2_user_data: MidiOutPort
        logger.log_info(f"Detaching & closing MIDI port {pin1_user_data.label} from {pin2_user_data.label}.")
        pin1_user_data.close()
        pin2_user_data.close()
    elif isinstance(pin1_user_data, MidiInPort):
        pin1_user_data: MidiInPort
        logger.log_info(f"Detaching & closing MIDI port {pin1_user_data.label} from the probe In.")
        pin1_user_data.close()
        dpg.set_item_user_data(pin2, None)
    elif isinstance(pin2_user_data, MidiOutPort):
        pin2_user_data: MidiOutPort
        logger.log_info(f"Detaching & closing MIDI port {pin2_user_data.label} from the probe Out.")
        dpg.set_item_user_data(pin1, None)
        pin2_user_data.close()

    logger.log_debug(f"Deleting link {app_data!r}.")
    dpg.delete_item(app_data)

    # Update visual cues
    dpg.configure_item(pin1, shape=dpg.mvNode_PinShape_Triangle)
    dpg.configure_item(pin2, shape=dpg.mvNode_PinShape_Triangle)

    logger.log_info(f"Disconnected \"{node1_label}: {_get_pin_text(pin1)}\" from "
                    f"\"{node2_label}: {_get_pin_text(pin2)}\".")


def input_mode_callback(sender: int | str, app_data: bool, user_data: Optional[Any]) -> None:
    """Sets/unsets the MIDI receive callback based off the widget checkbox's status.

    :param sender: Polling checkbox widget
    :param app_data: Checkbox status
    :param user_data: Polling checkbox user data

    """
    logger = Logger()

    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    pin_user_data = dpg.get_item_user_data('probe_in')
    if pin_user_data:
        if app_data == 'Polling':
            pin_user_data.polling()
            logger.log_info("Removed MIDI receive callback!")
        else:
            pin_user_data.callback()
            logger.log_info("Attached MIDI receive callback!")
    else:
        raise NotImplementedError

    dpg.set_value('input_mode', app_data)


def refresh_midi_ports() -> None:
    """Refreshes the available MIDI ports.

    """
    logger = Logger()

    dpg.configure_item('refresh_midi_modal', show=False)  # Close popup

    # Retrieve MIDI Input Ports objects
    midi_inputs = _extract_input_ports_infos(mido.get_input_names())
    logger.log_debug(f"Available MIDI inputs: {midi_inputs}")

    # Retrieve MIDI Output Ports objects
    midi_outputs = _extract_output_ports_infos(mido.get_output_names())
    logger.log_debug(f"Available MIDI outputs: {midi_outputs}")

    # Delete links
    dpg.delete_item('connections_editor', children_only=True, slot=0)

    # Delete ports
    dpg.delete_item('inputs_node', children_only=True)
    dpg.delete_item('outputs_node', children_only=True)

    # Input ports sorting
    if DEBUG:
        # TODO: implement
        with dpg.node_attribute(
                tag='inputs_settings',
                parent='inputs_node',
                attribute_type=dpg.mvNode_Attr_Static,
                label="Settings",
        ):
            with dpg.group(label="Sort", horizontal=True):
                dpg.add_text("Sorting:")
                dpg.add_radio_button(items=("None", "by ID", "by Name"),
                                     default_value="None")  # TODO:, callback=sort_inputs_callback)
                # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?

    # Input ports node and pins
    for midi_in in midi_inputs:
        with dpg.node_attribute(
                label=midi_in.name,
                parent='inputs_node',
                attribute_type=dpg.mvNode_Attr_Output,
                shape=dpg.mvNode_PinShape_Triangle,
                user_data=midi_in,
        ):
            with dpg.group(horizontal=True):
                if midi_in.num is not None:
                    dpg.add_text(midi_in.num)
                dpg.add_text(midi_in.label)
                # with dpg.popup(dpg.last_item()):
                #    dpg.add_button(label=f"Hide {midi_in.label} input")  # TODO
                #    dpg.add_button(label=f"Remove {midi_in.label} input")  # TODO: for virtual ports only

    # Add virtual input port
    if DEBUG:
        with dpg.popup('inputs_node'):
            dpg.add_button(label="Add virtual input")

    # Outputs ports sorting
    if DEBUG:
        # TODO: implement
        with dpg.node_attribute(parent='outputs_node',
                                tag='outputs_settings',
                                label="Settings",
                                attribute_type=dpg.mvNode_Attr_Static):
            with dpg.group(label="Sort", horizontal=True):
                dpg.add_text("Sorting:")
                dpg.add_radio_button(items=("None", "by ID", "by Name"),
                                     default_value="None")  # TODO:, callback=sort_outputs_callback)
                # FIXME: do the sorting in the GUI to prevent disconnection of existing I/O?

    # Output ports node and pins
    for midi_out in midi_outputs:
        with dpg.node_attribute(
                label=midi_out.name,
                attribute_type=dpg.mvNode_Attr_Input,
                shape=dpg.mvNode_PinShape_Triangle,
                parent='outputs_node',
                user_data=midi_out,
        ):
            with dpg.group(horizontal=True):
                if midi_out.num is not None:
                    dpg.add_text(midi_out.num)
                dpg.add_text(midi_out.label)
                # with dpg.popup(dpg.last_item()):
                #    dpg.add_button(label=f"Hide {midi_out.label} output")  # TODO
                #    dpg.add_button(label=f"Remove {midi_out.label} output")  # TODO: for virtual ports only

    # Add virtual output port
    if DEBUG:
        with dpg.popup(parent='outputs_node'):
            dpg.add_button(label="Add virtual output")


def create() -> None:
    """Creates the connections window.

    Including its menus, associated items and node editor.

    """
    with dpg.value_registry():
        dpg.add_string_value(tag='input_mode', default_value='Callback')

    # FIXME: compute dynamically?
    conn_win_height = 510
    if DEBUG:
        conn_win_height = 400

    with dpg.window(
            tag="conn_win",
            label="Connections",
            width=900,
            height=conn_win_height,
            no_close=True,
            collapsed=False,
            pos=[0, 20]
    ):
        # TODO: connection presets management

        with dpg.menu_bar():
            with dpg.window(label="Refresh MIDI ports", show=False, popup=True, tag='refresh_midi_modal'):
                dpg.add_text("Warning: All links will be removed.")
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="OK", width=75, callback=refresh_midi_ports)
                    dpg.add_button(
                        label="Cancel",
                        width=75,
                        callback=lambda: dpg.configure_item('refresh_midi_modal', show=False)
                    )

            with dpg.menu(label="Settings"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Input mode:")
                    dpg.add_radio_button(
                        items=("Callback", "Polling"),
                        source='input_mode',
                        callback=input_mode_callback
                    )

            with dpg.menu(label="Ports"):
                dpg.add_menu_item(
                    label="Refresh",
                    callback=lambda: dpg.configure_item('refresh_midi_modal', show=True)
                )
                if DEBUG:
                    # TODO: implement
                    with dpg.menu(label="Add virtual"):
                        dpg.add_menu_item(label="Input")
                        dpg.add_menu_item(label="Output")
                        dpg.add_menu_item(label="I/O")

            if DEBUG:
                # TODO: implement & add to context menu
                with dpg.menu(label="Tools"):
                    with dpg.menu(label="Add"):
                        dpg.add_menu_item(label="Probe")
                        dpg.add_menu_item(label="Generator")
                        dpg.add_menu_item(label="Filter/translator")
                        dpg.add_menu_item(label="Merger")
                        dpg.add_menu_item(label="Splitter")

        with dpg.node_editor(
                tag='connections_editor',
                callback=link_node_callback,
                delink_callback=delink_node_callback,
                # TODO: handle delinking in a right-click popup on the link. Upstream?
        ):
            with dpg.node(
                    tag='inputs_node',
                    pos=[10, 25],
                    label="INPUTS",
            ):
                # Dynamically populated
                pass

            # TODO: allow an arbitrary number of probes
            with dpg.node(
                    tag='probe_node',
                    pos=[360, 25],
                    label="PROBE",
            ):
                with dpg.node_attribute(
                        tag='probe_in',
                        attribute_type=dpg.mvNode_Attr_Input,
                        shape=dpg.mvNode_PinShape_Triangle,
                        label="In",
                ):
                    dpg.add_text("In")

                with dpg.node_attribute(
                        tag='probe_thru',
                        attribute_type=dpg.mvNode_Attr_Output,
                        shape=dpg.mvNode_PinShape_Triangle,
                        label="Thru",
                ):
                    dpg.add_text("Thru")

            if DEBUG:
                # TODO: implement
                with dpg.node(label="GENERATOR",
                              pos=[360, 165]):
                    with dpg.node_attribute(
                            tag='gen_out',
                            attribute_type=dpg.mvNode_Attr_Output,
                            shape=dpg.mvNode_PinShape_Triangle,
                            label="Out",
                    ):
                        dpg.add_text("Out", indent=2)

            if DEBUG:
                # TODO: implement
                with dpg.node(label="FILTER/TRANSLATOR",
                              pos=[360, 250]):
                    with dpg.node_attribute(
                            label="In",
                            attribute_type=dpg.mvNode_Attr_Input,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("In")
                    with dpg.node_attribute(
                            label="Out",
                            attribute_type=dpg.mvNode_Attr_Output,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("Out", indent=2)

            if DEBUG:
                # TODO: implement
                with dpg.node(label="MERGER",
                              pos=[360, 350]):
                    with dpg.node_attribute(
                            label="In1",
                            attribute_type=dpg.mvNode_Attr_Input,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("In1")
                    with dpg.node_attribute(
                            label="In2",
                            attribute_type=dpg.mvNode_Attr_Input,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("In2")
                    with dpg.node_attribute(
                            label="Out",
                            attribute_type=dpg.mvNode_Attr_Output,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("Out", indent=2)

            if DEBUG:
                # TODO: implement
                with dpg.node(
                        tag='splitter_node',
                        pos=[360, 475],
                        label="SPLITTER",
                ):
                    with dpg.node_attribute(
                            label="In",
                            attribute_type=dpg.mvNode_Attr_Input,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("In")
                    with dpg.node_attribute(
                            label="Out1",
                            attribute_type=dpg.mvNode_Attr_Output,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("Out1", indent=2)
                    with dpg.node_attribute(
                            label="Out2",
                            attribute_type=dpg.mvNode_Attr_Output,
                            shape=dpg.mvNode_PinShape_Triangle,
                    ):
                        dpg.add_text("Out2", indent=2)

            with dpg.node(
                    tag='outputs_node',
                    pos=[610, 25],
                    label="OUTPUTS",
            ):
                # Dynamically populated
                pass

        refresh_midi_ports()


def handle_received_data(timestamp: float, source: str, dest: str, midi_data: mido.Message) -> None:
    """Handles received MIDI data and echoes "Soft Thru" messages.

    :param timestamp: MIDI data timestamp.
    :param source: Source MIDI port.
    :param dest: Destination MIDI port or module.
    :param midi_data: RAW MIDI message.

    """
    logger = Logger()

    logger.log_debug(f"Received MIDI data from {source} to {dest} at {timestamp}: {midi_data}")

    port = None
    try:
        port = dpg.get_item_user_data(dest)
    except SystemError:
        logger.log_warning(f"Port for item #{dest} not found!")
        pass
    if isinstance(port, MidiOutPort):
        logger.log_debug(f"Echoing MIDI data to midi output {port.label}")
        port.port.send(midi_data)
    if dest == 'probe_in':
        probe_thru_user_data = dpg.get_item_user_data('probe_thru')
        if probe_thru_user_data:
            # logger.log_debug(f"Probe thru has user data: {probe_thru_user_data}")
            logger.log_debug("Echoing MIDI data to probe thru")
            probe_thru_user_data.port.send(midi_data)
        add(
            timestamp=timestamp,
            source=source,
            data=midi_data,
        )


def poll_processing() -> None:
    """MIDI data receive in "Polling" mode.

    Shorter MIDI message (1-byte) interval is 320us (10 symbols: 1 start bit, 8 data bits, 1 stop bit).
    In polling mode we are bound to the frame rendering time.
    At 60 FPS frame time is about 16.7 ms
    This amounts to up to 53 MIDI bytes per frame (52.17)!
    That's why callback mode is to be preferred.
    For reference: 60 FPS ~= 16.7 ms, 120 FPS ~= 8.3 ms

    """
    # TODO: subscribe pattern for multi module handling?

    # inputs = []
    #
    # for pin in dpg.get_item_children('connections_editor', slot=MOST):
    #     if pin is MidiInPort:
    #         inputs.append(dpg.get_item_user_data(pin))
    #
    # for input in inputs:
    #     for midi_message in input.port.iter_pending():
    #         timestamp = time.time()
    #         queue.put((timestamp, input.label, input.dest, midi_message))

    probe_in_user_data = dpg.get_item_user_data('probe_in')
    if probe_in_user_data:
        # logger.log_debug(f"Probe input has user data: {probe_in_user_data}")
        for midi_message in probe_in_user_data.port.iter_pending():
            timestamp = time.time()
            with midi_in_lock:
                midi_in_queue.put((timestamp, probe_in_user_data.label, probe_in_user_data.dest, midi_message))
