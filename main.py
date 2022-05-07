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

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/

import gui.logger
import gui.windows.conn
import gui.windows.gen
import gui.windows.log
import gui.windows.main
import gui.windows.probe
import midi.input
from gui.config import DEBUG, INIT_FILENAME, START_TIME

if __name__ == '__main__':
    dpg.create_context()

    # Initialize logger ASAP
    log_win = gui.windows.log.create()
    logger = gui.logger.Logger(log_win)
    if DEBUG:
        logger.log_level = 0  # TRACE
    else:
        logger.log_level = 2  # INFO
    logger.log_debug(f"Application started at {START_TIME}")

    midi.init()

    if not DEBUG:
        dpg.configure_app(init_file=INIT_FILENAME)

    ###
    # DOAR PYGUI WINDOWS
    ###
    main_win = gui.windows.main.create()
    conn_win = gui.windows.conn.create()
    probe_win = gui.windows.probe.create()
    gen_win = gui.windows.gen.create()

    gui.windows.conn.refresh_midi_ports()

    with dpg.handler_registry():
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)  # Fullscreen on F11
        dpg.add_key_press_handler(key=123, callback=gui.windows.log.toggle)  # Log on F12

    ###
    # DEAR PYGUI SETUP
    ###
    dpg.create_viewport(title='MIDI Explorer', width=1920, height=1080)

    # Icons must be called before showing viewport
    # TODO: icons
    # dpg.set_viewport_small_icon("path/to/icon.ico")
    # dpg.set_viewport_large_icon("path/to/icon.ico")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window(main_win, True)

    ###
    # MAIN LOOP
    ###
    while dpg.is_dearpygui_running():  # Replaces dpg.start_dearpygui()
        if dpg.get_value('input_mode') == 'Polling':
            with midi.input.lock:
                gui.windows.conn.poll_processing()

        while not midi.input.queue.empty():
            gui.windows.conn.handle_received_data(*midi.input.queue.get())

        gui.windows.probe.update_blink_status()

        dpg.render_dearpygui_frame()

    dpg.destroy_context()
