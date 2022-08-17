# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI Explorer main program.
"""

import os.path

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/

import constants.dpg_mvlogger
import gui.logger
import gui.windows.about
import gui.windows.conn
import gui.windows.gen
import gui.windows.log
import gui.windows.main
import gui.windows.probe
import midi
from gui.config import DEBUG, INIT_FILENAME, START_TIME
from midi.ports import midi_in_queue

if __name__ == '__main__':
    dpg.create_context()

    # ----------------
    # Logging system
    # Initialized ASAP
    # ----------------
    gui.windows.log.create()
    logger = gui.logger.Logger('log_win')
    if DEBUG:
        logger.log_level = constants.dpg_mvlogger.TRACE
    else:
        logger.log_level = constants.dpg_mvlogger.INFO
    logger.log_debug(f"Application started at {START_TIME}")

    # ----------------
    # MIDI I/O system
    # Initialized ASAP
    # ----------------
    try:
        midi.init()
    except ValueError:
        # TODO: error popup?
        pass

    # -------
    # Windows
    # -------
    gui.windows.about.create()
    gui.windows.main.create()
    gui.windows.conn.create()
    gui.windows.probe.create()
    if DEBUG:
        gui.windows.gen.create()

    # ---------------------
    # Initial configuration
    # ---------------------
    if not DEBUG:
        # FIXME: not stable
        if os.path.exists(INIT_FILENAME):
            dpg.configure_app(init_file=INIT_FILENAME)

    # ------------------
    # Keyboard shortcuts
    # ------------------
    with dpg.handler_registry():
        # FIXME: this doesn't seem to work in Mac OS X and Linux. Report upstream?
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=gui.windows.log.toggle)  # Log on F12

    # -----
    # Theme
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/themes.html
    # TODO: Custom theme?

    # -----
    # Icons
    # -----
    # Icons must be set before showing viewport (Can also be set when instantiating the viewport)
    small_icon = 'icons/midiexplorer.ico'
    large_icon = 'icons/midiexplorer.ico'

    # -----
    # Fonts
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
    with dpg.font_registry():
        dpg.add_font('fonts/Roboto-Regular.ttf', 14, tag='default_font')
        dpg.add_font('fonts/RobotoMono-Regular.ttf', 14, tag='mono_font')

    dpg.bind_font('default_font')

    log_win_textbox = dpg.get_item_children('log_win', slot=1)[2]
    dpg.bind_item_font(log_win_textbox, 'mono_font')

    if DEBUG:
        dpg.bind_item_font('probe_midi_mode', 'mono_font')
    dpg.bind_item_font('probe_status_container', 'mono_font')
    dpg.bind_item_font('probe_controllers_container', 'mono_font')
    dpg.bind_item_font('probe_sysex_container', 'mono_font')
    dpg.bind_item_font('probe_notes_container', 'mono_font')

    dpg.bind_item_font('probe_data_table_headers', 'mono_font')
    dpg.bind_item_font('probe_data_table', 'mono_font')

    # --------
    # Viewport
    # --------
    # FIXME: compute dynamically?
    vp_width = 1920
    vp_height = 1080
    dpg.create_viewport(
        title='MIDI Explorer',
        width=vp_width,
        height=vp_height,
        small_icon=small_icon,
        large_icon=large_icon
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()
    merge_primary_window = True
    dpg.set_primary_window('main_win', merge_primary_window)

    # ---------
    # MAIN LOOP
    # ---------
    while dpg.is_dearpygui_running():  # Replaces dpg.start_dearpygui()
        # TODO: Use a generic event handler with subscribe pattern instead?

        # Retrieve MIDI inputs data if not using a callback
        if dpg.get_value('input_mode') == 'Polling':
            gui.windows.conn.poll_processing()

        # Process MIDI inputs data
        while not midi_in_queue.empty():
            gui.windows.conn.handle_received_data(*midi_in_queue.get())

        # Update probe visual cues
        gui.windows.probe.update_mon_blink_status()

        # Render DPG frame
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
