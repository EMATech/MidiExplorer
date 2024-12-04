# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Standard MIDI File (SMF) window and management.
"""
import re
from typing import Any, Optional

import midi_const
from dearpygui import dearpygui as dpg
from mido import Message, MetaMessage, MidiFile

from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers import smf
from midiexplorer.gui.helpers.callbacks.debugging import (
    enable as enable_dpg_cb_debugging
)


def create() -> None:
    """Creates the SMF window.

    """

    ###
    # Values
    ###
    with dpg.value_registry():
        dpg.add_string_value(tag="SMF")

    ###
    # Window
    ###
    posx = (1_920 - 1_280) / 2
    posy = (1_080 - 720) / 2
    width = 1_280
    height = 720
    with dpg.window(
            tag='smf_win',
            label="Standard MIDI File",
            width=width,
            height=height,
            no_close=False,
            collapsed=False,
            pos=[posx, posy],
            show=False if not DEBUG else True,
    ):
        ###
        # MENU
        ###
        smf.create_selectors()
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="Open", callback=smf.open_file)
                if DEBUG:  # TODO: Implement recorder or editor first!
                    dpg.add_menu_item(label="Save", callback=smf.save_file, enabled=False)
                    dpg.add_menu_item(label="Save as", callback=smf.save_file_as, enabled=False)
                dpg.add_menu_item(tag='smf_close', label="Close", callback=smf.close_file, enabled=False)

        ###
        # Content
        ###

        ###
        # Recoder & Player
        # TODO!
        ###

        ###
        # Analyzer
        ###
        dpg.add_group(tag='smf_container')
        init()


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

    dpg.configure_item('smf_win', show=not dpg.is_item_visible('smf_win'))

    menu_item = 'menu_tools_smf'
    if sender != menu_item:  # Update menu checkmark when coming from the shortcut handler
        dpg.set_value(menu_item, not dpg.get_value(menu_item))


def init():
    clear()
    dpg.disable_item('smf_close')
    # TODO: allow drag-dropping a supported file
    # TODO: center button
    dpg.add_button(label="Open", callback=smf.open_file, parent='smf_container')


def clear():
    dpg.delete_item('smf_container', children_only=True)


def populate(file_bytes: bytes, midifile: MidiFile):
    clear()
    dpg.enable_item('smf_close')
    parent = 'smf_container'
    file_size = len(file_bytes)

    progress = ProgressBar(parent)

    with dpg.group(tag='smf_contents', parent=parent, horizontal=True):
        with dpg.group(label='RAW', tag='smf_raw_contents', show=False):
            with dpg.table(header_row=True, freeze_rows=1, policy=dpg.mvTable_SizingStretchProp,
                           borders_innerH=False, borders_outerH=True,
                           borders_innerV=False, borders_outerV=True,
                           scrollY=True, width=640):
                # Update progress indicator
                progress.state("Raw")

                # Header
                dpg.add_table_column(label="Offset (hex)")
                for index in range(0x00, 0x0F + 1):
                    dpg.add_table_column(label=f"{index:02X}")
                dpg.add_table_column(label="Decoded (ASCII)")

                digits = len(hex(file_size)) - 2  # Remove 0x
                for offset in range(0x00, file_size + 1, 0x10):
                    # Update progress indicator
                    progress.value((offset / file_size) / 2)
                    with dpg.table_row():
                        dpg.add_text(f"{offset:0{digits}X}")  # Offset
                        chunk = file_bytes[offset:offset + 0x0F + 1]
                        for index in range(0x00, 0x0F + 1):
                            try:
                                dpg.add_selectable(
                                    label=f"{chunk[index]:02X}",
                                    # callback=_selected_hex,  # FIXME
                                    user_data=(offset, index)
                                )
                            except IndexError:  # We may reach the end of the file earlier than the table width
                                dpg.add_text()
                        dotted_ascii = re.sub(r'[^\x32-\x7f]', '.', chunk.decode('ascii', errors='replace'))
                        dpg.add_text(dotted_ascii)

            # if DEBUG:
            #    dpg.add_text(f"{file_bytes!r}", wrap=80)

        # Update progress indicator
        progress.value(.5)

        with dpg.group(label='Decoded', tag='smf_decoded_contents', show=False):
            # Update progress indicator
            progress.state("Events")

            with dpg.tree_node(label=f"{midifile.filename}", default_open=True):

                dpg.add_tree_node(label=f"Size: {file_size} bytes", leaf=True)

                with dpg.tree_node(label="Header", default_open=True, selectable=True):
                    dpg.configure_item(
                        dpg.last_item(),
                        # callback=_selected_decode,  # FIXME
                        user_data=range(0, 7),
                    )
                    smf_format = midi_const.SMF_HEADER_FORMATS[midifile.type]
                    dpg.add_tree_node(label=f"Format: {midifile.type} ({smf_format})", leaf=True, selectable=True)
                    dpg.add_tree_node(label=f"Number of tracks: {len(midifile.tracks)}", leaf=True, selectable=True)
                    # FIXME: Upstream: mido. Support SMPTE division format.
                    dpg.add_tree_node(label=f"Division: {midifile.ticks_per_beat} ticks per quarter-note",
                                      leaf=True, selectable=True)

                tracks_total = len(midifile.tracks)
                for i, track in enumerate(midifile.tracks):
                    # Update progress indicator
                    progress.value(((i / tracks_total) / 2) + .5)
                    with dpg.tree_node(label=f"Track #{i} {track.name}", selectable=True):
                        for j, event in enumerate(track):
                            if isinstance(event, MetaMessage):
                                event_type = 'Meta'
                            # FIXME: Upstream: mido. Support Sysex event type and subtypes.
                            if isinstance(event, Message):
                                event_type = 'MIDI'
                            with dpg.tree_node(label=f"Event #{j} {event_type} {event.type}", selectable=True):
                                dpg.add_tree_node(label=f"Delta-time: {event.time}", leaf=True, selectable=True)
                                with dpg.tree_node(label=f"Type: {event.type}", selectable=True):
                                    # TODO: decode
                                    if DEBUG:
                                        dpg.add_tree_node(label=f"{event!r}", leaf=True)

            # if DEBUG:
            #     dpg.add_text(f"{midifile!r}")

        # Update progress indicator
        progress.state("Complete")
        progress.value(1.0)


def _selected_decode(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Generic Dear PyGui callback for debug purposes.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used by DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)
    if app_data:
        for index in user_data:
            row = int(index / 0x0F)
            index = index % 0x0F
            # FIXME: highlight file portions when selecting in decoded view
            pass
    raise NotImplementedError


def _selected_hex(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Generic Dear PyGui callback for debug purposes.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used by DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)
    if app_data:
        offset, index = user_data
        # FIXME: highlight decoded portions when selecting in the file view
        pass
    raise NotImplementedError


class ProgressBar:
    def __init__(self, parent):
        self._value: float = 0.0
        self._human_readable: str = "0 %"
        self._overlay_suffix: str = "(Starting)"

        with dpg.tree_node(label="Analysis in progress...", parent=parent, default_open=True):
            self._container = dpg.last_item()
            self._progress_bar: int = dpg.add_progress_bar(default_value=0.0,
                                                           parent=self._container)
        self._update_progress()

    def value(self, value: float) -> None:
        self._value = value
        self._human_readable: str = f"{round(value * 100)}%"
        self._update_progress()
        if value == .5:
            dpg.show_item('smf_raw_contents')
        if value == 1.0:
            dpg.show_item('smf_decoded_contents')
            dpg.configure_item(self._container, label="Analysis complete!", bullet=True)
            dpg.set_value(self._container, False)

    def state(self, value: str) -> None:
        self._overlay_suffix = f"({value})"
        self._update_progress()

    def _update_progress(self) -> None:
        dpg.set_value(self._progress_bar, self._value)
        dpg.configure_item(self._progress_bar,
                           overlay=f"{self._human_readable} {self._overlay_suffix}")
