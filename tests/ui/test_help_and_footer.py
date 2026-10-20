from conftest import plain, settle
from textual.widgets import Static

from djx.app import DjxApp
from djx.screens import HELP_GROUPS, NARROW_FOOTER, HelpScreen

KEY_LABELS = {
    "slash": "/",
    "question_mark": "?",
    "escape": "Esc",
    "backspace": "Backspace",
    "tab": "Tab",
    "shift+tab": "Shift-Tab",
    "right": "→",
    "enter": "Enter",
}


def test_help_lists_every_bound_key():
    help_text = " ".join(f"{keys} {what}" for _, rows in HELP_GROUPS for keys, what in rows)
    missing = []
    for binding in DjxApp.BINDINGS:
        if binding.key in "12345":
            label = "1-5"
        else:
            label = KEY_LABELS.get(binding.key, binding.key)
        if label not in help_text:
            missing.append(binding.key)
    assert not missing, f"keys bound but missing from the ? help: {missing}"


def test_help_is_grouped_by_section():
    titles = [title for title, _ in HELP_GROUPS]
    assert titles == ["Everywhere", "Endpoints", "Models", "Apps", "Commands", "URLs"]


async def test_help_screen_shows_groups(app):
    async with app.run_test(size=(100, 40)) as pilot:
        await settle(pilot)
        await pilot.press("question_mark")
        await settle(pilot)
        assert isinstance(app.screen, HelpScreen)
        texts = [plain(w.content) for w in app.screen.query(Static)]
        assert any("Models" in t for t in texts) and any("Backspace" in t for t in texts)


async def test_narrow_footer_is_not_truncated(app):
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        assert app.query_one("#narrow-footer").display
        assert not app.query_one("Footer").display
        last = [s.text.rstrip() for s in app.screen._compositor.render_strips()][-1]
        assert NARROW_FOOTER in last
        assert len(NARROW_FOOTER) <= 50


async def test_wide_uses_the_real_footer(app):
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        assert app.query_one("Footer").display
        assert not app.query_one("#narrow-footer").display
