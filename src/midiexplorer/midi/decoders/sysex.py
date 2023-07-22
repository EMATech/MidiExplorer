# This Python file uses the following encoding: utf-8
#
# SPDX-FileCopyrightText: 2021-2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
System Exclusive Decoders.
"""

# TODO: separate into dedicated subdecoders?

# TODO: decode sample dump standard (page 35)
# ACK, NAK, Wait, Cancel & EOF
# TODO: decode device inquiry (page 40)
# TODO: decode file dump (page 41)
# TODO: decode midi tuning (page 47)
# TODO: decode general midi system messages (page 52)
# TODO: decode MTC full message, user bits and real time cueing (page 53 + dedicated spec)
# TODO: decode midi show control (page 53 + dedicated spec)
# TODO: decode notation information (page 54)
# TODO: decode device control (page 57)
# TODO: decode MMC (page 58 + dedicated spec)

import functools

import midi_const
import mido


class DecodedSysExId:
    def __init__(self, value: int | tuple[int]):
        length: int
        try:
            length = len(value)
        except TypeError:
            # Integers don't have length
            length = 1
            pass
        if length not in (1, 3):
            raise ValueError(f"A system exclusive ID can only be 1-byte or 3-bytes long, not {length}-bytes!")
        self._len = length
        if isinstance(value, int):
            if value == 0:
                raise ValueError("3-bytes must be provided when the first is 0x00.")
        self._raw = value

    @property
    def length(self) -> int:
        return self._len

    @property
    def value(self) -> int | tuple[int]:
        return self._raw

    @functools.cached_property
    def group(self) -> str:
        index: int
        group: str
        if self._len == 1:
            index = self._raw
        else:
            index = self._raw[0]
        group = midi_const.SYSTEM_EXCLUSIVE_ID_GROUPS.get(index, "Undefined")
        return group

    @functools.cached_property
    def region(self) -> str:
        index: int
        region: str
        if self._len == 1:
            index = self._raw
        else:
            index = self._raw[1]
        region = midi_const.SYSTEM_EXCLUSIVE_ID_REGIONS.get(index, "N.A.")
        return region

    @functools.cached_property
    def name(self) -> str:
        name: str = "Undefined"
        if self._len == 1:
            name = midi_const.SYSTEM_EXCLUSIVE_ID.get(self._raw, "Undefined")
        else:
            name = midi_const.SYSTEM_EXCLUSIVE_ID.get(
                self._raw[0], {}
            ).get(
                self._raw[1], {}
            ).get(
                self._raw[2], name
            )
        return name


class DecodedSysExPayload:
    _id = int
    _raw: int | tuple[int]

    def __init__(self, identifier: DecodedSysExId, contents: int | tuple[int]):
        self._id = identifier
        self._raw = contents

    @property
    def value(self):
        return self._raw

    @staticmethod
    def get_decoder(identifier):
        if identifier.value == 0x7E:
            return DecodedUniversalNonRealTimeSysExPayload
        if identifier.value == 0x7F:
            return DecodedUniversalRealTimeSysExPayload
        return DecodedSysExPayload


class DecodedUniversalSysExPayload(DecodedSysExPayload):
    def __init__(self, identifier: DecodedSysExId, contents: int | tuple[int]):
        super().__init__(identifier, contents)


class DecodedUniversalNonRealTimeSysExPayload(DecodedUniversalSysExPayload):
    def __init__(self, identifier: DecodedSysExId, contents: int | tuple[int]):
        if identifier.value != 0x7E:
            raise ValueError
        super().__init__(identifier, contents)
        next_byte: int = 0
        self.sub_id1_value = self._raw[next_byte]
        self.sub_id1_name = midi_const. \
            DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_NON_REAL_TIME_SUB_ID_1.get(
            self.sub_id1_value, "Undefined"
            )
        if self.sub_id1_value in midi_const.NON_REAL_TIME_SUB_ID_2_FROM_1:
            next_byte += 1
            self.sub_id2_value = self._raw[next_byte]
            self.sub_id2_name = midi_const.NON_REAL_TIME_SUB_ID_2_FROM_1.get(
                self.sub_id1_value
                ).get(
                self.sub_id2_value, "Undefined"
            )


class DecodedUniversalRealTimeSysExPayload(DecodedUniversalSysExPayload):
    def __init__(self, identifier: DecodedSysExId, contents: int | tuple[int]):
        if identifier.value != 0x7F:
            raise ValueError
        super().__init__(identifier, contents)
        next_byte: int = 0
        self.sub_id1_value = self._raw[next_byte]
        self.sub_id1_name = midi_const. \
            DEFINED_UNIVERSAL_SYSTEM_EXCLUSIVE_MESSAGES_REAL_TIME_SUB_ID_1.get(
            self.sub_id1_value, "Undefined"
            )
        if self.sub_id1_value in midi_const.REAL_TIME_SUB_ID_2_FROM_1:
            next_byte += 1
            self.sub_id2_value = self._raw[next_byte]
            self.sub_id2_name = midi_const.REAL_TIME_SUB_ID_2_FROM_1.get(
                self.sub_id1_value
                ).get(
                self.sub_id2_value, "Undefined"
            )


class DecodedSysEx:
    def __init__(self, message: tuple):
        if len(message) < 3:
            raise ValueError("Message too short (less than 3 bytes) to be a proper system exclusive message.")
        # Scrub EOX if present
        if message[-1] == mido.messages.specs.SYSEX_END:
            self._raw = message[:-1]
        else:
            self._raw = message
        # Determine ID length
        if self._raw[0] == 0x00:
            # 3-byte ID
            if len(message) < 5:
                raise ValueError(
                    "Message too short (less than 5 bytes) to be a proper system exclusive message with a 3-byte ID."
                )
            self._device_id_byte = 3
            self.identifier = DecodedSysExId(self._raw[0:self._device_id_byte])
        else:
            # 1-byte ID
            self._device_id_byte = 1
            self.identifier = DecodedSysExId(self._raw[0])

    @functools.cached_property
    def device_id(self) -> int:
        return self._raw[self._device_id_byte]

    @functools.cached_property
    def _payload(self) -> int | tuple[int]:
        return self._raw[self._device_id_byte + 1:]

    @functools.cached_property
    def payload(self) -> DecodedSysExPayload:
        decoder = DecodedSysExPayload.get_decoder(self.identifier)
        return decoder(self.identifier, self._payload)
