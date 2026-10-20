"""Build the command that runs the engine under a project's Python.

The engine is loaded from its file location instead of putting its parent directory on
sys.path. That parent may be djx's own site-packages, which would shadow the project's packages.
"""

from __future__ import annotations

from pathlib import Path

_BOOTSTRAP = """\
import importlib.util, sys
pkg_dir = {pkg_dir!r}
spec = importlib.util.spec_from_file_location(
    "djx_engine", pkg_dir + "/__init__.py", submodule_search_locations=[pkg_dir]
)
module = importlib.util.module_from_spec(spec)
sys.modules["djx_engine"] = module
spec.loader.exec_module(module)
from djx_engine.cli import main
sys.exit(main(sys.argv[1:]))
"""


def run_cmd(python: str, argv: list[str]) -> list[str]:
    pkg_dir = str(Path(__file__).resolve().parent)
    return [python, "-c", _BOOTSTRAP.format(pkg_dir=pkg_dir), *argv]
