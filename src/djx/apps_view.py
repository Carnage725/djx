"""Apps section: flat list grouped by origin; jump from an app to its models."""

from __future__ import annotations

from typing import Any

from rich.text import Text

from djx import models_view
from djx.tree_model import ORIGIN_RANK, Context, Detail, Group, Leaf, Link, matches_all, rows_text

ITEMS = "apps"


def key(app: dict[str, Any]) -> str:
    return app["label"]


def visible(app: dict[str, Any], show_framework: bool) -> bool:
    return True  # no `b` filter here: the whole app list is short


def build(data: dict[str, Any], query: str, show_framework: bool) -> tuple[list[Group], str]:
    groups: dict[str, Group] = {}
    count = 0
    for app in data["apps"]:
        haystack = f"{app['label']} {app['name']} {app['verbose_name']} {app['path']}"
        if not matches_all(haystack, query):
            continue
        count += 1
        text = Text(app["label"])
        if app["name"] != app["label"]:
            text.append(f"  {app['name']}", style="dim")
        groups.setdefault(app["origin"], Group(app["origin"])).items.append(Leaf(app, text))
    ordered = sorted(groups.values(), key=lambda g: ORIGIN_RANK[g.title])
    return ordered, f"{count} apps"


def detail(app: dict[str, Any], ctx: Context) -> Detail:
    rows = [
        ("App", app["label"]),
        ("Name", app["name"]),
        ("Verbose name", app["verbose_name"]),
        ("Path", app["path"]),
        ("Origin", app["origin"]),
        ("Models", str(app["model_count"])),
        ("Commands", str(app["command_count"])),
    ]
    models = sorted(
        (m for m in ctx.data["models"] if m["app"] == app["label"]), key=lambda m: m["name"]
    )
    links = [Link("Models")] if models else []
    links += [Link(models_view.label(m), models_view.SECTION, m["label"]) for m in models]
    body = rows_text(rows, None, ctx.root)
    body.rstrip()
    return Detail(body, links)
