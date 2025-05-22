# pyright: reportUndefinedVariable=false
"""Connection package manifest file.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

# metadata for manifest file. Useful for micropython-lib packages.
metadata(description="", version="0.0.1")

# `package(package_path, files=None, base_path='.', opt=None)`
# if package not in the same directory as the manifest file, use `base_path`.
package("connection")
