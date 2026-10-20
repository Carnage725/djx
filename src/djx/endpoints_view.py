"""Pure functions for the Endpoints section: filter, group, label, detail text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.text import Text

from djx.tree_model import Context, Detail, Group, Leaf, matches_all, rows_text

METHOD_STYLES = {
    "GET": "bold white on green",
    "POST": "bold white on blue",
    "PUT": "bold white on dark_orange",
    "PATCH": "bold black on yellow",
    "DELETE": "bold white on red",
    "ANY": "bold white on grey42",
}


def is_visible(endpoint: dict[str, Any], show_framework: bool) -> bool:
    return show_framework or endpoint["origin"] == "local"


visible = is_visible


def method_label(endpoint: dict[str, Any]) -> str:
    methods = endpoint["methods"]
    if not methods:
        return "ANY"
    return methods[0] if len(methods) == 1 else f"{methods[0]}+{len(methods) - 1}"


def matches(endpoint: dict[str, Any], query: str) -> bool:
    """Every whitespace-separated token must appear in method, path, url_name, view or tags."""
    haystack = " ".join(
        [
            " ".join(endpoint["methods"]) or "any",
            endpoint["path"],
            endpoint["url_name"] or "",
            endpoint["view"],
            " ".join(endpoint["tags"]),
        ]
    )
    return matches_all(haystack, query)


def mount_prefix(endpoints: list[dict[str, Any]]) -> list[str]:
    """Leading path segments shared by every endpoint of one API (e.g. ["api", "v1"])."""
    paths = [[s for s in e["path"].split("/") if s] for e in endpoints]
    prefix: list[str] = []
    for parts in zip(*paths, strict=False):
        if len(set(parts)) != 1:
            break
        prefix.append(parts[0])
    return prefix[: max(min(len(p) for p in paths) - 1, 0)]


def short_path(endpoint: dict[str, Any], prefix: list[str]) -> str:
    parts = [s for s in endpoint["path"].split("/") if s]
    return "/" + "/".join(parts[len(prefix) :])


def label(endpoint: dict[str, Any], path: str) -> Text:
    method = method_label(endpoint)
    style = METHOD_STYLES.get(method.split("+")[0], METHOD_STYLES["ANY"])
    text = Text.assemble((f" {method:<6}", style), " ", path)
    if endpoint["is_async"]:
        text.append(" async", style="dim italic")
    return text



@dataclass
class Counts:
    ninja: int = 0
    django: int = 0
    hidden: int = 0

    def text(self) -> str:
        return f"{self.ninja} Ninja · {self.django} Django · {self.hidden} hidden"


def build_groups(
    endpoints: list[dict[str, Any]], query: str, show_framework: bool
) -> tuple[list[Group], Counts]:
    """Ninja: api -> first path segment -> endpoints. Django: namespace -> endpoints."""
    counts = Counts()
    shown = []
    for endpoint in endpoints:
        if not is_visible(endpoint, show_framework):
            counts.hidden += 1
            continue
        shown.append(endpoint)
        if endpoint["kind"] == "ninja":
            counts.ninja += 1
        else:
            counts.django += 1

    prefixes: dict[tuple[str, str], list[str]] = {}
    apis: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for endpoint in shown:
        if endpoint["kind"] == "ninja":
            key = (endpoint["api"]["title"], endpoint["api"]["version"])
            apis.setdefault(key, []).append(endpoint)
    for key, members in apis.items():
        prefixes[key] = mount_prefix(members)

    groups: list[Group] = []
    for key in sorted(apis, key=lambda k: (k[1], k[0])):  # by version, then title
        prefix = prefixes[key]
        segments: dict[str, Group] = {}
        for endpoint in apis[key]:
            if not matches(endpoint, query):
                continue
            parts = [s for s in endpoint["path"].split("/") if s][len(prefix) :]
            segment = segments.setdefault(parts[0] if parts else "/", Group(parts[0] if parts else "/"))
            segment.items.append(Leaf(endpoint, label(endpoint, short_path(endpoint, prefix))))
        if segments:
            groups.append(Group(f"{key[0]} {key[1]}", list(segments.values())))

    namespaces: dict[str, Group] = {}
    for endpoint in shown:
        if endpoint["kind"] != "django" or not matches(endpoint, query):
            continue
        name = endpoint["url_name"] or ""
        namespace = name.split(":")[0] if ":" in name else "root"
        namespaces.setdefault(namespace, Group(namespace)).items.append(
            Leaf(endpoint, label(endpoint, endpoint["path"]))
        )
    if namespaces:
        ordered = sorted(namespaces.values(), key=lambda g: (g.title != "root", g.title))
        groups.append(Group("Django", list(ordered), collapsed=show_framework and not query))
    return groups, counts


def detail(endpoint: dict[str, Any], ctx: Context) -> Detail:
    rows = [
        ("Method", ", ".join(endpoint["methods"]) or "ANY"),
        ("Path", endpoint["path"]),
        ("Route", endpoint["route"]),
        ("URL name", endpoint["url_name"] or "-"),
        ("View", endpoint["view"]),
        ("Summary", endpoint["summary"] or "-"),
        ("Tags", ", ".join(endpoint["tags"]) or "-"),
    ]
    if endpoint["api"]:
        rows.append(("API", f"{endpoint['api']['title']} {endpoint['api']['version']}"))
    rows += [
        ("Signature", endpoint["signature"] or "-"),
        ("Async", "yes" if endpoint["is_async"] else "no"),
        ("Origin", endpoint["origin"]),
    ]
    return Detail(rows_text(rows, endpoint["source"], ctx.root))


# ---- section interface used by the app ----

ITEMS = "endpoints"


def key(endpoint: dict[str, Any]) -> str:
    return endpoint["id"]


def build(data: dict[str, Any], query: str, show_framework: bool) -> tuple[list[Group], str]:
    groups, counts = build_groups(data["endpoints"], query, show_framework)
    return groups, counts.text()
