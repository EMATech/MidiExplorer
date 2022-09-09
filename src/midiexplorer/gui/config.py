# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Configuration file management.
"""
# FIXME: store preferences/settings

import os.path
import time

from dearpygui import dearpygui as dpg

START_TIME = time.time()  # Initialize ASAP
INIT_FILENAME = "midiexplorer.ini"
DEBUG = True  # TODO: allow changing with CLI parameter to the main app


def _doload(_, app_data) -> None:
    """Loads a configuration from selected file.

    :param _: Sender is ignored
    :param app_data: Selected file metadata

    """
    # FIXME: Does not work after creating the viewport!
    dpg.configure_app(init_file=app_data['file_path_name'], load_init_file=True)


def _dosaveas(_, app_data) -> None:
    """Saves the current configuration in the selected file.

    :param _: Sender is ignored
    :param app_data: Selected file metadata

    """
    dpg.save_init_file(app_data['file_path_name'])


def clear() -> None:
    """Removes the default configuration.

    """
    if os.path.exists(INIT_FILENAME):
        os.remove(INIT_FILENAME)


def create_selectors() -> None:
    """Creates config file selector dialogs.

    """
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


def load() -> None:
    """Shows the configuration file selector for loading.

    """
    dpg.show_item('load')


def save() -> None:
    """Saves the current configuration to the default file.

    """
    dpg.save_init_file(INIT_FILENAME)


def saveas() -> None:
    """Shows the configuration file selector for saving as.

    """
    dpg.show_item('saveas')
