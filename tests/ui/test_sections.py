from conftest import (
    FakeEngineClient,
    fixture_envelope,
    group_titles,
    leaves,
    link_texts,
    plain,
    settle,
)
from textual.widgets import Input, OptionList, Static, Tree

from djx.app import ArgInput, DjxApp


async def search(pilot, text):
    await pilot.press("slash")
    await pilot.press(*text)
    await pilot.press("enter")
    await settle(pilot)


def detail_text(app):
    return plain(app.query_one("#detail", Static).content)


# ---- models ----


async def test_models_tree_hides_django_until_b(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await settle(pilot)
        assert group_titles(app) == ["blog", "shop"]
        labels = [n.label.plain for n in leaves(app.query_one("#tree", Tree))]
        assert "ActiveProduct proxy" in labels
        assert "User" not in labels
        await pilot.press("b")
        await settle(pilot)
        assert "auth" in group_titles(app)
        assert group_titles(app)[:2] == ["blog", "shop"]  # local stays first
        await pilot.press("b")
        await settle(pilot)
        assert "auth" not in group_titles(app)


async def test_model_detail_shows_fk_to_category(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "shop.product")
        text = detail_text(app)
        assert "shop.Product" in text
        assert "shop_product" in text
        assert "category" in text and "ForeignKey" in text
        assert "fk → shop.Category" in text
        assert "shop/models.py:" in text
        links = link_texts(app)
        assert links[0] == "Relations"
        assert any("category" in t and "shop.Category" in t and "products" in t for t in links)
        assert "Referenced by" in links
        assert any("orderitem_set" in t and "shop.OrderItem" in t for t in links)


async def test_model_search_matches_field_names(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "sku")
        found = [n.data["label"] for n in leaves(app.query_one("#tree", Tree))]
        assert "shop.Product" in found


async def test_enter_on_relation_navigates_and_backspace_returns(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "shop.product")
        await pilot.press("l")
        assert app.query_one("#links", OptionList).has_focus
        await pilot.press("enter")  # first non-heading link: category
        await settle(pilot)
        assert app.djx_selected_key == "shop.Category"
        assert "shop_category" in detail_text(app)
        await pilot.press("backspace")
        await settle(pilot)
        assert app.djx_selected_key == "shop.Product"


async def test_relation_to_hidden_model_reveals_framework(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "shop.customer")
        await pilot.press("l")
        await pilot.press("enter")  # Customer.user -> auth.User (hidden by default)
        await settle(pilot)
        assert app.djx_selected_key == "auth.User"
        assert app.show_framework is True
        await pilot.press("backspace")
        await settle(pilot)
        assert app.djx_selected_key == "shop.Customer"


# ---- apps ----


async def test_apps_grouped_by_origin_and_jump_to_model(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("3")
        await settle(pilot)
        assert group_titles(app) == ["local", "third_party", "django"]
        await search(pilot, "shop")
        text = detail_text(app)
        assert "shop" in text and "Models" in text
        links = link_texts(app)
        assert links[0] == "Models"
        assert any("Product" in t for t in links)
        await pilot.press("l")
        await pilot.press("enter")
        await settle(pilot)
        assert app.section == 2
        assert app.djx_selected_key.startswith("shop.")
        await pilot.press("backspace")
        await settle(pilot)
        assert app.section == 3 and app.djx_selected_key == "shop"


# ---- commands ----


async def test_commands_local_first_and_builtin_toggle(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("4")
        await settle(pilot)
        assert group_titles(app) == ["blog", "shop", "ninja"]  # local first, then third party
        names = [n.data["name"] for n in leaves(app.query_one("#tree", Tree))]
        assert "seed_shop" in names and "migrate" not in names
        await pilot.press("b")
        await settle(pilot)
        names = [n.data["name"] for n in leaves(app.query_one("#tree", Tree))]
        assert "migrate" in names
        assert group_titles(app)[:2] == ["blog", "shop"]


async def test_command_detail(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("4")
        await search(pilot, "seed_shop")
        text = detail_text(app)
        assert "seed_shop" in text and "local" in text
        assert "Seed the shop" in text
        assert "shop/management/commands/seed_shop.py:" in text


# ---- urls ----


async def test_urls_list_and_filter(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await settle(pilot)
        assert group_titles(app) == ["root", "api-v1", "api-v2", "blog", "shop"]
        names = {n.data["name"] for n in leaves(app.query_one("#tree", Tree))}
        assert "blog:post-detail" in names and not any(n.startswith("admin:") for n in names)
        await pilot.press("b")
        await settle(pilot)
        names = {n.data["name"] for n in leaves(app.query_one("#tree", Tree))}
        assert any(n.startswith("admin:") for n in names)


async def test_url_search_and_detail(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "post-detail")
        text = detail_text(app)
        assert "blog:post-detail" in text and "/blog/<slug:slug>/" in text
        assert "blog.views.PostDetailView" in text
        assert "blog/views.py:" in text


async def test_reverse_form_types_into_url(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "post-detail")
        inputs = list(app.query(ArgInput))
        assert [i.arg_name for i in inputs] == ["slug"]
        assert "fill in: slug" in plain(app.query_one("#reverse-result", Static).content)
        await pilot.press("l")
        assert inputs[0].has_focus
        await pilot.press(*"hello")
        await pilot.pause(0.6)
        await settle(pilot)
        assert "/blog/hello/" in plain(app.query_one("#reverse-result", Static).content)
        # Escape leaves the form, back to the list.
        await pilot.press("escape")
        assert app.query_one("#tree", Tree).has_focus


async def test_reverse_form_is_debounced(monkeypatch):
    monkeypatch.setattr("djx.app.DEBOUNCE_SECONDS", 1.0)  # roomy, so slow CI keystrokes still batch
    client = FakeEngineClient()
    calls = []
    original = client.reverse
    client.reverse = lambda name, *a, **k: (calls.append(name), original(name, *a, **k))[1]
    app = DjxApp(client)
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "post-detail")
        await pilot.press("l")
        await pilot.press(*"hello")  # five keystrokes inside the debounce window
        await pilot.pause(1.5)
        await settle(pilot)
        assert calls[-3:].count("blog:post-detail") == 1  # earlier calls are the no-arg `home`
        assert calls.count("blog:post-detail") == 1


async def test_url_without_args_reverses_immediately(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "home")
        await settle(pilot)
        assert not list(app.query(ArgInput))
        assert "→ /" in plain(app.query_one("#reverse-result", Static).content)


async def test_unnamed_groups_disable_the_form():
    envelope = fixture_envelope()
    for url in envelope.data["url_names"]:
        if url["name"] == "blog:post-detail":
            url["unnamed_groups"] = 1
    app = DjxApp(FakeEngineClient(envelope))
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await search(pilot, "post-detail")
        assert not list(app.query(ArgInput))
        hint = plain(app.query_one("#form-hint", Static).content)
        assert hint.strip() == "Positional args can't be filled here. Use Resolve instead."


async def test_resolve_path(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")
        await settle(pilot)
        await pilot.press("p")
        assert app.query_one("#resolve-input", Input).has_focus
        await pilot.press(*"/api/v1/health")
        await pilot.pause(0.6)
        await settle(pilot)
        result = plain(app.query_one("#resolve-result", Static).content)
        assert "config.api.health" in result and "api-v1:health" in result
        assert "config/api.py:" in result
        app.query_one("#resolve-input", Input).value = "/nope/nope/"
        await pilot.pause(0.6)
        await settle(pilot)
        assert "No URL matches" in plain(app.query_one("#resolve-result", Static).content)


# ---- narrow terminals ----


async def test_every_section_is_usable_at_50_columns(app):
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        for key in "12345":
            await pilot.press(key)
            await settle(pilot)
            assert app.query_one("#list-pane").display
            assert not app.query_one("#detail-pane").display
            await pilot.press("enter")
            await settle(pilot)
            assert app.query_one("#detail-pane").display
            assert not app.query_one("#list-pane").display
            await pilot.press("escape")
            await settle(pilot)
            assert app.query_one("#list-pane").display


async def test_narrow_cross_link_stays_in_detail_and_backspace_returns(app):
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await search(pilot, "shop.product")
        await pilot.press("enter")  # drill in
        await settle(pilot)
        await pilot.press("l")
        await pilot.press("enter")
        await settle(pilot)
        assert app.djx_selected_key == "shop.Category"
        assert app.query_one("#detail-pane").display and not app.query_one("#list-pane").display
        await pilot.press("backspace")
        await settle(pilot)
        assert app.djx_selected_key == "shop.Product"


async def test_selecting_a_url_without_args_reverses_exactly_once():
    client = FakeEngineClient()
    calls = []
    original = client.reverse
    client.reverse = lambda name, *a, **k: (calls.append(name), original(name, *a, **k))[1]
    app = DjxApp(client)
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("5")  # first URL is `home`, which takes no args
        await pilot.pause(0.5)
        await settle(pilot)
        assert app.djx_selected_item["name"] == "home"
        assert calls == ["home"]
        # Moving away and back is a new request, not a repeat of the old one.
        await pilot.press("j")
        await pilot.pause(0.5)
        await settle(pilot)
        assert calls.count("home") == 1


async def test_keys_work_while_the_engine_is_still_loading():
    import time

    class Slow(FakeEngineClient):
        def collect(self):
            time.sleep(0.8)
            return super().collect()

    app = DjxApp(Slow())
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.2)
        assert app.query_one("LoadingIndicator").display
        await pilot.press("question_mark")  # must open help, not type into the search box
        await pilot.pause(0.2)
        assert type(app.screen).__name__ == "HelpScreen"
        assert app.query_one("#search", Input).value == ""
        await pilot.press("escape")
        await settle(pilot)
        assert leaves(app.query_one("#tree", Tree))
