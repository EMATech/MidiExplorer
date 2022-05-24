# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI ports helpers
"""

import multiprocessing
import threading
import time
from abc import ABC

import mido

lock = threading.Lock()
queue = multiprocessing.SimpleQueue()


class MidiPort(ABC):
    # FIXME: is this cross-platform compatible?
    port: mido.ports.BasePort

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

    @property
    def num(self):
        return self.name.split()[-1]

    @property
    def label(self):
        return self.name[0:-len(self.num) - 1]

    def close(self):
        self.port.close()


class MidiOutPort(MidiPort):
    port: mido.ports.BaseOutput

    def open(self):
        self.port = mido.open_output(self.name)


class MidiInPort(MidiPort):
    port: mido.ports.BaseInput
    dest: None | MidiOutPort | str = None

    def open(self, dest):
        self.dest = dest
        self.port = mido.open_input(self.name)

    def close(self):
        self.port.callback = None
        self.dest = None
        super().close()

    def callback(self):
        with lock:
            self.port.callback = self.receive_callback

    def polling(self):
        self.port.callback = None

    def receive_callback(self, midi_message: mido.Message) -> None:
        """
        MIDI data receive in "Callback" mode.

        Recommended.
        """
        # Get the timestamp ASAP
        timestamp = time.time()

        from gui.logger import Logger
        logger = Logger()

        logger.log_debug(f"Callback data: {midi_message} from {self.label} to {self.dest}")

        with lock:
            queue.put((timestamp, self.label, self.dest, midi_message))

    @property
    def mode(self):
        if self.port.callback is not None:
            mode = 'callback'
        else:
            mode = 'polling'
        return mode
