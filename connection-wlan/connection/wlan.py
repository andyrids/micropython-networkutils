# pyright: reportMissingImports=false
"""Connection package WLAN interface package.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Functions:
    debug_network_status: Print WLAN status message if verbose flag is True.

Exceptions:

"""

import network

from typing import Optional, Union
from .utils import debug_message

def debug_network_status(
        WLAN: network.WLAN,
        mode: int,
        verbose: bool
    ) -> None:
    """Print WLAN status message if verbose flag is True.

    Args:
        WLAN (network.WLAN): WLAN instance.
        mode (str): WLAN instance mode.
        verbose (bool): Message print flag.
    """
    WLAN_MODE_STR = ("STA", "AP")[mode]
    status = WLAN.status()
    active = WLAN.active()
    connected = WLAN.isconnected()

    message = f"""
    WLAN INFO
    ---------
    MODE: {WLAN_MODE_STR}
    STATUS: {status}
    ACTIVE: {active}
    CONNECTED: {connected}
    """

    debug_message(message, verbose)
