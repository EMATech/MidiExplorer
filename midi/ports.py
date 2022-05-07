# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from abc import ABC

import mido.ports


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


class MidiInPort(MidiPort):
    port: mido.ports.BaseInput
    pass


class MidiOutPort(MidiPort):
    port: mido.ports.BaseOutput
    pass
