# `metadata(description=None, version=None, license=None, author=None)`
# define metadata for this manifest file. This is useful for `micropython-lib` packages.
metadata(description="", version="0.0.1")

# require(name, library=None)
# require a package by name (and its dependencies) from `micropython-lib`.
require("connection")   

# `package(package_path, files=None, base_path='.', opt=None)`
# if the package isn't in the same directory as the manifest file, use `base_path`.
package("connection")