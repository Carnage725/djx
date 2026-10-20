"""Run the engine against sandbox/ and write tests/fixtures/sandbox_collect.json.

UI tests read this file so they never need Django. Run: uv run python scripts/regen_fixture.py

The output is stable: `generated_at` is zeroed, `project.python` is fixed, and the repo's absolute path becomes "/repo",
so the file is identical on every machine.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "sandbox_collect.json"
ZERO_TIME = "1970-01-01T00:00:00+00:00"


def normalize(envelope: dict) -> str:
    project = {**envelope["project"], "python": "/repo/.venv/bin/python"}
    envelope = {**envelope, "generated_at": ZERO_TIME, "project": project}
    return json.dumps(envelope, indent=2).replace(str(REPO), "/repo") + "\n"


def collect() -> dict:
    sys.path.insert(0, str(REPO / "src"))
    from djx_engine.launcher import run_cmd

    cmd = run_cmd(sys.executable, ["collect", "--root", str(REPO / "sandbox")])
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    envelope = json.loads(proc.stdout)
    if not envelope["ok"]:
        sys.exit(f"engine failed: {envelope['error']['message']}\n{proc.stderr}")
    return envelope


def main() -> None:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(normalize(collect()), encoding="utf-8")
    print(f"wrote {FIXTURE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
