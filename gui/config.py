# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from dearpygui import dearpygui as dpg

START_TIME = time.time()  # Initialize ASAP
INIT_FILENAME = "midiexplorer.ini"
DEBUG = True  # TODO: allow changing with CLI parameter to the main appS


def save() -> None:
    dpg.save_init_file(INIT_FILENAME)
