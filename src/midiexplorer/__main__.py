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
from midiexplorer.midi.ports import midi_in_queue
from midiexplorer.midi.timestamp import Timestamp


def main() -> None:
    """Entry point and main loop.

    """
    Timestamp()  # Initializes start time ASAP

    dpg.create_context()

    midiexplorer.gui.init()

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
