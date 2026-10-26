"""`reverse` and `resolve` subcommands."""

from __future__ import annotations

from typing import Any

from djx_engine.bootstrap import EngineError
from djx_engine.collectors.ninja_introspect import find_path_view
from djx_engine.contract import SCHEMA_VERSION
from djx_engine.sources import source_of
from djx_engine.urlwalk import dotted


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "ok": True, "data": data}


def reverse_url(name: str, args: list[str], kwargs: list[tuple[str, str]]) -> dict[str, Any]:
    """Build a URL from a URL name and args or kwargs, as `django.urls.reverse` does."""
    from django.urls import NoReverseMatch, reverse

    if args and kwargs:
        raise EngineError("ValueError", "Use either --arg or --kwarg, not both.", "Django cannot mix them.")
    try:
        url = reverse(name, args=args or None, kwargs=dict(kwargs) or None)
    except NoReverseMatch as exc:
        raise EngineError(
            "NoReverseMatch", str(exc), "Check the URL name and that the args/kwargs match."
        ) from exc
    return _ok({"url": url})


def resolve_path(path: str) -> dict[str, Any]:
    """Find the view, URL name, kwargs and source location for a URL path."""
    from django.urls import Resolver404, resolve

    try:
        match = resolve(path)
    except Resolver404 as exc:
        raise EngineError(
            "Resolver404", f"No URL matches {path!r}.", "Paths start with '/', e.g. /blog/hello/."
        ) from exc
    view = match.func
    methods: list[str] = []
    path_view = find_path_view(view)
    if path_view is not None and path_view.operations:
        # Django picked the first pattern, which belongs to the first operation.
        view = path_view.operations[0].view_func
        methods = sorted({m.upper() for op in path_view.operations for m in op.methods})
    url_name = ":".join([*match.namespaces, match.url_name]) if match.url_name else None
    return _ok(
        {
            "view": dotted(view),
            "url_name": url_name,
            "kwargs": match.kwargs,
            "methods": methods,
            "source": source_of(view),
        }
    )
