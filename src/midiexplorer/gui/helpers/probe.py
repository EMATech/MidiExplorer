# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import mido

import midiexplorer.gui.windows.hist.data
import midiexplorer.gui.windows.mon.data
from midiexplorer.gui.helpers.logger import Logger
from midiexplorer.midi.timestamp import Timestamp


def add(timestamp: Timestamp, source: str, data: mido.Message) -> None:
    """Decodes and presents data received from the probe.

    :param timestamp: System timestamp
    :param source: Input name
    :param data: MIDI data

    """
    logger = Logger()

    logger.log_debug(f"Adding data from {source} to probe at {timestamp}: {data!r}")

    midiexplorer.gui.windows.mon.data.update_gui_monitor(data)
