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
    unnamed_groups: int
    operation: Any = None  # ninja Operation when the pattern belongs to Ninja
    extra: dict[str, Any] = field(default_factory=dict)


def _group_names(pattern: Any) -> list[str]:
    try:
        groups = pattern.regex.groupindex
    except Exception:  # noqa: BLE001 - exotic pattern classes
        return []
    return [name for name, _ in sorted(groups.items(), key=lambda item: item[1])]


def _unnamed_group_count(pattern: Any) -> int:
    try:
        regex = pattern.regex
        return regex.groups - len(regex.groupindex)
    except Exception:  # noqa: BLE001 - exotic pattern classes
        return 0


def _piece(pattern: Any) -> str:
    text = str(pattern)
    if type(pattern).__name__ == "RegexPattern":
        text = text.removeprefix("^").removesuffix("$")
    return text


def walk(collector: str, matcher: Any = None) -> Iterator[Entry]:
    # Imported here: the collectors package imports this module, so a top-level import would loop.
    from django.urls import URLResolver, get_resolver

    from djx_engine.collectors.ninja_introspect import NinjaMatcher

    matcher = matcher or NinjaMatcher()

    def visit(
        patterns: Any, prefix: str, namespaces: list[str], args: list[str], unnamed: int
    ) -> Iterator[Entry]:
        for p in patterns:
            route = prefix + _piece(p.pattern)
            p_args = args + _group_names(p.pattern)
            p_unnamed = unnamed + _unnamed_group_count(p.pattern)
            if isinstance(p, URLResolver):
                inner = namespaces + [p.namespace] if p.namespace else namespaces
                try:
                    children = p.url_patterns
                except Exception as exc:  # noqa: BLE001 - skip one broken include, keep going
                    diagnostics.warn(collector, f"Could not load urls for {route!r}: {exc}")
                    continue
                yield from visit(children, route, inner, p_args, p_unnamed)
                continue
            name = ":".join([*namespaces, p.name]) if p.name else None
            operation = matcher.operation_for(p.callback)
            yield Entry(
                callback=p.callback,
                route=route,
                name=name,
                namespace=":".join(namespaces) or None,
                args=p_args,
                unnamed_groups=p_unnamed,
                operation=operation,
            )

    for entry in visit(get_resolver().url_patterns, "", [], [], 0):
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
