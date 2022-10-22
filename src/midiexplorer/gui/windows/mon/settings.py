# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Settings options.
"""

import midiexplorer.midi.notes

# TODO: add both?
eox_categories = (
    "System Common Message (default, MIDI specification compliant)",
    "System Exclusive Message"
)
notation_modes = {
    "English Alphabetical (default)": midiexplorer.midi.notes.MIDI_NOTES_ALPHA_EN,
    "Syllabic": midiexplorer.midi.notes.MIDI_NOTES_SYLLABIC,
    "German Alphabetic ": midiexplorer.midi.notes.MIDI_NOTES_ALPHA_DE,
}
