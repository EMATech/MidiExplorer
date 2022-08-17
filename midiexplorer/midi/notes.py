# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Helper to convert MIDI notes to various human-readable formats.
"""

NOTES_SYLLABIC = ["Do", "Do#", "Re", "Re#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
NOTES_ALPHA_EN = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_ALPHA_DE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"]

MIDI_NOTES_SYLLABIC = {}
MIDI_NOTES_ALPHA_EN = {}
MIDI_NOTES_ALPHA_DE = {}

for midi_note in range(128):
    note_index = int(midi_note % 12)
    octave = int(midi_note / 12) - 1
    MIDI_NOTES_SYLLABIC[midi_note] = f"{NOTES_SYLLABIC[note_index]}{octave}"
    MIDI_NOTES_ALPHA_EN[midi_note] = f"{NOTES_ALPHA_EN[note_index]}{octave}"
    MIDI_NOTES_ALPHA_DE[midi_note] = f"{NOTES_ALPHA_DE[note_index]}{octave}"
