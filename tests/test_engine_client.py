import sys
from pathlib import Path

from djx.engine_client import EngineClient, collect, find_python

SANDBOX = Path(__file__).resolve().parents[1] / "sandbox"


def test_find_python_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("DJX_PYTHON", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert find_python(tmp_path) == sys.executable
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()
    assert find_python(tmp_path) == str(venv_python)
    other_venv = tmp_path / "other"
    (other_venv / "bin").mkdir(parents=True)
    (other_venv / "bin" / "python").touch()
    monkeypatch.setenv("VIRTUAL_ENV", str(other_venv))
    assert find_python(tmp_path / "empty") == str(other_venv / "bin" / "python")
    monkeypatch.setenv("DJX_PYTHON", "/env/python")
    assert find_python(tmp_path) == "/env/python"
    assert find_python(tmp_path, "/flag/python") == "/flag/python"


def test_collect_sandbox():
    envelope = collect(SANDBOX, sys.executable)
    assert envelope.ok
    assert envelope.project["settings_module"] == "config.settings"
    assert envelope.data["endpoints"]


def test_engine_error_becomes_error_envelope():
    envelope = collect(SANDBOX, sys.executable, "config.settings_broken")
    assert not envelope.ok
    assert envelope.error["type"] == "ModuleNotFoundError"
    assert "config.settings_broken" in envelope.error["hint"]


def test_missing_python_becomes_error_envelope():
    envelope = collect(SANDBOX, "/no/such/python")
    assert not envelope.ok
    assert envelope.error["type"] == "EngineLaunchError"


def test_python_without_django_gives_hint(tmp_path):
    fake = tmp_path / "py"
    fake.write_text("#!/bin/sh\necho 'boom on stderr' >&2\nexit 1\n")
    fake.chmod(0o755)
    envelope = collect(SANDBOX, str(fake))
    assert not envelope.ok
    assert envelope.error["type"] == "EngineOutputError"
    assert "boom on stderr" in envelope.error["traceback"]


def test_reverse_and_resolve_through_client():
    client = EngineClient(SANDBOX, sys.executable)
    reversed_ = client.reverse("blog:post-detail", kwargs={"slug": "hello"})
    assert reversed_.ok and reversed_.data["url"] == "/blog/hello/"
    resolved = client.resolve("/api/v1/health")
    assert resolved.ok and resolved.data["view"] == "config.api.health"
    assert not client.reverse("nope").ok
