import subprocess

import pytest
from conftest import FakeEngineClient, fixture_envelope, settle

from djx import jump
from djx.app import DjxApp
from djx.jump import expand_template, open_in_editor, resolve_template, source_of_item

ZED = "zed {file}:{line}"


class PopenRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))


@pytest.fixture
def popen(monkeypatch):
    recorder = PopenRecorder()
    monkeypatch.setattr(jump.subprocess, "Popen", recorder)
    return recorder


@pytest.fixture
def toasts(monkeypatch):
    messages = []
    monkeypatch.setattr(
        DjxApp,
        "notify",
        lambda self, message, **kw: messages.append((message, kw.get("severity", "information"))),
    )
    return messages


# ---- templates ----


def test_template_expansion():
    assert expand_template("zed {file}:{line}", "/p/a.py", 42) == ["zed", "/p/a.py:42"]
    assert expand_template("code -g {file}:{line}", "/p/a.py", 42) == ["code", "-g", "/p/a.py:42"]
    assert expand_template("nvim +{line} {file}", "/p/a.py", 42) == ["nvim", "+42", "/p/a.py"]
    assert expand_template("zed {file}:{line}:{col}", "/p/a.py", 42, 7) == ["zed", "/p/a.py:42:7"]


def test_path_with_spaces_stays_one_argument():
    assert expand_template("zed {file}:{line}", "/My Project/a b.py", 3) == [
        "zed",
        "/My Project/a b.py:3",
    ]
    assert expand_template("nvim +{line} {file}", "/My Project/a b.py", 3) == [
        "nvim",
        "+3",
        "/My Project/a b.py",
    ]


def test_path_that_looks_like_a_placeholder_is_left_alone():
    assert expand_template("ed {file} {line}", "/p/{line}.py", 5) == ["ed", "/p/{line}.py", "5"]


# ---- resolution order ----


def which_of(*found):
    return lambda name: f"/bin/{name}" if name in found else None


def test_resolution_order():
    assert resolve_template("my {file}", {"DJX_EDITOR": "x"}, which_of("zed")) == "my {file}"
    assert resolve_template(None, {"DJX_EDITOR": "x {file}"}, which_of("zed")) == "x {file}"
    assert resolve_template(None, {}, which_of("zed", "code")) == "zed {file}:{line}"
    assert resolve_template(None, {}, which_of("zeditor", "code")) == "zeditor {file}:{line}"
    assert resolve_template(None, {}, which_of("code")) == "code -g {file}:{line}"
    assert resolve_template(None, {"EDITOR": "nvim"}, which_of("nvim")) == "nvim +{line} {file}"
    assert resolve_template(None, {"EDITOR": "nvim -f"}, which_of("nvim")) == "nvim -f +{line} {file}"
    assert resolve_template(None, {"EDITOR": "nvim"}, which_of()) is None
    assert resolve_template(None, {}, which_of()) is None


def test_default_argv_for_zed(popen):
    source = {"file": "/proj/shop/api/products.py", "line": 18}
    result = open_in_editor(source, "/proj", env={}, which=which_of("zed"))
    assert result.ok
    assert popen.calls[0][0] == ["zed", "/proj/shop/api/products.py:18"]
    assert result.message == "Opened shop/api/products.py:18 in zed"


# ---- launch rules ----


def test_launch_is_detached_and_shellless(popen):
    open_in_editor({"file": "/p/a b.py", "line": 2}, "/p", ZED)
    argv, kwargs = popen.calls[0]
    assert isinstance(argv, list)
    assert "shell" not in kwargs
    assert kwargs["stdin"] == kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
    assert kwargs["start_new_session"] is True


def test_missing_editor_message_includes_path_and_line():
    result = open_in_editor(
        {"file": "/proj/shop/models.py", "line": 12}, "/proj", env={}, which=which_of()
    )
    assert not result.ok
    assert result.message.splitlines() == [jump.NO_EDITOR, "shop/models.py:12"]


def test_null_source_message(popen):
    result = open_in_editor({"file": None, "line": None}, "/proj", ZED)
    assert (result.ok, result.message) == (False, "No source location")
    assert popen.calls == []


