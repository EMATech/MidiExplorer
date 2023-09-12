# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Main menu.
"""

from dearpygui import dearpygui as dpg
from dearpygui.demo import show_demo

import midiexplorer.gui.helpers.config
import midiexplorer.gui.helpers.logger
import midiexplorer.gui.windows.about
import midiexplorer.gui.windows.log
from midiexplorer.__config__ import DEBUG


def create() -> None:
    """Creates the main application menu.

    Including the menu bar, associated items and file selector dialogs.

    """
    midiexplorer.gui.helpers.config.create_selectors()
    midiexplorer.gui.windows.about.create()

    with dpg.viewport_menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Exit", callback=dpg.stop_dearpygui)

        if DEBUG:  # FIXME: Currently unstable
            with dpg.menu(label="Configuration"):
                dpg.add_menu_item(label="Load", callback=midiexplorer.gui.helpers.config.load_file)
                dpg.add_menu_item(label="Save", callback=midiexplorer.gui.helpers.config.save_file)
                dpg.add_menu_item(label="Save as", callback=midiexplorer.gui.helpers.config.save_file_as)
                dpg.add_menu_item(label="Reset", callback=midiexplorer.gui.helpers.config.clear)

        with dpg.menu(label="Tools"):
            dpg.add_menu_item(label="Connections",
                              shortcut="F1",
                              check=True,
                              default_value=True,
                              callback=midiexplorer.gui.windows.conn.toggle)
            dpg.add_menu_item(label="History",
                              shortcut="F2",
                              check=True,
                              default_value=True,
                              callback=midiexplorer.gui.windows.hist.toggle)
            dpg.add_menu_item(label="Monitor",
                              shortcut="F3",
                              check=True,
                              default_value=True,
                              callback=midiexplorer.gui.windows.mon.toggle)
            dpg.add_menu_item(label="Generator",
                              shortcut="F4",
                              check=True,
                              default_value=True,
                              callback=midiexplorer.gui.windows.gen.toggle)
            dpg.add_menu_item(
                label="Standard MIDI File",
                shortcut="F5",
                check=True,
                default_value=True,
                callback=midiexplorer.gui.windows.smf.toggle
                )
            dpg.add_menu_item(label="Log",
                              shortcut="F12",
                              check=True,
                              default_value=DEBUG,
                              callback=midiexplorer.gui.windows.log.toggle)

        with dpg.menu(label="Display"):
            dpg.add_menu_item(label="Toggle Fullscreen",
                              shortcut="F11",
                              check=True,
                              default_value=False,
                              callback=dpg.toggle_viewport_fullscreen)

        with dpg.menu(label="Help"):
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
                    dpg.add_menu_item(label="Show ImGui Demo", callback=dpg.show_imgui_demo)
                    dpg.add_menu_item(label="Show ImPlot Demo", callback=dpg.show_implot_demo)
                    dpg.add_menu_item(label="Show Dear PyGui Demo", callback=show_demo)
            dpg.add_menu_item(label="About", callback=midiexplorer.gui.windows.about.toggle)
            # TODO: Add documentation
