# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Helper to convert mido status message types to standard midi numbers.
"""
import mido.messages


def get_status_by_type(msg_type: str) -> int:
    """Converts mido message type name to MIDI status number.

    :param msg_type: mido message type.
    :return: MIDI status number.

    """
    return mido.messages.SPEC_BY_TYPE[msg_type]['status_byte']
