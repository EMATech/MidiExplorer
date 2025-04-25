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
from pathlib import Path

from dearpygui import dearpygui as dpg

from midiexplorer.__config__ import INIT_FILENAME


def _do_load(_, app_data) -> None:
    """Loads a configuration from selected file.

    :param _: Sender is ignored
    :param app_data: Selected file metadata

    """
    # FIXME: Does not work after creating the viewport!
    dpg.configure_app(load_init_file=app_data['file_path_name'])


def _do_save_as(_, app_data) -> None:
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
            tag='conf_load',
            label="Load configuration",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            default_filename=Path(INIT_FILENAME).stem,
            callback=_do_load,
            file_count=100,
    ):
        dpg.add_file_extension('.ini')

    with dpg.file_dialog(
            tag='conf_saveas',
            label="Save configuration as",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            default_filename=Path(INIT_FILENAME).stem,
            callback=_do_save_as,
    ):
        dpg.add_file_extension('.ini')


def load_file() -> None:
    """Shows the configuration file selector for loading.

    """
    dpg.show_item('conf_load')


def save_file() -> None:
    """Saves the current configuration to the default file.

    """
    dpg.save_init_file(INIT_FILENAME)


def save_file_as() -> None:
    """Shows the configuration file selector for saving as.

    """
    dpg.show_item('conf_saveas')
