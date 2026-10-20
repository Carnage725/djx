from __future__ import annotations

from typing import Any

from djx_engine.sources import source_of, view_origin
from djx_engine.urlwalk import dotted, walk


def collect_url_names() -> list[dict[str, Any]]:
    result = []
    for entry in walk("url_names"):
        if entry.name is None:
            continue
        view = entry.operation.view_func if entry.operation is not None else entry.callback
        result.append(
            {
                "name": entry.name,
                "namespace": entry.namespace,
                "route": entry.route,
                "args": entry.args,
                "unnamed_groups": entry.unnamed_groups,
                "view": dotted(view),
                "origin": view_origin(view),
                "source": source_of(view),
            }
        )
    return sorted(result, key=lambda u: (u["name"], u["route"]))
