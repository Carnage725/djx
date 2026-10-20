from __future__ import annotations

from collections import Counter
from typing import Any

from django.apps import apps

from djx_engine.collectors.commands import command_owners
from djx_engine.sources import app_origin


def collect_apps() -> list[dict[str, Any]]:
    command_counts = Counter(label for label, _ in command_owners().values())
    return [
        {
            "label": config.label,
            "name": config.name,
            "verbose_name": str(config.verbose_name),
            "path": config.path,
            "origin": app_origin(config.name, config.path),
            "model_count": len(list(config.get_models())),
            "command_count": command_counts.get(config.label, 0),
        }
        for config in apps.get_app_configs()
    ]
