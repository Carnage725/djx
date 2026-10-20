"""Commands section: app -> management command, local apps first."""

from __future__ import annotations

from typing import Any

from rich.text import Text

from djx.tree_model import ORIGIN_RANK, Context, Detail, Group, Leaf, matches_all, rows_text

ITEMS = "commands"


def key(command: dict[str, Any]) -> str:
    return command["name"]


def visible(command: dict[str, Any], show_framework: bool) -> bool:
    return show_framework or command["origin"] != "django"


def build(data: dict[str, Any], query: str, show_framework: bool) -> tuple[list[Group], str]:
    shown = [c for c in data["commands"] if visible(c, show_framework)]
    hidden = len(data["commands"]) - len(shown)
    apps: dict[str, Group] = {}
    origin_of: dict[str, str] = {}
    for command in shown:
        if not matches_all(f"{command['name']} {command['app']} {command['help']}", query):
            continue
        apps.setdefault(command["app"], Group(command["app"])).items.append(
            Leaf(command, Text(command["name"]))
        )
        origin_of[command["app"]] = command["origin"]
    ordered = sorted(apps.values(), key=lambda g: (ORIGIN_RANK[origin_of[g.title]], g.title))
    return ordered, f"{len(shown)} commands · {hidden} hidden"


def detail(command: dict[str, Any], ctx: Context) -> Detail:
    rows = [
        ("Command", command["name"]),
        ("App", command["app"]),
        ("Origin", command["origin"]),
        ("Help", command["help"] or "-"),
    ]
    return Detail(rows_text(rows, command["source"], ctx.root))
