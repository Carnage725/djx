"""URLs section: every named URL, grouped by namespace. The reverse form lives in the app."""

from __future__ import annotations

from typing import Any

from rich.text import Text

from djx.tree_model import Context, Detail, Group, Leaf, matches_all, rows_text

ITEMS = "url_names"
NO_POSITIONAL = "Positional args can't be filled here. Use Resolve instead."


def key(url: dict[str, Any]) -> str:
    return f"{url['name']}|{url['route']}"


def visible(url: dict[str, Any], show_framework: bool) -> bool:
    return show_framework or url["origin"] == "local"


def build(data: dict[str, Any], query: str, show_framework: bool) -> tuple[list[Group], str]:
    shown = [u for u in data["url_names"] if visible(u, show_framework)]
    hidden = len(data["url_names"]) - len(shown)
    namespaces: dict[str, Group] = {}
    for url in shown:
        haystack = f"{url['name']} {url['route']} {url['view']} {url['namespace'] or ''}"
        if not matches_all(haystack, query):
            continue
        text = Text(url["name"].split(":")[-1])
        text.append(f"  {url['route']}", style="dim")
        namespaces.setdefault(url["namespace"] or "root", Group(url["namespace"] or "root")).items.append(
            Leaf(url, text)
        )
    ordered = sorted(namespaces.values(), key=lambda g: (g.title != "root", g.title))
    return ordered, f"{len(shown)} names · {hidden} hidden"


def detail(url: dict[str, Any], ctx: Context) -> Detail:
    rows = [
        ("Name", url["name"]),
        ("Namespace", url["namespace"] or "-"),
        ("Route", url["route"]),
        ("View", url["view"]),
        ("Args", ", ".join(url["args"]) or "-"),
        ("Origin", url["origin"]),
    ]
    return Detail(rows_text(rows, url["source"], ctx.root))
