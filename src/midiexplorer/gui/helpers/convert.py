# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Data conversions.
"""
from dearpygui import dearpygui as dpg


def add_string_value_preconv(tag: str) -> None:
    """Add string value with pre-converted values.

    :param tag: String value tag name
    """
    dpg.add_string_value(tag=tag)
    if tag == 'syx_payload':
        dpg.add_string_value(tag=f'{tag}_char')
    dpg.add_string_value(tag=f'{tag}_hex')
    dpg.add_string_value(tag=f'{tag}_bin')
    dpg.add_string_value(tag=f'{tag}_dec')


def convert_to(unit: chr, values: int | tuple[int] | list[int], length, padding) -> str:
    """Converts a single integer or a group to a text representation in the specified unit.

    :param unit: Unit to convert to (Format specification type)
    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in unit format
    """
    unit_name = "Unknown"
    if unit == 'X':
        unit_name = "Hexadecimal"
    if unit == 'd':
        unit_name = "Decimal"
    if unit == 'b':
        unit_name = "Binary"
    if unit == 'c':
        unit_name = "Character"
    unit_name_padding = 12 - len(unit_name)

    converted_values = ""
    if values is not None:
        if isinstance(values, int):
            converted_values += f"{' ':{padding}}{values:0{length}{unit}}"
        else:
            for value in values:
                converted_values += f"{' ':{padding}}{value:0{length}{unit}}"
    return f"{unit_name}:{' ':{unit_name_padding}}{converted_values.rstrip()}"


def conv2hex(values: int | tuple[int] | list[int], length: int = 2, padding: int = 7) -> str:
    """Converts a group of integers or a single integer to its hexadecimal text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in hexadecimal format
    """
    return convert_to('X', values, length, padding)


def conv2dec(values: int | tuple[int] | list[int], length: int = 3, padding: int = 6) -> str:
    """Converts a group of integers or a single integer to its decimal text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in decimal format
    """
    return convert_to('d', values, length, padding)


def conv2bin(values: int | tuple[int] | list[int], length: int = 8, padding: int = 1) -> str:
    """Converts a group of integers or a single integer to its binary text representation.

    :param values: Value(s) to convert
    :param length: Conversion length
    :param padding: Prefixed padding length
    :return: Text representation of value(s) in binary format
    """
    return convert_to('b', values, length, padding)


def conv2char(values: int | tuple[int] | list[int]) -> str:
    """Converts a group of integers or a single integer to its ASCII text representation.

    :param values: Value(s) to convert
    :return: Text representation of value(s) in ASCII format
    """
    return convert_to('c', values, 1, 8)


def set_value_preconv(source: str, value: int | tuple[int] | list[int]) -> None:
    """Set value and pre-converted values.

    :param source: Value source tag name
    :param value: Value to set
    """
    dpg.set_value(source, str(value))
    if source == 'syx_payload':
        dpg.set_value(f'{source}_char', conv2char(value))
    dpg.set_value(f'{source}_hex', conv2hex(value))
    dpg.set_value(f'{source}_bin', conv2bin(value))
    dpg.set_value(f'{source}_dec', conv2dec(value))


def tooltip_conv(title: str, values: int | tuple[int] | list[int] | None = None,
                 hlen: int = 2, dlen: int = 3, blen: int = 8) -> None:
    """Adds a tooltip with data converted to hexadecimal, decimal and binary.

    :param title: Tooltip title.
    :param values: Tooltip value(s)
    :param hlen: Hexadecimal length
    :param dlen: Decimal length
    :param blen: Binary length

    """
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text(f"{title}")
        hconv = conv2hex(values, hlen, blen - hlen + 1)
        dconv = conv2dec(values, dlen, blen - dlen + 1)
        bconv = conv2bin(values, blen)
        if values is not None:
            dpg.add_text()
            dpg.add_text(f"{hconv}")
            dpg.add_text(f"{dconv}")
            dpg.add_text(f"{bconv}")


def tooltip_preconv(static_title: str | None = None, title_value_source: str | None = None,
                    values_source: str | None = None) -> None:
    """Adds a tooltip with pre-converted data.

    :param static_title: Tooltip static title.
    :param title_value_source: Tooltip title text value source.
    :param values_source: Tooltip value(s) source tag name
    """
    with dpg.tooltip(dpg.last_item()):
        if static_title:
            dpg.add_text(static_title)
        if title_value_source:
            dpg.add_text(source=title_value_source)
        dpg.add_text()
        if values_source == 'syx_payload':
            dpg.add_text(source=f'{values_source}_char')
        dpg.add_text(source=f'{values_source}_hex')
        dpg.add_text(source=f'{values_source}_dec')
        dpg.add_text(source=f'{values_source}_bin')
