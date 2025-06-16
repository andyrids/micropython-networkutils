# pyright: reportMissingImports=false
"""An MQTT extension for the `networkutils` package.

NOTE: TODO.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

class CertificateNotFound(Exception):
    """SSL context certificate not found."""

    pass


def mqtt_dummy_function() -> None:
    pass