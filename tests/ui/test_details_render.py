"""Every detail view must return a real renderable for every item in the sandbox snapshot.

Regression: Text.rstrip() mutates in place and returns None; using its return value made the
Apps detail body None and crashed the UI.
"""

import pytest
from conftest import fixture_envelope, plain
from rich.console import Group as RichGroup
from rich.text import Text

from djx import apps_view, commands_view, endpoints_view, models_view, urls_view
from djx.tree_model import Context

VIEWS = [endpoints_view, models_view, apps_view, commands_view, urls_view]


@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v.ITEMS)
def test_every_detail_renders(view):
    envelope = fixture_envelope()
    ctx = Context(envelope.project["root"], envelope.data)
    items = envelope.data[view.ITEMS]
    assert items
    for item in items:
        detail = view.detail(item, ctx)
        assert isinstance(detail.body, (Text, RichGroup)), f"{view.__name__}: body is {detail.body!r}"
        assert plain(detail.body).strip()


def test_apps_detail_is_not_none_and_lists_models():
    envelope = fixture_envelope()
    ctx = Context(envelope.project["root"], envelope.data)
    shop = next(a for a in envelope.data["apps"] if a["label"] == "shop")
    detail = apps_view.detail(shop, ctx)
    assert detail.body is not None
    assert "Commands" in plain(detail.body)
    assert any("Product" in str(link.text) for link in detail.links)
