# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI Explorer main program.
"""

import pathlib

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/

import midiexplorer.gui.logger
import midiexplorer.gui.windows.about
import midiexplorer.gui.windows.conn
import midiexplorer.gui.windows.gen
import midiexplorer.gui.windows.log
import midiexplorer.gui.windows.main
import midiexplorer.gui.windows.probe
import midiexplorer.gui.windows.probe.blink
import midiexplorer.midi
from midiexplorer.dpg_helpers.constants.mvlogger import TRACE, INFO
from midiexplorer.gui.config import DEBUG, INIT_FILENAME, START_TIME
from midiexplorer.midi.ports import midi_in_queue


def init() -> None:
    """Initializes the GUI.

    """
    # ----------------
    # Logging system
    # Initialized ASAP
    # ----------------
    midiexplorer.gui.windows.log.create()
    logger = midiexplorer.gui.logger.Logger('log_win')
    if DEBUG:
        logger.log_level = TRACE
    else:
        logger.log_level = INFO
    logger.log_debug(f"Application started at {START_TIME}")

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
    midiexplorer.gui.windows.about.create()
    midiexplorer.gui.windows.main.create()
    midiexplorer.gui.windows.conn.create()
    midiexplorer.gui.windows.probe.create()
    if DEBUG:
        midiexplorer.gui.windows.gen.create()

    # ---------------------
    # Initial configuration
    # ---------------------
    if not DEBUG:
        # FIXME: not stable
        if pathlib.Path(INIT_FILENAME).exists():
            dpg.configure_app(init_file=INIT_FILENAME)

    # ------------------
    # Keyboard shortcuts
    # ------------------
    with dpg.handler_registry():
        # FIXME: this doesn't seem to work in Mac OS X and Linux. Report upstream?
        # Fullscreen on F11
        dpg.add_key_press_handler(key=122, callback=dpg.toggle_viewport_fullscreen)
        # Log on F12
        dpg.add_key_press_handler(key=123, callback=midiexplorer.gui.windows.log.toggle)

    # -----
    # Theme
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/themes.html
    # TODO: Custom theme?

    # -----
    # Icons
    # -----
    # Icons must be set before showing viewport (Can also be set when instantiating the viewport)
    module_root = pathlib.Path(midiexplorer.__file__).parent
    small_icon = f'{module_root}/icons/midiexplorer.ico'
    large_icon = f'{module_root}icons/midiexplorer.ico'

    # -----
    # Fonts
    # -----
    # https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
    with dpg.font_registry():
        dpg.add_font(f'{module_root}/fonts/Roboto-Regular.ttf', 14, tag='default_font')
        dpg.add_font(f'{module_root}/fonts/RobotoMono-Regular.ttf', 14, tag='mono_font')

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


def main() -> None:
    """Entry point and main loop.

    """
    dpg.create_context()

    init()

    # ---------
    # MAIN LOOP
    # ---------
    while dpg.is_dearpygui_running():  # Replaces dpg.start_dearpygui()
        # TODO: Use a generic event handler with subscribe pattern instead?

        # Retrieve MIDI inputs data if not using a callback
        if dpg.get_value('input_mode') == 'Polling':
            midiexplorer.gui.windows.conn.poll_processing()

        # Process MIDI inputs data
        while not midi_in_queue.empty():
            midiexplorer.gui.windows.conn.handle_received_data(*midi_in_queue.get())

        # Update probe visual cues
        midiexplorer.gui.windows.probe.blink.update_mon_status()

        # Render DPG frame
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == '__main__':
    main()
