"""Models section: app -> model tree, fields table, relations that can be followed."""

from __future__ import annotations

from typing import Any

from rich.console import Group as RichGroup
from rich.table import Table
from rich.text import Text

from djx.tree_model import (
    ORIGIN_RANK,
    Context,
    Detail,
    Group,
    Leaf,
    Link,
    matches_all,
    rows_text,
    source_text,
)

ITEMS = "models"
SECTION = 2


def key(model: dict[str, Any]) -> str:
    return model["label"]


def visible(model: dict[str, Any], show_framework: bool) -> bool:
    return show_framework or model["origin"] != "django"


def matches(model: dict[str, Any], query: str) -> bool:
    names = " ".join(f["name"] for f in model["fields"])
    return matches_all(f"{model['label']} {names} {model['db_table']}", query)


def label(model: dict[str, Any]) -> Text:
    text = Text(model["name"])
    if model["proxy"]:
        text.append(" proxy", style="italic yellow")
    return text


def build(data: dict[str, Any], query: str, show_framework: bool) -> tuple[list[Group], str]:
    shown = [m for m in data["models"] if visible(m, show_framework)]
    hidden = len(data["models"]) - len(shown)
    apps: dict[str, Group] = {}
    origin_of: dict[str, str] = {}
    for model in shown:
        if not matches(model, query):
            continue
        apps.setdefault(model["app"], Group(model["app"])).items.append(Leaf(model, label(model)))
        origin_of[model["app"]] = model["origin"]
    ordered = sorted(apps.values(), key=lambda g: (ORIGIN_RANK[origin_of[g.title]], g.title))
    return ordered, f"{len(shown)} models · {hidden} hidden"


def _fields_table(model: dict[str, Any]) -> Table:
    table = Table(box=None, show_edge=False, pad_edge=False, padding=(0, 1), header_style="bold")
    for column in ("name", "type", "null", "uniq", "len", "relation"):
        table.add_column(column, overflow="fold")
    for field in model["fields"]:
        relation = field["relation"]
        table.add_row(
            field["name"],
            field["type"],
            "✓" if field["null"] else "",
            "✓" if field["unique"] else "",
            "" if field["max_length"] is None else str(field["max_length"]),
            f"{relation['kind']} → {relation['to']}" if relation else "",
        )
    return table


def detail(model: dict[str, Any], ctx: Context) -> Detail:
    rows = [
        ("Model", model["label"]),
        ("Table", model["db_table"]),
        ("PK", model["pk"] or "-"),
        ("Ordering", ", ".join(model["ordering"]) or "-"),
    ]
    if model["proxy"]:
        rows.append(("Proxy for", model["proxy_for"]))
    rows.append(("Origin", model["origin"]))
    header = rows_text(rows, None, ctx.root)
    source = Text.assemble(("Source\n", "bold"), source_text(model["source"], ctx.root))
    body = RichGroup(header, Text("Fields", style="bold"), _fields_table(model), Text(), source)

    links: list[Link] = []
    outgoing = [f for f in model["fields"] if f["relation"]]
    if outgoing:
        links.append(Link("Relations"))
        for field in outgoing:
            rel = field["relation"]
            extra = rel["on_delete"] or "m2m"
            if rel["related_name"]:
                extra += f", related_name={rel['related_name']}"
            text = Text.assemble((field["name"], "bold"), f"  {rel['kind']} → {rel['to']}  ")
            text.append(f"({extra})", style="dim")
            links.append(Link(text, SECTION, rel["to"]))
    if model["reverse_relations"]:
        links.append(Link("Referenced by"))
        for rev in model["reverse_relations"]:
            text = Text.assemble((rev["name"], "bold"), f"  {rev['kind']} ← {rev['from']}")
            text.append(f".{rev['field']}", style="dim")
            links.append(Link(text, SECTION, rev["from"]))
    return Detail(body, links)
