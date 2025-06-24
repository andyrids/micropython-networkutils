import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from typing import Type
from hatchling.plugin import hookimpl


class CrossCompileHook(BuildHookInterface):
    """A Hatch build hook to compile .py files to .mpy files using mpy-cross.
    """
    PLUGIN_NAME = "compile"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """
        This method is called before each build.
        It finds specified .py files, compiles them to .mpy, and adjusts
        the build artifacts to include the .mpy files while excluding the
        original .py files.
        """

        self.app.display_mini_header("`CrossCompileHook` BUILD HOOK INIT")

        # Run only once
        if self.target_name not in build_data.get("hooks", {}).get(self.PLUGIN_NAME, {}):
            build_data.setdefault("hooks", {}).setdefault(self.PLUGIN_NAME, {})["ran"] = False
        
        if build_data["hooks"][self.PLUGIN_NAME].get("ran", False):
            return

        # check for mpy-cross executable
        compiler = "mpy-cross"
        if not shutil.which(compiler):
            self.app.display_warning(f"`{compiler}` NOT FOUND IN PATH")
            self.app.display_info("USING COMMAND: `python -m mpy_cross`")                    
            command = [sys.executable, "-m", "mpy_cross"]
        else:
            command = [compiler]
        
        # load configuration
        only_include = self.config.get("only-include", [])
        if not only_include:
            self.app.display_warning("MISSING `only-include` IN CONFIG")
            return
        self.app.display_info(f"COMPILATION DIRECTORIES: {only_include}")

        options = self.config.get("compiler-options", [])
        if options:
            self.app.display_info(f"USING `compiler-options`: {options}")

        # --- Prepare for compilation ---
        # Get the package directory from hatchling's project model
        # This ensures we work within the correct source directory
        # package_dir = self.config.get("source-root")
        # if not package_dir and self.build_config.sources:
        #     self.app.display_info("`source-root` unset, using `build_config.sources`")
        #     self.app.display_info(f"{self.build_config.sources=}")
        #     package_dir = list(self.build_config.sources.keys())[0]
        # if not package_dir:
        #     self.app.display_error("Could not determine the source package directory.")
        #     raise RuntimeError("Source directory not configured in [tool.hatch.build.targets...]")

        self.app.display_info(f"PACKAGE ROOT DIR: {self.root}")
        self.app.display_info("SCANNING FOR FILES IN:")
        for i, dir_ in enumerate(only_include, start=1):
            self.app.display_info(f"{i}. {self.root / Path(dir_)}")

        compiled_files = {}
        excluded_source_files = []

        root = Path(self.root)
        # find & compile Python files
        for directory in only_include:
            for py in (root / directory).glob("*.py"):
                if not py.is_file():
                    continue
                self.app.display_info(f"FOUND {py=}")

                # ensure relative path for artifact mapping
                relative_py = py.relative_to(root)
                mpy = py.with_suffix(".mpy")
                relative_mpy = mpy.relative_to(root)

                self.app.display_info(f"COMPILING: {relative_py} -> {relative_mpy}")

                # Construct the mpy-cross command
                command = [
                    *command,
                    *options,
                    str(py)
                ]
                
                # compile Python file
                try:
                    process = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=root,
                    )
                    if process.stderr:
                        self.app.display_warning(f"{process.stderr=}")
                    self.app.display_success(f"COMPILED: {relative_py}")
                    
                    # Track files for inclusion/exclusion
                    # The key for force_include is the on-disk path (absolute)
                    # The value is the path within the archive (relative)
                    compiled_files[str(mpy)] = str(relative_mpy)
                    excluded_source_files.append(str(relative_py))

                except FileNotFoundError:
                    self.app.display_error(f"FAILED TO EXECUTE `{command}`")
                    self.app.display_error("ENSURE `mpy-cross` IS INSTALLED")
                    raise
                except subprocess.CalledProcessError as e:
                    self.app.display_error(f"FAILED TO COMPILE `{relative_py}`")
                    self.app.display_error(f"COMMAND: `{' '.join(e.cmd)}`")
                    self.app.display_error(f"RETURN CODE: `{e.returncode}`")
                    self.app.display_error(f"STDOUT: `{e.stdout}`")
                    self.app.display_error(f"STDERR: `{e.stderr}`")
                    raise RuntimeError(f"FAILED TO COMPILE {py}") from e

        # update build data
        if compiled_files:
            self.app.display_info("UPDATING ARTIFACTS")
            
            # Use setdefault to safely initialize the keys if they don't exist
            build_data.setdefault("force_include", {})
            build_data.setdefault("exclude", [])

            # Add .mpy files to the build
            for src, dest in compiled_files.items():
                self.app.display_info(f"\t-> INCLUDING: {dest}")
                build_data["force_include"][src] = dest
            
            # Exclude original .py files
            for file in excluded_source_files:
                self.app.display_info(f"\t-> EXCLUDING: {file}")
                build_data["exclude"].append(file)

        build_data["hooks"][self.PLUGIN_NAME]["ran"] = True
        
        self.app.display_info(f"BUILD DATA: {build_data}")
        self.app.display_info("CUSTOM HOOK (CrossCompileHook): FINALISED")

@hookimpl
def hatch_register_build_hook() -> Type[CrossCompileHook]:
    return CrossCompileHook