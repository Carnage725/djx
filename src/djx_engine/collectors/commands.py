from __future__ import annotations

from typing import Any

from django.apps import apps
from django.core.management import get_commands, load_command_class

from djx_engine import diagnostics
from djx_engine.sources import app_origin, source_of


def command_owners() -> dict[str, tuple[str, str]]:
    """command name -> (app label or raw module name, origin)."""
    configs = {config.name: config for config in apps.get_app_configs()}
    owners = {}
    for name, app_name in get_commands().items():
        config = configs.get(app_name)
        label = config.label if config else app_name
        path = config.path if config else None
        owners[name] = (label, app_origin(app_name, path))
    return owners


def collect_commands() -> list[dict[str, Any]]:
    result = []
    for name, app_name in sorted(get_commands().items()):
        label, origin = command_owners()[name]
        help_text = ""
        source = {"file": None, "line": None}
        try:
            command = load_command_class(app_name, name)
            help_text = str(command.help).strip()
            source = source_of(type(command))
        except Exception as exc:  # noqa: BLE001 - keep the command, record why it failed
            diagnostics.warn("commands", f"Could not load command {name}: {exc}")
        result.append(
            {"name": name, "app": label, "origin": origin, "help": help_text, "source": source}
        )
    # Local first, then by name (sorted() is stable).
    order = {"local": 0, "third_party": 1, "django": 2}
    result.sort(key=lambda c: (order[c["origin"]], c["name"]))
    return result
