# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI Explorer main program.
"""

import dearpygui.dearpygui as dpg  # https://dearpygui.readthedocs.io/en/latest/

import midiexplorer.gui
from midiexplorer import APPLICATION_NAME
from midiexplorer.__config__ import INIT_FILENAME
from midiexplorer.gui.helpers.logger import Logger
from midiexplorer.midi.ports import midi_in_queue
from midiexplorer.midi.timestamp import Timestamp


def main() -> None:
    """Entry point and main loop.

    """
    Timestamp()  # Initializes start time ASAP
    # Use logger cache since we can’t instantiate the logger window yet
    Logger.log(f"Application started at {Timestamp().START_TIME}")

    dpg.create_context()
    Logger.log("DPG Context created")

    # TODO: determine which init file to load (Vendor or user)

    # ---------------------
    # Initial configuration
    #
    # Must be done before creating the viewport
    # ---------------------
    Logger.log(f"Configuring app using init file: {INIT_FILENAME}")
    dpg.configure_app(
        # FIXME: upstream documentation is misleading.
        load_init_file=INIT_FILENAME,  # Non-modifiable vendor init file
        docking=True,
        docking_space=True,
        docking_shift_only=False,
        #init_file=INIT_FILENAME,  # Init file modifiable by user
        auto_save_init_file=False,  # Saves window positions on close
        # FIXME: determine what these do!
        #        Upstream: document
        #device: int  # GPU selection
        #auto_device: bool  # GPU selection
        #allow_alias_overwrites: bool
        #manual_alias_management: bool
        #skip_keyword_args: bool
        #skip_positional_args: bool
        #skip_required_args: bool
        #wait_for_input=False,  # Only update on user input
        #manual_callback_management: bool
        #keyboard_navigation=False,  # Accessibility
        #anti_aliased_lines=True,
        #anti_aliased_lines_use_tex=True,
        #anti_aliased_fill=True,
    )

    midiexplorer.gui.init()

    # Normal logger is now initialized and available
    logger = Logger()
    logger.log(f"{APPLICATION_NAME} GUI initialized")

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

        # Update monitor visual cues
        midiexplorer.gui.windows.mon.blink.update_mon_status()

        # Render DPG frame
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == '__main__':
    main()
