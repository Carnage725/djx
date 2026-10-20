"""Shapes shared by every section view."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.text import Text

ORIGIN_RANK = {"local": 0, "third_party": 1, "django": 2}


@dataclass
class Leaf:
    item: dict[str, Any]
    label: Text


@dataclass
class Group:
    title: str
    items: list[Group | Leaf] = field(default_factory=list)
    collapsed: bool = False


@dataclass
class Link:
    """A row in the side list of a detail view. `section=None` makes it a heading."""

    text: Text | str
    section: int | None = None
    key: str | None = None


@dataclass
class Detail:
    body: Any  # a Rich renderable
    links: list[Link] = field(default_factory=list)


@dataclass
class Context:
    root: str
    data: dict[str, Any]


def source_text(source: dict[str, Any], root: str) -> str:
    """`relative/path.py:LINE`, a plain string so Cmd+Click works in Zed's terminal."""
    file = source.get("file")
    if not file:
        return "(no source location)"
    try:
        file = str(Path(file).relative_to(root))
    except ValueError:
        pass
    return f"{file}:{source['line']}" if source.get("line") else file


def rows_text(rows: list[tuple[str, str]], source: dict[str, Any] | None, root: str) -> Text:
    """Bold label line, value line, blank line. Source last, on its own line."""
    text = Text()
    for name, value in rows:
        text.append(f"{name}\n", style="bold")
        text.append(f"{value}\n\n")
    if source is not None:
        text.append("Source\n", style="bold")
        text.append(source_text(source, root))
    return text


def matches_all(haystack: str, query: str) -> bool:
    """Every whitespace-separated token must appear (case-insensitive)."""
    haystack = haystack.lower()
    return all(token in haystack for token in query.lower().split())
