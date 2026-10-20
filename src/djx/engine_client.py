"""Run the engine as a subprocess under the project's Python and parse its JSON."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from djx_engine.launcher import run_cmd

TIMEOUT_SECONDS = 30
STDERR_TAIL_LINES = 40


@dataclass
class Envelope:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    project: dict[str, Any] = field(default_factory=dict)
    warnings: list[dict[str, str]] = field(default_factory=list)
    error: dict[str, str] | None = None


def error_envelope(type_: str, message: str, hint: str, traceback: str = "") -> Envelope:
    error = {"type": type_, "message": message, "hint": hint, "traceback": traceback}
    return Envelope(ok=False, error=error)


def find_python(root: Path | str, override: str | None = None) -> str:
    """--python flag > DJX_PYTHON env > <root>/.venv > $VIRTUAL_ENV > this interpreter."""
    if override:
        return override
    env = os.environ.get("DJX_PYTHON")
    if env:
        return env
    bin_dir, exe = ("Scripts", "python.exe") if sys.platform == "win32" else ("bin", "python")
    candidate = Path(root) / ".venv" / bin_dir / exe
    if candidate.exists():
        return str(candidate)
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        candidate = Path(virtual_env) / bin_dir / exe
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _tail(text: str) -> str:
    return "\n".join(text.strip().splitlines()[-STDERR_TAIL_LINES:])


def _run(python: str, argv: list[str]) -> Envelope:
    try:
        proc = subprocess.run(
            run_cmd(python, argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        return error_envelope(
            "EngineTimeout",
            f"The engine did not finish within {TIMEOUT_SECONDS} seconds.",
            "Something in the project hangs at import time. Run `djx doctor` or check stderr below.",
            _tail(stderr or ""),
        )
    except OSError as exc:
        return error_envelope(
            "EngineLaunchError",
            f"Could not run {python}: {exc}",
            "Check --python or DJX_PYTHON.",
        )
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return error_envelope(
            "EngineOutputError",
            f"The engine exited with code {proc.returncode} and printed no valid JSON.",
            "Is Django installed in this Python? Try --python or DJX_PYTHON.",
            _tail(proc.stderr) or proc.stdout[:500],
        )
    if not raw.get("ok"):
        error = raw.get("error", {})
        return error_envelope(
            error.get("type", "EngineError"),
            error.get("message", ""),
            error.get("hint", ""),
            error.get("traceback", ""),
        )
    return Envelope(
        ok=True,
        data=raw.get("data", {}),
        project=raw.get("project", {}),
        warnings=raw.get("warnings", []),
    )


def _base_args(command: str, root: Path | str, settings: str | None) -> list[str]:
    argv = [command, "--root", str(Path(root).resolve())]
    if settings:
        argv += ["--settings", settings]
    return argv


def collect(root: Path | str, python: str, settings: str | None = None) -> Envelope:
    return _run(python, _base_args("collect", root, settings))


def reverse(
    root: Path | str,
    python: str,
    name: str,
    args: list[str] | None = None,
    kwargs: dict[str, str] | None = None,
    settings: str | None = None,
) -> Envelope:
    argv = _base_args("reverse", root, settings) + ["--name", name]
    for value in args or []:
        argv += ["--arg", value]
    for key, value in (kwargs or {}).items():
        argv += ["--kwarg", f"{key}={value}"]
    return _run(python, argv)


def resolve(
    root: Path | str, python: str, path: str, settings: str | None = None
) -> Envelope:
    return _run(python, _base_args("resolve", root, settings) + ["--path", path])


class EngineClient:
    """What the app talks to. Tests swap in a fake with the same three methods."""

    def __init__(self, root: Path | str, python: str, settings: str | None = None):
        self.root = Path(root).resolve()
        self.python = python
        self.settings = settings

    def collect(self) -> Envelope:
        return collect(self.root, self.python, self.settings)

    def reverse(
        self, name: str, args: list[str] | None = None, kwargs: dict[str, str] | None = None
    ) -> Envelope:
        return reverse(self.root, self.python, name, args, kwargs, self.settings)

    def resolve(self, path: str) -> Envelope:
        return resolve(self.root, self.python, path, self.settings)
