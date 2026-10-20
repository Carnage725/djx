import io
import json
import re
from pathlib import Path

import pytest
from rich.console import Console

from djx.app import DjxApp
from djx.engine_client import Envelope, error_envelope

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sandbox_collect.json"


def fixture_envelope() -> Envelope:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return Envelope(
        ok=True, data=raw["data"], project=raw["project"], warnings=raw["warnings"]
    )


class FakeEngineClient:
    """Serves the committed sandbox snapshot, so UI tests never need Django."""

    def __init__(self, envelope: Envelope | None = None):
        self.envelope = envelope or fixture_envelope()
        self.collect_calls = 0

    def collect(self) -> Envelope:
        self.collect_calls += 1
        return self.envelope

    def reverse(self, name, args=None, kwargs=None) -> Envelope:
        """Same answers as the real engine for the sandbox's simple routes."""
        kwargs = kwargs or {}
        for url in self.envelope.data["url_names"]:
            if url["name"] != name:
                continue
            try:
                path = re.sub(r"<(?:\w+:)?(\w+)>", lambda m: kwargs[m.group(1)], url["route"])
            except KeyError:
                continue
            return Envelope(ok=True, data={"url": path})
        return error_envelope("NoReverseMatch", f"Reverse for '{name}' not found.", "")

    def resolve(self, path) -> Envelope:
        for endpoint in self.envelope.data["endpoints"]:
            pattern = re.sub(r"\{\w+\}", "[^/]+", re.escape(endpoint["path"]).replace("\\{", "{").replace("\\}", "}"))
            if re.fullmatch(pattern.rstrip("/") + "/?", path):
                data = {
                    "view": endpoint["view"],
                    "url_name": endpoint["url_name"],
                    "kwargs": {},
                    "methods": endpoint["methods"],
                    "source": endpoint["source"],
                }
                return Envelope(ok=True, data=data)
        return error_envelope("Resolver404", f"No URL matches {path!r}.", "")


@pytest.fixture
def client():
    return FakeEngineClient()


@pytest.fixture
def app(client):
    return DjxApp(client)


async def settle(pilot):
    """Wait for the engine worker and for the tree to finish rebuilding."""
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()
    await pilot.pause()


def leaves(tree):
    """All leaf nodes that carry data (endpoints)."""
    found = []

    def walk(node):
        for child in node.children:
            if child.children:
                walk(child)
            elif child.data:
                found.append(child)

    walk(tree.root)
    return found


def plain(renderable) -> str:
    """Render any Rich renderable (or str) to plain text, like the terminal would show it."""
    console = Console(file=io.StringIO(), width=100, record=True, color_system=None)
    console.print(renderable)
    return console.export_text()


def link_texts(app) -> list[str]:
    options = app.query_one("#links")
    return [str(options.get_option_at_index(i).prompt) for i in range(options.option_count)]


def group_titles(app) -> list[str]:
    return [n.label.plain for n in app.query_one("#tree").root.children]
