import json
import subprocess
import sys
from pathlib import Path

import pytest

from djx_engine.launcher import run_cmd

SANDBOX = Path(__file__).resolve().parents[2] / "sandbox"


def run_engine(*argv):
    cmd = run_cmd(sys.executable, list(argv))
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return proc.returncode, proc.stdout, json.loads(proc.stdout)


def run_engine_raw(*argv):
    proc = subprocess.run(run_cmd(sys.executable, list(argv)), check=False, capture_output=True, text=True)
    return proc


@pytest.fixture(scope="session")
def collected():
    """One `collect` run against sandbox/, shared by all engine tests."""
    code, stdout, envelope = run_engine("collect", "--root", str(SANDBOX))
    assert code == 0, stdout
    return envelope


@pytest.fixture(scope="session")
def data(collected):
    return collected["data"]


@pytest.fixture(scope="session")
def models_by_label(data):
    return {m["label"]: m for m in data["models"]}


_TAIL = "from djx_engine.cli import main\nsys.exit(main(sys.argv[1:]))\n"


def run_with_driver(driver, *argv, cwd=None):
    """Run the engine like the launcher does, but run `driver` code before main().

    `driver` is Python source that may use `sys`, `main` and `djx_engine`.
    """
    cmd = run_cmd(sys.executable, list(argv))
    assert cmd[2].endswith(_TAIL)
    cmd[2] = cmd[2][: -len(_TAIL)] + "from djx_engine.cli import main\n" + driver + "\nsys.exit(main(sys.argv[1:]))\n"
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=cwd)
    return proc
