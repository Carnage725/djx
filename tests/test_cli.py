import json
import sys
from pathlib import Path

import pytest

from djx import __version__, cli
from djx.engine_client import find_python_with_source

SANDBOX = Path(__file__).resolve().parents[1] / "sandbox"


@pytest.fixture(autouse=True)
def no_editor_env(monkeypatch):
    monkeypatch.delenv("DJX_EDITOR", raising=False)
    monkeypatch.delenv("DJX_PYTHON", raising=False)


def test_version(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["--version"])
    assert exit_.value.code == 0
    assert capsys.readouterr().out.strip() == f"djx {__version__}"


def test_json_returns_ok_true(capsys):
    assert cli.main(["--json", str(SANDBOX)]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["ok"] is True
    assert document["project"]["settings_module"] == "config.settings"
    assert document["data"]["endpoints"]


def test_json_walks_up_to_manage_py(capsys):
    assert cli.main(["--json", str(SANDBOX / "shop" / "api")]) == 0
    assert json.loads(capsys.readouterr().out)["project"]["root"] == str(SANDBOX)


def test_json_engine_error_exits_2_with_valid_json(capsys):
    code = cli.main(["--json", str(SANDBOX), "--settings", "config.settings_broken"])
    assert code == 2
    document = json.loads(capsys.readouterr().out)
    assert document["ok"] is False
    assert "config.settings_broken" in document["error"]["hint"]


def test_doctor_on_sandbox_is_green(capsys):
    assert cli.main(["doctor", str(SANDBOX)]) == 0
    out = capsys.readouterr().out
    for expected in (
        "Project root:",
        "Python:",
        "Settings module: config.settings (from manage.py)",
        "Django version:",
        "Ninja version:",
        "Engine ran OK in",
        "Warnings: 0",
        "Editor:",
        "All good.",
    ):
        assert expected in out
    assert "[FAIL]" not in out


def test_doctor_on_empty_dir_is_friendly(tmp_path, capsys):
    assert cli.main(["doctor", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "no manage.py" in out and "fix:" in out
    assert "Traceback" not in out


def test_doctor_reports_broken_settings_with_a_fix(capsys):
    code = cli.main(["doctor", str(SANDBOX), "--settings", "config.settings_broken"])
    out = capsys.readouterr().out
    assert code == 1
    assert "[FAIL]" in out and "Could not import settings module config.settings_broken" in out
    assert "Traceback" not in out


def test_doctor_reports_missing_python(capsys):
    code = cli.main(["doctor", str(SANDBOX), "--python", "/no/such/python"])
    out = capsys.readouterr().out
    assert code == 1
    assert "/no/such/python" in out and "--python or DJX_PYTHON" in out


def test_doctor_warns_but_passes_without_an_editor(capsys, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    monkeypatch.delenv("EDITOR", raising=False)
    # `which` is only used for the editor and python lookups; the sandbox python is a real path
    assert cli.main(["doctor", str(SANDBOX)]) == 0
    assert "[warn] Editor: none found" in capsys.readouterr().out


def test_no_project_is_a_friendly_message_not_a_traceback(tmp_path, capsys):
    assert cli.main([str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "no manage.py found" in err and "Traceback" not in err
    assert cli.main(["--json", str(tmp_path)]) == 2


def test_ui_launch_wires_flags_into_the_app(monkeypatch):
    seen = {}

    def fake_run(self):
        seen["client"] = self.client
        seen["editor"] = self.djx_editor

    monkeypatch.setattr("djx.app.DjxApp.run", fake_run)
    code = cli.main(
        [str(SANDBOX), "--python", sys.executable, "--settings", "x.y", "--editor", "ed {file}"]
    )
    assert code == 0
    assert seen["client"].root == SANDBOX
    assert seen["client"].python == sys.executable
    assert seen["client"].settings == "x.y"
    assert seen["editor"] == "ed {file}"


def test_two_paths_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_:
        cli.main(["a", "b"])
    assert exit_.value.code == 2


def test_python_is_found_in_a_parent_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()
    project = tmp_path / "backend" / "app"
    project.mkdir(parents=True)
    python, how = find_python_with_source(project)
    assert python == str(venv_python) and how.startswith(".venv in")
