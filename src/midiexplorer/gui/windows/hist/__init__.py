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
from midiexplorer.gui.windows.hist.data import clear_hist_data_table


def _add_table_columns():
    dpg.add_table_column(label="Timestamp (s)")
    dpg.add_table_column(label="Delta (ms)")
    dpg.add_table_column(label="Source")
    dpg.add_table_column(label="Destination")
    dpg.add_table_column(label="Raw Message (HEX)")
    if DEBUG:
        dpg.add_table_column(label="Decoded\nMessage")
    dpg.add_table_column(label="Status")
    dpg.add_table_column(label="Channel")
    dpg.add_table_column(label="Data 1")
    dpg.add_table_column(label="Data 2")
    dpg.add_table_column(label="Select", width_fixed=True, width=0, no_header_width=True, no_header_label=True)


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
            label="History",
            tag='hist_win',
            width=900,
            height=hist_win_height,
            no_close=True,
            collapsed=False,
            pos=[0, hist_win_y]
    ):
        # -------------------
        # History data table
        # -------------------

        # Buttons
        with dpg.group(parent='hist_win', horizontal=True):
            dpg.add_text("Order:")
            dpg.add_radio_button(items=("Reversed", "Auto-Scroll"), label="Mode", tag='hist_data_table_mode',
                                 default_value="Reversed", horizontal=True)
            dpg.add_checkbox(label="Selection to Generator", tag='hist_data_to_gen', default_value=True)
            dpg.add_button(label="Clear", callback=clear_hist_data_table)

        # TODO: Allow sorting
        # TODO: timegraph?

        # Content details
        with dpg.table(
                tag='hist_data_table',
                parent='hist_win',
                header_row=True,
                #clipper= True,
                policy=dpg.mvTable_SizingStretchProp,
                freeze_rows=1,
                # sort_multi=True,
                # sort_tristate=True, # TODO: implement
                resizable=True,
                reorderable=True,  # TODO: TableSetupColumn()?
                hideable=True,
                # sortable=True,  # TODO: TableGetSortSpecs()?
                context_menu_in_body=True,
                row_background=True,
                borders_innerV=True,
                scrollY=True,
        ):
            _add_table_columns()


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

    menu_item = 'menu_tools_history'
    if sender != menu_item:  # Update menu checkmark when coming from the shortcut handler
        dpg.set_value(menu_item, not dpg.get_value(menu_item))
