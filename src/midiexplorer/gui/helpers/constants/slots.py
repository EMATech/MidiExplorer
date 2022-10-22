# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
DearPyGui Slot types.
"""
from enum import IntEnum


class Slots(IntEnum):
    SPECIAL = 0
    MOST = 1
    DRAW = 2
    DRAG_PAYLOAD = 3
