# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI ports helpers
"""

import multiprocessing
import platform
import threading
from abc import ABC

import time

import mido

lock = threading.Lock()
queue = multiprocessing.SimpleQueue()


class MidiPort(ABC):
    """
    Abstract Base Class for MIDI ports management around Mido.

    FIXME: is this cross-platform compatible?
    """
    port: mido.ports.BasePort

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

    @property
    def num(self):
        if platform.system() == "Windows" or platform.system() == "Linux":
            return self.name.split()[-1]

    @property
    def label(self):
        if platform.system() == "Windows":
            return self.name[0:-len(self.num) - 1]
        elif platform.system() == "Linux":
            return self.name[self.name.index(':') + 1:-len(self.num) - 1]
        else:
            return self.name

    def close(self):
        self.port.close()


class MidiOutPort(MidiPort):
    """
    Manages output ports.

    A thin wrapper around Mido.
    """
    port: mido.ports.BaseOutput

    def open(self):
        self.port = mido.open_output(self.name)


class MidiInPort(MidiPort):
    """
    Manages output ports.
    A thin wrapper around Mido.
    """
    port: mido.ports.BaseInput
    dest: None | MidiOutPort | str = None  # We can only open the port once. Therefore, only one destination exists.

    @property
    def mode(self):
        """
        Gives the mode in which the port operates.
        Either:
          - callback
          - polling

        :return: str
        """
        if self.port.callback is not None:
            mode = 'callback'
        else:
            mode = 'polling'
        return mode

    def open(self, dest):
        """
        Opens the port to the given destination.

        :param dest: destination
        """
        self.dest = dest
        self.port = mido.open_input(self.name)

    def close(self):
        """
        Closes the port.
        """
        self.port.callback = None
        self.dest = None
        super().close()

    def callback(self):
        """
        Sets the port in callback mode.

        This is the recommended mode for the best performance.
        """
        with lock:
            self.port.callback = self.receive_callback

    def polling(self):
        """
        Sets the port in polling mode.

        Not recommended except when the need to debug arises.
        """
        self.port.callback = None

    def receive_callback(self, midi_message: mido.Message) -> None:
        """
        Processes the messages received in callback mode.
        """
        # Get the system timestamp ASAP
        timestamp = time.time()

        from gui.logger import Logger
        logger = Logger()
        logger.log_debug(f"Callback data: {midi_message} from {self.label} to {self.dest}")

        with lock:
            queue.put((timestamp, self.label, self.dest, midi_message))
