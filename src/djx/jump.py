"""Open a source location in the user's editor (Zed by default)."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from djx.tree_model import source_text

# `zed path:line[:col]`, checked against https://zed.dev/docs/reference/cli
EDITOR_TEMPLATES = [
    ("zed", "zed {file}:{line}"),
    ("zeditor", "zeditor {file}:{line}"),
    ("code", "code -g {file}:{line}"),
]
NO_EDITOR = "No editor found. Set --editor or DJX_EDITOR."
PLACEHOLDER = re.compile(r"\{(file|line|col)\}")


@dataclass
class JumpResult:
    ok: bool
    message: str
    severity: str  # a Textual notify severity


def source_of_item(section: int, item: dict[str, Any]) -> dict[str, Any]:
    """The `source` to open for an item. Apps have no source: open the package's __init__."""
    if "source" in item:
        return item["source"]
    return {"file": str(Path(item["path"]) / "__init__.py"), "line": 1}


def expand_template(template: str, file: str, line: int, col: int = 1) -> list[str]:
    """Split the template into arguments first, then fill placeholders.

    Filling after splitting keeps a path with spaces in a single argument.
    """
    values = {"file": file, "line": str(line), "col": str(col)}
    return [PLACEHOLDER.sub(lambda m: values[m.group(1)], part) for part in shlex.split(template)]


def resolve_template(
    flag: str | None,
    env: Mapping[str, str],
    which: Callable[[str], str | None],
) -> str | None:
    """--editor flag > DJX_EDITOR > zed > zeditor > code > $EDITOR. None if nothing is found."""
    if flag:
        return flag
    if env.get("DJX_EDITOR"):
        return env["DJX_EDITOR"]
    for command, template in EDITOR_TEMPLATES:
        if which(command):
            return template
    parts = shlex.split(env.get("EDITOR", ""))
    if parts and which(parts[0]):
        return shlex.join(parts) + " +{line} {file}"
    return None


def open_in_editor(
    source: dict[str, Any],
    root: str,
    flag: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> JumpResult:
    """Start the editor detached, without a shell. Never raises."""
    if not source.get("file"):
        return JumpResult(False, "No source location", "warning")
    shown = source_text(source, root)
    template = resolve_template(flag, os.environ if env is None else env, which or shutil.which)
    if template is None:
        return JumpResult(False, f"{NO_EDITOR}\n{shown}", "warning")
    try:
        argv = expand_template(template, source["file"], source.get("line") or 1)
    except ValueError as exc:
        return JumpResult(False, f"Bad editor template {template!r}: {exc}", "error")
    if not argv:
        return JumpResult(False, "The editor template is empty.", "error")
    name = Path(argv[0]).name
    try:
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return JumpResult(False, f"Could not launch {name}: {exc}", "error")
    return JumpResult(True, f"Opened {shown} in {name}", "information")
