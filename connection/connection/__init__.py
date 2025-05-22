# sourcery skip: use-contextlib-suppress
# pyright: reportMissingImports=false
"""Connection package __init__.

This MicroPython package `__init__` is used to import optional
extensions for the `connection` package:

- `connection-wlan` (WIP)
- `connection-mqtt` (TODO)
- `connection-server` (TODO)

This package uses static typing, which is enabled by the package dependencies.
On installation, the cross-compiled `typing.mpy` & `typing_extensions.mpy`
files are downloaded to the device `lib` folder.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

# optional dependencies
try:
    from .wlan import *
except ImportError:
    pass


class CertificateNotFound(Exception):
    """SSL context certificate not found."""

    pass
