"""Walk Django's URL resolver tree. Shared by the endpoints and url_names collectors."""

from __future__ import annotations

import inspect
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from djx_engine import diagnostics
from djx_engine.sources import unwrap


@dataclass
class Entry:
    callback: Any
    route: str  # concatenated Django route, leading "/", regex anchors removed
    name: str | None  # full name including namespaces, e.g. "blog:post-detail"
    namespace: str | None
    args: list[str]
    operation: Any = None  # ninja Operation when the pattern belongs to Ninja
    extra: dict[str, Any] = field(default_factory=dict)


def _path_view_class() -> Any:
    try:
        from ninja.operation import PathView
    except ImportError:
        return None
    return PathView


def find_path_view(callback: Any, path_view_class: Any) -> Any:
    """Ninja 1.7 hands Django a closure that captures its PathView as `self`.

    Older versions used a bound method. Support both.
    """
    if path_view_class is None:
        return None
    owner = getattr(callback, "__self__", None)
    if isinstance(owner, path_view_class):
        return owner
    for cell in getattr(callback, "__closure__", None) or ():
        try:
            value = cell.cell_contents
        except ValueError:  # empty cell
            continue
        if isinstance(value, path_view_class):
            return value
    return None


def _group_names(pattern: Any) -> list[str]:
    try:
        groups = pattern.regex.groupindex
    except Exception:  # noqa: BLE001 - exotic pattern classes
        return []
    return [name for name, _ in sorted(groups.items(), key=lambda item: item[1])]


def _piece(pattern: Any) -> str:
    text = str(pattern)
    if type(pattern).__name__ == "RegexPattern":
        text = text.removeprefix("^").removesuffix("$")
    return text


def walk(collector: str) -> Iterator[Entry]:
    from django.urls import URLResolver, get_resolver

    path_view_class = _path_view_class()
    counters: dict[int, int] = {}

    def visit(patterns: Any, prefix: str, namespaces: list[str], args: list[str]) -> Iterator[Entry]:
        for p in patterns:
            route = prefix + _piece(p.pattern)
            p_args = args + _group_names(p.pattern)
            if isinstance(p, URLResolver):
                inner = namespaces + [p.namespace] if p.namespace else namespaces
                try:
                    children = p.url_patterns
                except Exception as exc:  # noqa: BLE001 - skip one broken include, keep going
                    diagnostics.warn(collector, f"Could not load urls for {route!r}: {exc}")
                    continue
                yield from visit(children, route, inner, p_args)
                continue
            name = ":".join([*namespaces, p.name]) if p.name else None
            operation = None
            path_view = find_path_view(p.callback, path_view_class)
            if path_view is not None:
                # Ninja yields one URLPattern per operation, in operation order.
                index = counters.get(id(path_view), 0)
                counters[id(path_view)] = index + 1
                if index >= len(path_view.operations):
                    continue
                operation = path_view.operations[index]
            yield Entry(
                callback=p.callback,
                route=route,
                name=name,
                namespace=":".join(namespaces) or None,
                args=p_args,
                operation=operation,
            )

    for entry in visit(get_resolver().url_patterns, "", [], []):
        entry.route = "/" + entry.route.lstrip("/")
        yield entry


def _replace_named_groups(text: str) -> str:
    """Turn regex `(?P<name>...)` into `{name}`, honouring nested parentheses."""
    out = []
    i = 0
    while i < len(text):
        match = re.compile(r"\(\?P<(\w+)>").match(text, i)
        if match:
            depth = 1
            j = match.end()
            while j < len(text) and depth:
                if text[j] == "\\":
                    j += 1
                elif text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            out.append("{" + match.group(1) + "}")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def display_path(route: str) -> str:
    """`/blog/<slug:slug>/` -> `/blog/{slug}/`. Regex routes get the same treatment."""
    path = _replace_named_groups(route)
    path = re.sub(r"<(?:[^>:]+:)?([^>]+)>", r"{\1}", path)
    path = re.sub(r"\\([^A-Za-z0-9])", r"\1", path)
    path = path.replace("^", "").replace("$", "")
    return "/" + re.sub(r"/+", "/", path).lstrip("/")


def dotted(obj: Any) -> str:
    target = unwrap(obj)
    module = getattr(target, "__module__", None)
    qualname = getattr(target, "__qualname__", None) or type(target).__name__
    return f"{module}.{qualname}" if module else qualname


def first_doc_line(obj: Any) -> str:
    doc = getattr(unwrap(obj), "__doc__", None)  # own docstring only, never inherited
    if not isinstance(doc, str) or not doc.strip():
        return ""
    return inspect.cleandoc(doc).splitlines()[0]