def test_launch_error_becomes_message(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError(2, "No such file or directory: 'zed'")

    monkeypatch.setattr(jump.subprocess, "Popen", boom)
    result = open_in_editor({"file": "/p/a.py", "line": 1}, "/p", ZED)
    assert not result.ok and result.message.startswith("Could not launch zed:")


def test_bad_template_becomes_message(popen):
    result = open_in_editor({"file": "/p/a.py", "line": 1}, "/p", 'zed "{file}')
    assert not result.ok and "Bad editor template" in result.message


def test_apps_open_their_init_module():
    app = {"label": "shop", "path": "/proj/shop"}
    assert source_of_item(3, app) == {"file": "/proj/shop/__init__.py", "line": 1}


# ---- in the app ----


def make_app(envelope=None):
    return DjxApp(FakeEngineClient(envelope), editor=ZED)


async def test_o_on_an_endpoint_calls_the_launcher(popen, toasts):
    app = make_app()
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("slash")
        await pilot.press(*"get_product")
        await pilot.press("enter")
        await settle(pilot)
        await pilot.press("o")
        argv = popen.calls[-1][0]
        assert argv == ["zed", "/repo/sandbox/shop/api/products.py:18"]
        assert toasts[-1] == ("Opened shop/api/products.py:18 in zed", "information")


@pytest.mark.parametrize("size", [(140, 40), (50, 30)], ids=["wide", "50-columns"])
async def test_o_works_in_all_five_sections(popen, toasts, size):
    app = make_app()
    async with app.run_test(size=size) as pilot:
        await settle(pilot)
        for key in "12345":
            await pilot.press(key)
            await settle(pilot)
            before = len(popen.calls)
            await pilot.press("o")
            assert len(popen.calls) == before + 1, f"section {key}"
            argv = popen.calls[-1][0]
            expected = source_of_item(app.section, app.djx_selected_item)
            assert argv == ["zed", f"{expected['file']}:{expected['line']}"]
            assert argv[1].startswith("/")  # absolute path goes to the editor


async def test_enter_opens_on_wide_but_drills_on_narrow(popen, toasts):
    app = make_app()
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("enter")
        assert len(popen.calls) == 1
    app = make_app()
    async with app.run_test(size=(50, 30)) as pilot:
        await settle(pilot)
        await pilot.press("enter")
        await settle(pilot)
        assert popen.calls[1:] == [] and app.drilled
        await pilot.press("enter")  # in the detail view, Enter opens
        assert len(popen.calls) == 2


async def test_enter_on_a_relation_follows_it_instead_of_opening(popen, toasts):
    app = make_app()
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("2")
        await pilot.press("slash")
        await pilot.press(*"shop.product")
        await pilot.press("enter")
        await settle(pilot)
        await pilot.press("l")
        await pilot.press("enter")
        await settle(pilot)
        assert app.djx_selected_key == "shop.Category"
        assert popen.calls == []
        await pilot.press("o")
        assert len(popen.calls) == 1


async def test_null_source_shows_a_toast(popen, toasts):
    envelope = fixture_envelope()
    for endpoint in envelope.data["endpoints"]:
        endpoint["source"] = {"file": None, "line": None}
    app = make_app(envelope)
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("o")
        assert toasts[-1] == ("No source location", "warning")
        assert popen.calls == []


async def test_missing_editor_shows_a_toast(popen, toasts, monkeypatch):
    monkeypatch.delenv("DJX_EDITOR", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(jump.shutil, "which", lambda name: None)
    app = DjxApp(FakeEngineClient())  # no --editor
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("o")
        message, severity = toasts[-1]
        assert message.startswith("No editor found. Set --editor or DJX_EDITOR.")
        assert message.splitlines()[1].startswith("shop/") or ".py:" in message
        assert severity == "warning"
        assert popen.calls == []


async def test_launch_failure_is_a_toast_not_a_crash(toasts, monkeypatch):
    def boom(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(jump.subprocess, "Popen", boom)
    app = make_app()
    async with app.run_test(size=(140, 40)) as pilot:
        await settle(pilot)
        await pilot.press("o")
        assert toasts[-1][0].startswith("Could not launch zed:")
        assert toasts[-1][1] == "error"
        assert app.is_running
