from conftest import FakeEngineClient, leaves, settle
from textual.widgets import Input, Static, Tree

from djx.app import DjxApp
from djx.endpoints_view import mount_prefix
from djx.engine_client import error_envelope
from djx.screens import ErrorScreen


async def test_mounts_and_shows_local_endpoints(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        tree = app.query_one("#tree", Tree)
        endpoints = [n.data for n in leaves(tree)]
        ninja = [e for e in endpoints if e["kind"] == "ninja"]
        assert len([e for e in ninja if e["api"]["version"] == "1.0.0"]) == 12
        assert len([e for e in ninja if e["api"]["version"] == "2.0.0"]) == 2
        assert {e["origin"] for e in endpoints} == {"local"}
        assert "14 Ninja" in str(app.query_one("#summary", Static).content)
        assert "hidden" in str(app.query_one("#summary", Static).content)
        assert "sandbox" in str(app.query_one("#top", Static).content)


async def test_tree_groups(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        tree = app.query_one("#tree", Tree)
        top = [n.label.plain for n in tree.root.children]
        assert top == ["Shop API 1.0.0", "NinjaAPI 2.0.0", "Django"]
        shop = next(n for n in tree.root.children if n.label.plain == "Shop API 1.0.0")
        assert [n.label.plain for n in shop.children] == ["auth", "health", "orders", "products"]


async def test_search_filters_live(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        tree = app.query_one("#tree", Tree)
        before = len(leaves(tree))
        await pilot.press("slash")
        assert app.query_one("#search", Input).has_focus
        await pilot.press(*"products")
        await settle(pilot)
        found = [n.data for n in leaves(tree)]
        assert 0 < len(found) < before
        assert all("products" in (e["path"] + e["view"] + e["url_name"]).lower() for e in found)
        # Escape clears the search and restores the list.
        await pilot.press("escape")
        await settle(pilot)
        assert app.query_one("#search", Input).value == ""
        assert len(leaves(tree)) == before


async def test_search_matches_method_token(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("slash")
        await pilot.press(*"delete products")
        await settle(pilot)
        found = [n.data for n in leaves(app.query_one("#tree", Tree))]
        assert [e["view"] for e in found] == ["shop.api.products.delete_product"]


async def test_other_sections_do_not_crash(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        for key in "2345":
            await pilot.press(key)
            await settle(pilot)
            assert app.section == int(key)
            tree = app.query_one("#tree", Tree)
            assert tree.root.children[0].label.plain == "coming in next step"
        await pilot.press("1")
        await settle(pilot)
        assert leaves(app.query_one("#tree", Tree))


async def test_tab_cycles_sections(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("tab")
        assert app.section == 2
        await pilot.press("shift+tab", "shift+tab")
        assert app.section == 5


async def test_refresh_reloads(app, client):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        assert client.collect_calls == 1
        await pilot.press("r")
        await settle(pilot)
        assert client.collect_calls == 2
        assert leaves(app.query_one("#tree", Tree))


async def test_framework_toggle(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        tree = app.query_one("#tree", Tree)
        local = len(leaves(tree))
        await pilot.press("b")
        await settle(pilot)
        assert len(leaves(tree)) > local + 50
        assert "0 hidden" in str(app.query_one("#summary", Static).content)
        django = next(n for n in tree.root.children if n.label.plain == "Django")
        assert not django.is_expanded
        namespaces = [n.label.plain for n in django.children]
        assert namespaces[0] == "root" and "admin" in namespaces
        await pilot.press("b")
        await settle(pilot)
        assert len(leaves(tree)) == local


async def test_detail_shows_source_path_line(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("slash")
        await pilot.press(*"get_product")
        await settle(pilot)
        detail = str(app.query_one("#detail", Static).content)
        assert "shop.api.products.get_product" in detail
        assert "Shop API 1.0.0" in detail
        assert "/api/v1/products/{product_id}" in detail
        lines = detail.splitlines()
        assert any(line.startswith("shop/api/products.py:") for line in lines)


async def test_wide_shows_two_panes(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        assert app.query_one("#list-pane").display
        assert app.query_one("#detail-pane").display


async def test_narrow_one_pane_with_drill_in(app):
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        assert app.query_one("#list-pane").display
        assert not app.query_one("#detail-pane").display
        await pilot.press("enter")
        await settle(pilot)
        assert not app.query_one("#list-pane").display
        assert app.query_one("#detail-pane").display
        await pilot.press("escape")
        await settle(pilot)
        assert app.query_one("#list-pane").display
        assert not app.query_one("#detail-pane").display


async def test_live_resize(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.resize_terminal(50, 30)
        await settle(pilot)
        assert not app.query_one("#detail-pane").display
        await pilot.resize_terminal(140, 40)
        await settle(pilot)
        assert app.query_one("#detail-pane").display and app.query_one("#list-pane").display


async def test_error_envelope_shows_error_screen():
    error = error_envelope(
        "ModuleNotFoundError",
        "No module named 'x'",
        "Could not import settings module config.settings_broken",
        "Traceback (most recent call last): boom",
    )
    client = FakeEngineClient(error)
    app = DjxApp(client)
    async with app.run_test(size=(80, 30)) as pilot:
        await settle(pilot)
        assert isinstance(app.screen, ErrorScreen)
        text = lambda id_: str(app.screen.query_one(id_, Static).content)
        assert text("#error-type") == "ModuleNotFoundError"
        assert "config.settings_broken" in text("#error-hint")
        assert "boom" in text("#error-traceback")
        # r retries: the error is still there, but the engine was asked again.
        await pilot.press("r")
        await settle(pilot)
        assert client.collect_calls == 2
        assert isinstance(app.screen, ErrorScreen)
        # Once the engine recovers, r returns to the explorer.
        from conftest import fixture_envelope

        client.envelope = fixture_envelope()
        await pilot.press("r")
        await settle(pilot)
        assert not isinstance(app.screen, ErrorScreen)
        assert leaves(app.query_one("#tree", Tree))


async def test_warnings_badge_and_list():
    from conftest import fixture_envelope

    envelope = fixture_envelope()
    envelope.warnings = [{"collector": "models", "message": "boom"}]
    app = DjxApp(FakeEngineClient(envelope))
    async with app.run_test(size=(100, 30)) as pilot:
        await settle(pilot)
        assert "1 warnings" in str(app.query_one("#top", Static).content)
        await pilot.press("w")
        await settle(pilot)
        assert type(app.screen).__name__ == "WarningsScreen"
        await pilot.press("escape")
        await settle(pilot)
        assert type(app.screen).__name__ != "WarningsScreen"


def test_mount_prefix():
    def ep(path):
        return {"path": path}

    assert mount_prefix([ep("/api/v1/a"), ep("/api/v1/b/c")]) == ["api", "v1"]
    assert mount_prefix([ep("/api/v1/health")]) == ["api", "v1"]
    assert mount_prefix([ep("/a")]) == []
