from typing import Type
from hatchling.plugin import hookimpl
from hatch_mpy_compile import MpyCompileHook


@hookimpl
def hatch_register_build_hook() -> Type[MpyCompileHook]:
    return MpyCompileHook
