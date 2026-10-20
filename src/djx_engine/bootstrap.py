"""Get the user's Django project ready: sys.path, settings module, django.setup()."""

from __future__ import annotations

import os
import re
import sys
from importlib import metadata
from pathlib import Path

from djx_engine.contract import Project

SETTINGS_RE = re.compile(
    r"""os\.environ\.setdefault\(\s*["']DJANGO_SETTINGS_MODULE["']\s*,\s*["']([^"']+)["']"""
)


# Set by setup(); used to tell local code from third-party code.
PROJECT_ROOT: Path | None = None


class EngineError(Exception):
    def __init__(self, type_: str, message: str, hint: str):
        super().__init__(message)
        self.type = type_
        self.message = message
        self.hint = hint


def detect_settings_module(root: Path, override: str | None) -> str:
    """--settings flag > DJANGO_SETTINGS_MODULE env > manage.py (the only text parsing allowed)."""
    if override:
        return override
    env = os.environ.get("DJANGO_SETTINGS_MODULE")
    if env:
        return env
    manage = root / "manage.py"
    if manage.is_file():
        match = SETTINGS_RE.search(manage.read_text(encoding="utf-8", errors="replace"))
        if match:
            return match.group(1)
    raise EngineError(
        "SettingsNotFound",
        "Could not determine DJANGO_SETTINGS_MODULE.",
        "Pass --settings MODULE, set DJANGO_SETTINGS_MODULE, or make manage.py call "
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', '...').",
    )


def _ninja_version() -> str | None:
    try:
        return metadata.version("django-ninja")
    except metadata.PackageNotFoundError:
        return None


def setup(root_arg: str, settings_override: str | None) -> Project:
    global PROJECT_ROOT
    root = Path(root_arg).expanduser().resolve()
    if not root.is_dir():
        raise EngineError("ProjectNotFound", f"Not a directory: {root}", "Check the --root path.")

    PROJECT_ROOT = root
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    settings_module = detect_settings_module(root, settings_override)
    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    try:
        import django
        from django.conf import settings
    except ImportError as exc:
        raise EngineError(
            type(exc).__name__,
            str(exc),
            f"Django is not importable from {sys.executable}. "
            "Point djx at the project's Python (--python or DJX_PYTHON).",
        ) from exc

    try:
        settings.INSTALLED_APPS  # noqa: B018 - forces the settings module to import
    except Exception as exc:
        raise EngineError(
            type(exc).__name__,
            str(exc),
            f"Could not import settings module {settings_module}",
        ) from exc

    try:
        django.setup()
    except Exception as exc:
        raise EngineError(
            type(exc).__name__,
            str(exc),
            f"django.setup() failed for settings module {settings_module}",
        ) from exc

    return {
        "root": str(root),
        "settings_module": settings_module,
        "python": sys.executable,
        "django_version": django.get_version(),
        "ninja_version": _ninja_version(),
    }
