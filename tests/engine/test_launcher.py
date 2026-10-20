import json
import subprocess
import sys
from pathlib import Path

from djx_engine.launcher import run_cmd

SANDBOX = Path(__file__).resolve().parents[2] / "sandbox"


def run(*argv):
    cmd = run_cmd(sys.executable, list(argv))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def test_collect_sandbox_returns_envelope():
    code, env = run("collect", "--root", str(SANDBOX))
    assert code == 0
    assert env["schema_version"] == 1 and env["ok"] is True
    assert env["project"]["settings_module"] == "config.settings"
    assert env["project"]["root"] == str(SANDBOX)
    assert env["project"]["django_version"]
    assert set(env["data"]) == {"apps", "models", "endpoints", "url_names", "commands"}
    assert env["warnings"] == []


def test_broken_settings_gives_error_envelope():
    code, env = run("collect", "--root", str(SANDBOX), "--settings", "config.settings_broken")
    assert code == 2
    assert env["ok"] is False
    assert env["error"]["type"] == "ModuleNotFoundError"
    assert "config.settings_broken" in env["error"]["hint"]
    assert "this_module_does_not_exist" in env["error"]["traceback"]


def test_missing_root_gives_error_envelope(tmp_path):
    code, env = run("collect", "--root", str(tmp_path / "nope"))
    assert code == 2 and env["error"]["type"] == "ProjectNotFound"


def test_reverse_stub_is_error_envelope():
    code, env = run("reverse", "--root", str(SANDBOX), "--name", "home")
    assert code == 2 and env["ok"] is False
