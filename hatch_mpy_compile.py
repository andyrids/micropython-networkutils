import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Dict, List

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from typing import Type
from hatchling.plugin import hookimpl


class MpyCompileHook(BuildHookInterface):
    """
    A Hatch build hook to compile .py files to .mpy files using mpy-cross.
    """
    PLUGIN_NAME = "mpy-compile"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """
        This method is called before each build.
        It finds specified .py files, compiles them to .mpy, and adjusts
        the build artifacts to include the .mpy files while excluding the
        original .py files.
        """
        # Run only once
        if self.target_name not in build_data.get("hooks", {}).get(self.PLUGIN_NAME, {}):
            build_data.setdefault("hooks", {}).setdefault(self.PLUGIN_NAME, {})["ran"] = False
        
        if build_data["hooks"][self.PLUGIN_NAME].get("ran", False):
            return

        self.app.display_info("mpy-compile hook: Initializing")

        # --- Check for mpy-cross executable ---
        mpy_cross_exe = "mpy-cross"
        if not shutil.which(mpy_cross_exe):
            self.app.display_warning(
                f"'{mpy_cross_exe}' not found in PATH. "
                f"Attempting to run via 'python -m mpy_cross'."
            )
            # Fallback to module execution
            mpy_cross_cmd_base = [sys.executable, "-m", "mpy_cross"]
        else:
            mpy_cross_cmd_base = [mpy_cross_exe]
        
        # --- Load configuration ---
        include_patterns = self.config.get("include", [])
        if not include_patterns:
            self.app.display_warning("No 'include' patterns found in config. Nothing to compile.")
            return

        mpy_cross_args = self.config.get("mpy_cross_args", [])
        
        self.app.display_info(f"Include patterns: {include_patterns}")
        if mpy_cross_args:
            self.app.display_info(f"mpy-cross args: {mpy_cross_args}")

        # --- Prepare for compilation ---
        # Get the package directory from hatchling's project model
        # This ensures we work within the correct source directory
        package_dir = ""
        if self.build_config.sources:
            package_dir = list(self.build_config.sources.keys())[0]
        
        if not package_dir:
            self.app.display_error("Could not determine the source package directory.")
            raise RuntimeError("Source directory not configured in [tool.hatch.build.targets...]")

        source_root = self.root / pathlib.Path(package_dir)
        self.app.display_info(f"Scanning for .py files in: {source_root}")

        compiled_files = {}
        excluded_source_files = []

        # --- Find and compile files ---
        for pattern in include_patterns:
            for py_file in source_root.glob(pattern):
                if not py_file.is_file():
                    continue

                # Ensure we have a relative path for artifact mapping
                relative_py_path = py_file.relative_to(self.root)
                mpy_file = py_file.with_suffix(".mpy")
                relative_mpy_path = mpy_file.relative_to(self.root)

                self.app.display_info(f"Compiling: {relative_py_path} -> {relative_mpy_path}")

                # Construct the mpy-cross command
                command = [
                    *mpy_cross_cmd_base,
                    *mpy_cross_args,
                    str(py_file)
                ]
                
                # Execute the compilation
                try:
                    process = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=self.root,
                    )
                    if process.stderr:
                        self.app.display_warning(f"mpy-cross stderr:\n{process.stderr}")
                    
                    self.app.display_success(f"Successfully compiled: {relative_py_path}")
                    
                    # Track files for inclusion/exclusion
                    # The key for force_include is the on-disk path (absolute)
                    # The value is the path within the archive (relative)
                    compiled_files[str(mpy_file)] = str(relative_mpy_path)
                    excluded_source_files.append(str(relative_py_path))

                except FileNotFoundError:
                    self.app.display_error("Failed to execute mpy-cross.")
                    self.app.display_error(
                        "Please ensure 'mpy-cross' is installed and in your PATH, "
                        "or that it can be run via 'python -m mpy_cross'."
                    )
                    raise
                except subprocess.CalledProcessError as e:
                    self.app.display_error(
                        f"Failed to compile {relative_py_path}:\n"
                        f"Command: {' '.join(e.cmd)}\n"
                        f"Return Code: {e.returncode}\n"
                        f"Stdout: {e.stdout}\n"
                        f"Stderr: {e.stderr}"
                    )
                    raise RuntimeError(f"mpy-cross compilation failed for {py_file}") from e

        # --- Update build data ---
        if compiled_files:
            self.app.display_info("Updating build artifacts...")
            
            # Use setdefault to safely initialize the keys if they don't exist
            build_data.setdefault("force_include", {})
            build_data.setdefault("exclude", [])

            # Add .mpy files to the build
            for src, dest in compiled_files.items():
                self.app.display_info(f"  -> Including: {dest}")
                build_data["force_include"][src] = dest
            
            # Exclude original .py files
            for py_file_path in excluded_source_files:
                self.app.display_info(f"  -> Excluding: {py_file_path}")
                build_data["exclude"].append(py_file_path)

        build_data["hooks"][self.PLUGIN_NAME]["ran"] = True
        self.app.display_info("mpy-compile hook: Finalized")

@hookimpl
def hatch_register_build_hook() -> Type[MpyCompileHook]:
    return MpyCompileHook