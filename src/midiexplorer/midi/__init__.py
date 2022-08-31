# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
MIDI helpers.
"""

import mido  # https://mido.readthedocs.io/en/latest/

from midiexplorer.gui.logger import Logger


def init() -> None:
    """Initializes MIDO with the RtMidi backend.

    This doesn't open any input or output at this stage.

    """
    logger = Logger()

    # RtMidi is required for the features we need (callback and delta timestamps)
    mido.set_backend('mido.backends.rtmidi')

    # -------------------------
    # MIDO and backend versions
    # -------------------------
    logger.log_debug("Using MIDO:")
    logger.log_debug(f"\t - version: {mido.__version__}")
    logger.log_debug(f"\t - backend: {mido.backend.name}")

    # -------------------------
    # Native API used by RtMidi
    # -------------------------
    if mido.backend.name == 'mido.backends.rtmidi':
        api_names = mido.backend.module.get_api_names()
        api_names_count = len(api_names)
        if api_names_count == 0:
            logger.log_warning("No RtMidi API found!")
        elif api_names_count == 1:
            logger.log_debug(f"\t - RtMidi API: {api_names[0]}")
        else:
            logger.log_debug("\t - RtMidi APIs:")
            for name in api_names:
                logger.log_debug(f"\t\t - {name}")
    else:
        err_msg = "Wrong MIDI backend or no backend loaded!"
        logger.log_warning(err_msg)
        raise ValueError(err_msg)
