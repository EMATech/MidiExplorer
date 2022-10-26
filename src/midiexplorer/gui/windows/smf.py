# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Standard MIDI File (SMF) window and management.
"""
import re

from dearpygui import dearpygui as dpg
from mido import MidiFile, MetaMessage, Message

import midiexplorer.midi.constants
from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers import smf


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
            no_close=True,
            collapsed=False,
            pos=[posx, posy],
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
        # TODO: split screen and display decoded tree on the left and file contents on the right like wireshark
        dpg.add_group(tag='smf_contents', horizontal=True)
        init()

        # TODO: allow drag-dropping a supported file


def populate(file_bytes: bytes, midifile: MidiFile):
    clear()
    dpg.enable_item('smf_close')
    parent = 'smf_contents'

    file_size = len(file_bytes)

    with dpg.group(label='RAW', tag='smf_raw_contents', parent=parent):
        with dpg.table(header_row=True, freeze_rows=1, policy=dpg.mvTable_SizingStretchProp,
                       borders_innerH=False, borders_outerH=True,
                       borders_innerV=False, borders_outerV=True,
                       scrollY=True, width=640):
            # Header
            dpg.add_table_column(label="Offset (hex)")
            for index in range(0x00, 0x0F + 1):
                dpg.add_table_column(label=f"{index:02X}")
            dpg.add_table_column(label="Decoded (ASCII)")

            digits = len(hex(file_size)) + 1
            for offset in range(0x00, file_size + 1, 0x10):
                with dpg.table_row():
                    dpg.add_text(f"{offset:0{digits}X}")  # Offset
                    chunk = file_bytes[offset:offset + 0x0F + 1]
                    for index in range(0x00, 0x0F + 1):
                        try:
                            dpg.add_text(f"{chunk[index]:02X}")
                            # FIXME: adding a tag is very slow!
                            # dpg.add_text(f"{chunk[index]:02X}", tag=f'byte_{offset+index}')
                        except IndexError:  # We may reach the end of the file earlier than the table width
                            dpg.add_text()
                    dotted_ascii = re.sub(r'[^\x32-\x7f]', '.', chunk.decode('ascii', errors='replace'))
                    dpg.add_text(dotted_ascii)

        # if DEBUG:
        #    dpg.add_text(f"{file_bytes!r}", wrap=80)

    with dpg.group(label='Decoded', tag='smf_decoded_contents', parent=parent):
        with dpg.tree_node(label=f"{midifile.filename}", default_open=True):

            dpg.add_tree_node(label=f"Size: {file_size} bytes", leaf=True)

            with dpg.tree_node(label="Header", default_open=True, selectable=True):
                smf_format = midiexplorer.midi.constants.SMF_HEADER_FORMATS[midifile.type]
                dpg.add_tree_node(label=f"Format: {midifile.type} ({smf_format})", leaf=True, selectable=True)
                dpg.add_tree_node(label=f"Number of tracks: {len(midifile.tracks)}", leaf=True, selectable=True)
                # FIXME: Upstream: mido. Support SMPTE division format.
                dpg.add_tree_node(label=f"Division: {midifile.ticks_per_beat} ticks per quarter-note",
                                  leaf=True, selectable=True)

            for i, track in enumerate(midifile.tracks):
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


def clear():
    dpg.delete_item('smf_contents', children_only=True)


def init():
    clear()
    dpg.disable_item('smf_close')
    dpg.add_button(label="Open", callback=smf.open_file, parent='smf_contents')


def selection():
    # FIXME: highlight file portions when selecting in decoded view
    theme = '__force_act'
    for index in range(0, 1):
        dpg.bind_item_theme(f'byte_{index})', theme)
    raise NotImplementedError
