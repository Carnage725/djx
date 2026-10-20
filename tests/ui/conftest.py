import json
from pathlib import Path

import pytest

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
        return error_envelope("NotImplemented", "fake", "")

    def resolve(self, path) -> Envelope:
        return error_envelope("NotImplemented", "fake", "")


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
