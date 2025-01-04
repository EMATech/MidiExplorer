# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
GUI elements (DearPy GUI).
"""
import importlib.resources
import pathlib
from typing import Any, Optional

from dearpygui import dearpygui as dpg
from dearpygui_ext.logger import mvLogger

import midiexplorer.fonts
import midiexplorer.icons
import midiexplorer.midi
from midiexplorer.__config__ import DEBUG, INIT_FILENAME
from midiexplorer.gui.helpers import constants, logger, menu
from midiexplorer.gui.windows import conn, gen, hist, mon, smf
from midiexplorer.midi.timestamp import Timestamp
from midiexplorer.gui.helpers.callbacks.debugging import (
    enable as enable_dpg_cb_debugging
)

def init():
    """Initializes the GUI.

    """
    # ----------------
    # Logging system
    # Initialized ASAP
    # ----------------
    midiexplorer.gui.windows.log.create()
    logger: mvLogger = midiexplorer.gui.helpers.logger.Logger('log_win')
    if DEBUG:
        logger.log_level = midiexplorer.gui.helpers.logger.MvLogger.TRACE
    else:
        logger.log_level = midiexplorer.gui.helpers.logger.MvLogger.INFO
    logger.log_debug(f"Application started at {Timestamp.START_TIME}")

    # ----------------
    # MIDI I/O system
    # Initialized ASAP
    # ----------------
    try:
        midiexplorer.midi.init()
    except ValueError:
        # TODO: error popup?
        pass

    # -------
    # Windows
    # -------
    midiexplorer.gui.helpers.menu.create()
    midiexplorer.gui.windows.conn.create()
    midiexplorer.gui.windows.hist.create()
    midiexplorer.gui.windows.mon.create()
    midiexplorer.gui.windows.gen.create()
    midiexplorer.gui.windows.smf.create()

    # ---------------------
    # Initial configuration
    # ---------------------
    if not DEBUG:
        # FIXME: not stable
        if pathlib.Path(INIT_FILENAME).exists():
            dpg.configure_app(init_file=INIT_FILENAME)

    # ------------------
    # Keyboard shortcuts
    #
    # Don't forget to update menus!
    # ------------------
    with dpg.handler_registry():
        # F1: connections
        dpg.add_key_press_handler(key=dpg.mvKey_F1, callback=midiexplorer.gui.windows.conn.toggle)
        # F2: history
        dpg.add_key_press_handler(key=dpg.mvKey_F2, callback=midiexplorer.gui.windows.hist.toggle)
        # F3: monitor
        dpg.add_key_press_handler(key=dpg.mvKey_F3, callback=midiexplorer.gui.windows.mon.toggle)
        # F4: generator
        dpg.add_key_press_handler(key=dpg.mvKey_F4, callback=midiexplorer.gui.windows.gen.toggle)
        # F5: SMF
        dpg.add_key_press_handler(key=dpg.mvKey_F5, callback=midiexplorer.gui.windows.smf.toggle)
        # Fullscreen on F11
        dpg.add_key_press_handler(key=dpg.mvKey_F11, callback=midiexplorer.gui.toggle_fullscreen)
        # Log on F12
        dpg.add_key_press_handler(key=dpg.mvKey_F12, callback=midiexplorer.gui.windows.log.toggle)

    # -----
    # Theme
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/themes.html
    # TODO: Custom theme?

    # -----
    # Icons
    # -----
    # Icons must be set before showing viewport (Can also be set when instantiating the viewport)
    icons_root = importlib.resources.files(midiexplorer.icons)
    logger.log(f"Icons root: {icons_root}")
    small_icon = str(icons_root.joinpath('midiexplorer.ico'))
    large_icon = str(icons_root.joinpath('midiexplorer.ico'))

    # -----
    # Fonts
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
    fonts_root = importlib.resources.files(midiexplorer.fonts)
    logger.log(f"Fonts root: {fonts_root}")
    with dpg.font_registry():
        dpg.add_font(str(fonts_root.joinpath('Roboto-Regular.ttf')), 14, tag='default_font')
        dpg.add_font(str(fonts_root.joinpath('RobotoMono-Regular.ttf')), 14, tag='mono_font')

    dpg.bind_font('default_font')

    log_win_textbox = dpg.get_item_children('log_win', slot=midiexplorer.gui.helpers.constants.slots.Slots.MOST)[2]
    dpg.bind_item_font(log_win_textbox, 'mono_font')

    dpg.bind_item_font('hist_data_table_headers', 'mono_font')
    dpg.bind_item_font('hist_data_table', 'mono_font')

    if DEBUG:
        dpg.bind_item_font('mon_midi_mode', 'mono_font')
    dpg.bind_item_font('mon_status_container', 'mono_font')
    dpg.bind_item_font('mon_notes_container', 'mono_font')
    dpg.bind_item_font('mon_controllers_container', 'mono_font')
    dpg.bind_item_font('mon_program_container', 'mono_font')
    dpg.bind_item_font('mon_sysex_container', 'mono_font')

    dpg.bind_item_font('generator_container', 'mono_font')

    if DEBUG:
        dpg.bind_item_font('smf_container', 'mono_font')

    # --------
    # Viewport
    # --------
    # FIXME: compute dynamically?
    vp_width = 1920
    vp_height = 1080
    dpg.create_viewport(
        title=midiexplorer.APPLICATION_NAME,
        width=vp_width,
        height=vp_height,
        small_icon=small_icon,
        large_icon=large_icon
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()


def toggle_fullscreen(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
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

    dpg.toggle_viewport_fullscreen()

    menu_item = 'menu_display_fullscreen'
    if sender != menu_item:  # Update menu checkmark when coming from the shortcut handler
        dpg.set_value(menu_item, not dpg.get_value(menu_item))
