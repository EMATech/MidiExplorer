# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
History window and management.
"""
from typing import Any, Optional

from dearpygui import dearpygui as dpg

from midiexplorer.__config__ import DEBUG
from midiexplorer.gui.helpers.callbacks.debugging import enable as enable_dpg_cb_debugging
from midiexplorer.gui.windows.hist.data import init_details_table_data, clear_hist_data_table


def _add_table_columns():
    dpg.add_table_column(label="Source")
    dpg.add_table_column(label="Destination")
    dpg.add_table_column(label="Timestamp (s)")
    dpg.add_table_column(label="Delta (ms)")
    dpg.add_table_column(label="Raw Message (HEX)")
    if DEBUG:
        dpg.add_table_column(label="Decoded Message")
    dpg.add_table_column(label="Status")
    dpg.add_table_column(label="Channel")
    dpg.add_table_column(label="Data 1")
    dpg.add_table_column(label="Data 2")


def create() -> None:
    """Creates the history window.

    """
    # -------------------------
    # History window size
    # --------------------------
    # TODO: compute dynamically?
    hist_win_height = 510
    hist_win_y = 530
    if DEBUG:
        hist_win_height = 395
        hist_win_y = 530 - 110

    # --------------------
    # History window
    # --------------------
    with dpg.window(
            tag='hist_win',
            label="History",
            width=900,
            height=hist_win_height,
            no_close=True,
            collapsed=False,
            pos=[0, hist_win_y]
    ):
        # -------------------
        # History data table
        # -------------------
        dpg.add_child_window(tag='hist_table_container', height=470, border=False)

        # Separate headers
        # FIXME: workaround table scrolling not implemented upstream yet to have static headers
        # dpg.add_child_window(tag='hist_det_headers', label="Details headers", height=5, border=False)
        with dpg.table(parent='hist_table_container',
                       tag='hist_data_table_headers',
                       header_row=True,
                       freeze_rows=1,
                       policy=dpg.mvTable_SizingStretchSame):
            _add_table_columns()

        # TODO: Allow sorting
        # TODO: Show/hide columns
        # TODO: timegraph?

        # Content details
        dpg.add_child_window(parent='hist_table_container', tag='hist_det', label="Details", height=420, border=False)
        with dpg.table(parent='hist_det',
                       tag='hist_data_table',
                       header_row=False,  # FIXME: True when table scrolling will be implemented upstream
                       freeze_rows=0,  # FIXME: 1 when table scrolling will be implemented upstream
                       policy=dpg.mvTable_SizingStretchSame,
                       # scrollY=True,  # FIXME: Scroll the table instead of the window when available upstream
                       ):
            _add_table_columns()
            init_details_table_data()

        # Buttons
        # FIXME: separated to not scroll with table child window until table scrolling is supported
        dpg.add_child_window(parent='hist_table_container', tag='hist_btns', label="Buttons", border=False)
        with dpg.group(parent='hist_btns', horizontal=True):
            dpg.add_checkbox(tag='hist_data_table_autoscroll', label="Auto-Scroll", default_value=True)
            dpg.add_button(label="Clear", callback=clear_hist_data_table)


def toggle(sender: int | str, app_data: Any, user_data: Optional[Any]) -> None:
    """Callback to toggle the window visibility.

    :param sender: argument is used by DPG to inform the callback
                   which item triggered the callback by sending the tag
                   or 0 if trigger by the application.
    :param app_data: argument is used DPG to send information to the callback
                     i.e. the current value of most basic widgets.
    :param user_data: argument is Optionally used to pass your own python data into the function.

    """
    if DEBUG:
        enable_dpg_cb_debugging(sender, app_data, user_data)

    dpg.configure_item('hist_win', show=not dpg.is_item_visible('hist_win'))
