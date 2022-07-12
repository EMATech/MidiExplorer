# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Configuration management
"""
import os.path

import time
from dearpygui import dearpygui as dpg

START_TIME = time.time()  # Initialize ASAP
INIT_FILENAME = "midiexplorer.ini"
DEBUG = False  # TODO: allow changing with CLI parameter to the main app


def create_selectors():
    with dpg.file_dialog(
            tag='load',
            label="Load configuration",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            default_filename=INIT_FILENAME,
            callback=_doload,
            file_count=100,
    ):
        dpg.add_file_extension('.ini')

    with dpg.file_dialog(
            tag='saveas',
            label="Save configuration as",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            default_filename=INIT_FILENAME,
            callback=_dosaveas,
    ):
        dpg.add_file_extension('.ini')


def load():
    dpg.show_item('load')


def _doload(_, app_data) -> None:
    # FIXME: Does not work after creating the viewport!
    dpg.configure_app(init_file=app_data['file_path_name'], load_init_file=True)


def save() -> None:
    dpg.save_init_file(INIT_FILENAME)


def saveas() -> None:
    dpg.show_item('saveas')


def _dosaveas(_, app_data):
    dpg.save_init_file(app_data['file_path_name'])


def clear() -> None:
    if os.path.exists(INIT_FILENAME):
        os.remove(INIT_FILENAME)
