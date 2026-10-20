from __future__ import annotations

import inspect
from typing import Any

from djx_engine import diagnostics
from djx_engine.collectors.ninja_introspect import NinjaMatcher
from djx_engine.sources import source_of, unwrap, view_origin
from djx_engine.urlwalk import Entry, display_path, dotted, first_doc_line, walk


def _signature(func: Any) -> str:
    try:
        return str(inspect.signature(unwrap(func)))
    except (TypeError, ValueError):
        return ""


def _class_methods(cls: Any) -> list[str]:
    from django.views import View

    methods = []
    for name in getattr(cls, "http_method_names", []):
        if not hasattr(cls, name):
            continue
        if name == "options" and getattr(cls, name) is View.options:
            continue  # inherited default, not something the class defines
        methods.append(name.upper())
    return methods


def _ninja_summary(operation: Any) -> str:
    func = operation.view_func
    auto = func.__name__.title().replace("_", " ")  # what Ninja invents when none is given
    if operation.summary and operation.summary != auto:
        return operation.summary
    return first_doc_line(func)


def _ninja_endpoints(entry: Entry, path: str) -> list[dict[str, Any]]:
    operation = entry.operation
    func = operation.view_func
    api = operation.api
    api_info = (
        {"title": api.title, "version": api.version, "namespace": api.urls_namespace}
        if api is not None
        else None
    )
    namespace = api_info["namespace"] if api_info else ""
    return [
        {
            "id": f"ninja:{namespace}:{method.upper()}:{path}",
            "kind": "ninja",
            "methods": [method.upper()],
            "path": path,
            "route": entry.route,
            "url_name": entry.name,
            "view": dotted(func),
            "summary": _ninja_summary(operation),
            "tags": list(operation.tags or []),
            "api": api_info,
            "is_async": bool(operation.is_async),
            "signature": _signature(func),
            "origin": view_origin(func),
            "source": source_of(func),
        }
        for method in operation.methods
    ]


def _django_endpoint(entry: Entry, path: str) -> dict[str, Any]:
    callback = entry.callback
    target = unwrap(callback)
    is_class = inspect.isclass(target)
    methods = _class_methods(target) if is_class else []
    return {
        "id": f"django:{','.join(methods) or 'ANY'}:{path}",
        "kind": "django",
        "methods": methods,
        "path": path,
        "route": entry.route,
        "url_name": entry.name,
        "view": dotted(callback),
        "summary": first_doc_line(callback),
        "tags": [],
        "api": None,
        "is_async": inspect.iscoroutinefunction(callback) or inspect.iscoroutinefunction(target),
        "signature": "" if is_class else _signature(callback),
        "origin": view_origin(callback),
        "source": source_of(callback),
    }


def collect_endpoints() -> list[dict[str, Any]]:
    result = []
    matcher = NinjaMatcher()
    for entry in walk("endpoints", matcher):
        path = display_path(entry.route)
        if entry.operation is not None:
            result.extend(_ninja_endpoints(entry, path))
        else:
            result.append(_django_endpoint(entry, path))
    for message in matcher.warnings():
        diagnostics.warn("endpoints", message)
    return sorted(
        result, key=lambda e: (e["kind"], e["path"], e["methods"][0] if e["methods"] else "")
    )
