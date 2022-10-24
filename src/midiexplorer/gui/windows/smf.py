# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Standard MIDI File (SMF) window and management.
"""
from dearpygui import dearpygui as dpg

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
    posx = 0
    posy = 0
    width = 800
    height = 600
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
                if DEBUG:  # TODO: Implement recorder first!
                    dpg.add_menu_item(label="Save", callback=smf.save_file, enabled=False)
                    dpg.add_menu_item(label="Save as", callback=smf.save_file_as, enabled=False)
                dpg.add_menu_item(label="Close", callback=smf.close_file, enabled=False)

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
        dpg.add_text(source='SMF')
