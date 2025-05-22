# sourcery skip: use-contextlib-suppress
# pyright: reportMissingImports=false
"""Connection package __init__ file.

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
