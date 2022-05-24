# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI helpers
"""

import mido  # https://mido.readthedocs.io/en/latest/

from gui.logger import Logger


def init() -> None:
    logger = Logger()

    mido.set_backend('mido.backends.rtmidi')

    logger.log_debug(f"Using MIDO:")
    logger.log_debug(f"\t - version: {mido.__version__}")
    logger.log_debug(f"\t - backend: {mido.backend.name}")
    if mido.backend.name == 'mido.backends.rtmidi':
        api_names = mido.backend.module.get_api_names()
        api_names_count = len(api_names)
        if api_names_count == 0:
            logger.log_warning("No RtMidi API found!")
        elif api_names_count == 1:
            logger.log_debug(f"\t - RtMidi API: {api_names[0]}")
        else:
            logger.log_debug(f"\t - RtMidi APIs:")
            for name in api_names:
                logger.log_debug(f"\t\t - {name}")
    else:
        logger.log_warning("Wrong MIDI backend or no backend loaded!")
