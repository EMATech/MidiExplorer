#
# SPDX-FileCopyrightText: 2022 Raphaël Doursenaud <rdoursenaud@free.fr>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Timestamp singleton.
"""
import time


class Timestamp:
    """Timestamp singleton.
    
    Allows sharing the latest timestamp globally.
    
    """
    __instance = None
    START_TIME = time.time()  # Initialize ASAP (seconds)
    value = 0  # Current timestamp (seconds)
    delta = 0  # Delta to previous timestamp (seconds)

    def __new__(cls) -> object:
        """Instantiates a new logger or retrieves the existing one.

        :return: A timestamp instance.

        """
        if Timestamp.__instance is None:
            Timestamp.__instance = super(Timestamp, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        now = time.time() - self.START_TIME
        self.delta = now - self.value
        self.value = now
