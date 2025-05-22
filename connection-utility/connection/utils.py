"""Connection package utils module.

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
    debug_message: Print debug message if verbose flag is True.

    debug_network_status: Print WLAN status message if verbose flag is True.
"""

def debug_message(message: str, verbose: bool) -> None:
    """Print debug message if verbose flag is True.

    Args:
        message (str): Message to print.

        verbose (bool): Message print flag.
    """
    # "{:^30}".format("CENTRED STRING")
    if not verbose:
        return
    print("\n".join([i.strip() for i in message.split("\n")]))