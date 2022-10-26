# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Standard MIDI File (SMF) menus callbacks.
"""

from dearpygui import dearpygui as dpg
from mido import MidiFile

import midiexplorer.gui.windows.smf
from midiexplorer.__config__ import DEBUG


def _do_load(_, app_data) -> None:
    """Loads an SMF from selected file.

    :param _: Sender is ignored
    :param app_data: Selected file metadata

    """
    # TODO: sanity checks?

    # Logger().log_debug(f"{app_data!r}")
    filename = app_data['file_path_name']

    # Raw file
    with open(filename, 'rb') as file:
        contents = file.read()
    # Logger().log_debug(f"{contents!r}")

    # Decoded file
    mid = MidiFile(filename, clip=True, debug=DEBUG,
                   # charset='ascii',
                   )
    # Logger().log_debug(f"{mid!r}")

    midiexplorer.gui.windows.smf.populate(contents, mid)


def _do_save_as(_, app_data) -> None:
    """Saves the current SMF to the selected file.

    :param _: Sender is ignored
    :param app_data: Selected file metadata

    """
    raise NotImplementedError


def _set_supported_extensions() -> None:
    """Sets the supported extensions to the file dialog.
    """
    dpg.add_file_extension('.mid')
    dpg.add_file_extension('.midi')
    dpg.add_file_extension('.smf')
    if DEBUG:  # TODO: Implement these formats!
        dpg.add_file_extension('.rmid')
        dpg.add_file_extension('.xmf')
        dpg.add_file_extension('.syx')
        dpg.add_file_extension('.kar')


def create_selectors() -> None:
    """Creates SMF selector dialogs.

    """
    with dpg.file_dialog(
            tag='smf_open',
            label="Open SMF",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            callback=_do_load,
            file_count=100,
    ):
        _set_supported_extensions()

    with dpg.file_dialog(
            tag='smf_saveas',
            label="Save SMF as",
            min_size=(640, 480),
            show=False,
            modal=True,
            directory_selector=False,
            callback=_do_save_as,
    ):
        _set_supported_extensions()


def open_file() -> None:
    """Shows the SMF selector for loading.

    """
    dpg.show_item('smf_open')


def save_file() -> None:
    """Saves to the currently open SMF.

    """
    raise NotImplementedError


def save_file_as() -> None:
    """Shows the SMF selector for saving as.

    """
    dpg.show_item('smf_saveas')


def close_file() -> None:
    """Closes the current SMF.

    """
    midiexplorer.gui.windows.smf.init()
