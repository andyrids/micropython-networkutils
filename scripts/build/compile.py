"""A Hatch custom build hook for compilation to MicroPython binaries.

NOTE: This build hook is a WIP.

Configuration of the build hook is set in a package `pyproject.toml` file.
This build hook is setup as a local script and therefore must be used as a
custom build hook (https://hatch.pypa.io/latest/plugins/build-hook/custom/).

This build hook is triggered by the command `uv build` with or without the
`--all-packages` option. This option builds the extension packages such as
`networkutils-mqtt`.

Example `pyproject.toml` config headers:

1. [tool.hatch.build.hooks.custom]

2. [tool.hatch.build.targets.sdist.hooks.custom]

3. [tool.hatch.build.targets.wheel.hooks.custom]

Example `pyproject.toml` config options:

1. `path` - Path of `compile.py` relative to package `pyproject.toml`.

2. `only-include` - Specific relative directory paths to the Python files,
    which are to be compiled by `mpy-cross`.

3. `compiler-option` - Options passed to `mpy-cross`. See documentation
    of all options @ https://pypi.org/project/mpy-cross/.


Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.

Classes:
    CrossCompileHook: A build hook to compile Python files into MicroPython
        binaries.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from typing import Any, Type
from hatchling.plugin import hookimpl


class CrossCompileHook(BuildHookInterface):
    """A build hook to compile Python files into MicroPython binaries."""

    PLUGIN_NAME = "compile"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Build hook entry point, managing the cross-compilation process."""

        self.app.display_info("`CrossCompileHook` - initialize")

        hooks = build_data.setdefault("hooks", {}).setdefault(
            self.PLUGIN_NAME, {}
        )
        if hooks.get("ran", False):
            return

        # compilation command
        command = self._find_compiler()
        # compilation target paths & options
        only_include, options = self._get_config()
        if not only_include:
            pyproject = Path(self.root) / "pyproject.toml"
            self.app.display_warning(f"Missing `only-include` in {pyproject}")
            return

        root = Path(self.root)
        files = self._get_source_files(root, only_include)
        if not files:
            self.app.display_info("No Python files found (`only-include`)")
            hooks["ran"] = True
            return

        self.app.display_info(f"Found; {','.join(map(str, files))}")
        success, stderr = self._compile_files(command, options, files, root)
        if not success:
            self.app.display_error("Batch compilation failed")
            self.app.display_error(stderr)
            raise RuntimeError("`mpy-cross` compilation error")

        artifacts = self._map_artifacts(files, root)
        self._update_build_data(build_data, artifacts)

        hooks["ran"] = True

    def finalize(
        self, version: str, build_data: dict[str, Any], artifact_path: str
    ) -> None:
        """Build hook exit point, managing the cross-compilation process."""
        self.app.display_info("`CrossCompileHook` - finalize")

        lib = Path(artifact_path).parent / "lib"
        if not lib.is_dir():
            lib.mkdir(parents=True)

        root = Path(self.root)
        sources = self.build_config.sources or {}
        for artifact in build_data["artifacts"]:
            rel_artifact = Path(artifact)
            for src_prefix, dest_prefix in sources.items():
                src_prefix_path = Path(src_prefix)
                dest_prefix_path = Path(dest_prefix)
                if not rel_artifact.is_relative_to(src_prefix_path):
                    continue
                rel_artifact = rel_artifact.relative_to(src_prefix_path)
                rel_artifact = dest_prefix_path / rel_artifact
                break

            src = root / artifact
            dest = lib / rel_artifact
            dest.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dest)
            self.app.display_info(f"{dest=}")

    def _compile_files(
        self,
        compiler_cmd: list[str],
        options: list[str],
        py_files: list[Path],
        root: Path,
    ) -> tuple[bool, str]:
        """Batch compile all Python files to MicroPython binary.

        Args:
            compiler_cmd (list[str]): A list containing the compiler command -
                either `mpy-cross` or `python -m mpy_cross`.

            options (list[str]): A list of `mpy-cross` compilation options.

            py_files (list[Path]): A list of `Path` objects for each
                Python compilation target.

            root (Path): A `Path` object for the package root directory.

        Returns:
            tuple[bool, str]: A tuple containing a success flag boolean and
                any `stderr` output.
        """
        if not py_files:
            return True, ""
        cmd = [*compiler_cmd, *options] + list(map(str, py_files))
        self.app.display_info(f"Running command - `{' '.join(cmd)}`")
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=root,
            )

            stderr = process.stderr.strip()
            if stderr:
                self.app.display_warning(f"mpy-cross stderr: {stderr}")
            return True, stderr
        except FileNotFoundError:
            self.app.display_error(f"Command failed - `{' '.join(cmd)}`")
            self.app.display_error("Ensure `mpy-cross` is installed")
            raise
        except subprocess.CalledProcessError as e:
            return False, e.stderr or e.stdout or "Unknown error"

    def _find_compiler(self) -> list[str]:
        """Locate the `mpy-cross` compiler."""
        compiler = "mpy-cross"
        if shutil.which(compiler):
            self.app.display_info(f"Using `{compiler}` for compilation.")
            return [compiler]
        self.app.display_warning(f"`{compiler}` not found in `$PATH`")
        self.app.display_info("Using default command `python -m mpy_cross`")
        return [sys.executable, "-m", "mpy_cross"]

    def _get_config(self) -> tuple[list[str], list[str]]:
        """Retrieve compilation options & build hook configuration.

        Returns:
            tuple[list[str], list[str]]: A list of string values for the
                `only-include` & `compiler-options` config settings.
        """
        only_include = self.config.get("only-include", [])
        options = self.config.get("compiler-options", [])
        return only_include, options

    def _get_source_files(
        self, root: Path, only_include: list[str]
    ) -> list[Path]:
        """Find all Python files within `only-include` directories.

        Args:
            root (Path): Root path - same as package `pyproject.toml`.

            only_include (list[str]): A list of directories specified in the
                custom build hook `only-include` config.

        Returns:
            list[Path]: A list of Path objects for each Python file within the
                `only_include` directories.
        """
        files = []
        self.app.display_info("Searching `only-include` directories")
        for i, directory in enumerate(only_include, start=1):
            path = root / Path(directory)
            self.app.display_info(f"{i}. {path}")
            if path.is_dir():
                files.extend(sorted(path.glob("*.py")))
        return files

    def _map_artifacts(
        self, py_files: list[Path], root: Path
    ) -> dict[str, str]:
        """Map compiled binary file paths relative to package root directory.

        Args:
            py_files (list[Path]): A list of `Path` objects for each
                Python compilation target.

            root (Path): A `Path` object for the package root directory.

        Returns:
            dict[str, str]: A dict containing compiled binary file paths
                as keys and relative paths as values.
        """
        compiled_files = {}
        for py in py_files:
            mpy = py.with_suffix(".mpy")
            compiled_files[str(mpy)] = str(mpy.relative_to(root))
        return compiled_files

    def _update_build_data(
        self, build_data: dict[str, Any], compiled_files: dict[str, str]
    ) -> None:
        """Update `build_data` to include MicroPython binaries in artifacts.

        Args:
            build_data: dict[str, Any]: Package build data.
        """
        build_data.setdefault("artifacts", [])
        self.app.display_info("Updating `build_data` artifacts")
        for path in compiled_files.values():
            self.app.display_info(f"+ {path}")
            build_data["artifacts"].append(path)
