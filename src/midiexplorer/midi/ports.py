# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI ports helpers.
"""

import multiprocessing
import platform
import threading
import time
from abc import ABC
from functools import cached_property

import mido

from midiexplorer.gui.logger import Logger

# TODO: MIDI Input Queue Singleton?
midi_in_lock = threading.Lock()
midi_in_queue = multiprocessing.SimpleQueue()


class MidiPort(ABC):
    """Abstract Base Class for MIDI ports management around Mido.

    """
    _system = platform.system()

    port: mido.ports.BasePort

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return self.name

    @cached_property
    def num(self) -> str:
        """Numerical ID of the port.

        Platform dependant:
        - Microsoft Windows (MME): single integer number
        - Linux (ALSA): "x:y" pair of integer numbers
        - Mac OS X (Core MIDI): seem to not have any ID exposed (at least by RtMidi)

        :return: The system port index.

        """
        if self._system in {'Windows', 'Linux'}:
            return self.name.split()[-1]
        return ''

    @cached_property
    def label(self) -> str:
        """Human-readable name of the port.

        Platform dependant:
        - Microsoft Windows (MME): requires removing the ID and preceding space from the string end
        - Linux (ALSA): requires removing the interface name and semicolon delimiter from the beginning of the string
          and the ID and preceding space from the string end
        - Mac OS X (Core MIDI): no processing since they don't seem to use any ID or strange formatting


        :return: The name of the port.
        """
        if self._system == 'Windows':
            return self.name[0:-len(self.num) - 1]
        if self._system == 'Linux':
            return self.name[self.name.index(':') + 1:-len(self.num) - 1]
        return self.name

    def close(self) -> None:
        """Closes the port.

        """
        self.port.close()


class MidiOutPort(MidiPort):
    """Manages output ports.

    A thin wrapper around Mido.

    """
    port: mido.ports.BaseOutput

    def open(self) -> None:
        """Opens the port.

        """
        self.port = mido.open_output(self.name)


class MidiInPort(MidiPort):
    """Manages output ports.

    A thin wrapper around Mido.

    """
    port: mido.ports.BaseInput
    dest: None | MidiOutPort | str = None  # We can only open the port once. Therefore, only one destination exists.

    @property
    def mode(self) -> None:
        """Gives the mode in which the port operates.

        :return: Either 'callback' or 'polling'.

        """
        if self.port.callback is not None:
            mode = 'callback'
        else:
            mode = 'polling'
        return mode

    def open(self, dest: MidiOutPort | str) -> None:
        """Opens the port to the given destination.

        :param dest: Destination port or module.

        """
        self.dest = dest
        self.port = mido.open_input(self.name)

    def close(self) -> None:
        """Closes the port.

        """
        self.port.callback = None
        self.dest = None
        super().close()

    def callback(self) -> None:
        """Sets the port in callback mode.

        This is the recommended mode for the best performance.

        """
        with midi_in_lock:
            self.port.callback = self.receive_callback

    def polling(self) -> None:
        """Sets the port in polling mode.

        Not recommended except when the need to debug arises.

        """
        self.port.callback = None

    def receive_callback(self, midi_message: mido.Message) -> None:
        """Processes the messages received in callback mode.

        :param midi_message: The received MIDI message.

        """
        # Get the system timestamp ASAP
        timestamp = time.time()

        logger = Logger()
        logger.log_debug(f"Callback data: {midi_message} from {self.label} to {self.dest}")

        with midi_in_lock:
            midi_in_queue.put((timestamp, self.label, self.dest, midi_message))
