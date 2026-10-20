from __future__ import annotations

from collections.abc import Callable
from typing import Any

from djx_engine.collectors.apps import collect_apps
from djx_engine.collectors.commands import collect_commands
from djx_engine.collectors.endpoints import collect_endpoints
from djx_engine.collectors.models import collect_models
from djx_engine.collectors.url_names import collect_url_names

# (key in envelope["data"], collector). One list, one place.
COLLECTORS: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = [
    ("apps", collect_apps),
    ("models", collect_models),
    ("endpoints", collect_endpoints),
    ("url_names", collect_url_names),
    ("commands", collect_commands),
]
