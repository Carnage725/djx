"""The `djx` command: launch the UI, dump engine JSON, or run `djx doctor`."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from djx import __version__
from djx.engine_client import (
    EngineClient,
    base_args,
    collect,
    find_python_with_source,
    run_json,
)
from djx.jump import resolve_template
from djx_engine.bootstrap import EngineError, detect_settings_source

NO_PROJECT_HINT = "Run djx inside a Django project, or pass the project folder: djx path/to/project"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="djx",
        description="Explore a Django + Django Ninja project in the terminal.",
        epilog="djx doctor [PATH]  checks your setup and says how to fix what is wrong.",
    )
    parser.add_argument("targets", nargs="*", metavar="PATH", help="project folder (default: .)")
    parser.add_argument("--python", help="Python of the project (default: auto-detected)")
    parser.add_argument("--settings", help="settings module (default: read from manage.py)")
    parser.add_argument("--editor", help='editor command, e.g. "zed {file}:{line}"')
    parser.add_argument("--json", action="store_true", help="print the raw engine JSON and exit")
    parser.add_argument("--version", action="version", version=f"djx {__version__}")
    return parser


def find_project_root(path: str | None) -> Path | None:
    """The folder with manage.py: PATH itself, or the nearest parent of it."""
    start = Path(path or ".").expanduser().resolve()
    if start.is_file():
        start = start.parent
    for folder in [start, *start.parents]:
        if (folder / "manage.py").is_file():
            return folder
    return None


def _no_project(path: str | None) -> int:
    start = Path(path or ".").expanduser().resolve()
    print(f"djx: no manage.py found in {start} or any parent folder.", file=sys.stderr)
    print(f"     {NO_PROJECT_HINT}", file=sys.stderr)
    return 2


class Report:
    """A plain checklist. Every failure carries a one-line fix."""

    def __init__(self) -> None:
        self.broken = False

    def ok(self, text: str) -> None:
        print(f"[ ok ] {text}")

    def warn(self, text: str, fix: str) -> None:
        print(f"[warn] {text}")
        print(f"       fix: {fix}")

    def fail(self, text: str, fix: str) -> None:
        self.broken = True
        print(f"[FAIL] {text}")
        print(f"       fix: {fix}")


def run_doctor(path: str | None, args: argparse.Namespace) -> int:
    report = Report()
    root = find_project_root(path)
    if root is None:
        start = Path(path or ".").expanduser().resolve()
        report.fail(f"Project root: no manage.py in {start} or any parent folder", NO_PROJECT_HINT)
        print("\nSomething is broken. See the fix lines above.")
        return 1
    report.ok(f"Project root: {root}")

    python, how = find_python_with_source(root, args.python)
    if Path(python).exists() or shutil.which(python):
        report.ok(f"Python: {python} ({how})")
    else:
        report.fail(f"Python: {python} ({how}) does not exist", "Fix --python or DJX_PYTHON.")

    try:
        module, source = detect_settings_source(root, args.settings)
        report.ok(f"Settings module: {module} (from {source})")
    except EngineError as exc:
        report.fail(f"Settings module: {exc.message}", exc.hint)

    started = time.perf_counter()
    envelope = collect(root, python, args.settings)
    elapsed = time.perf_counter() - started
    if not envelope.ok:
        error = envelope.error
        report.fail(f"Engine: {error['type']}: {error['message']}", error["hint"] or "Run `djx --json`.")
        detail = [line for line in error["traceback"].splitlines() if line.strip()][-1:]
        if detail:
            print(f"       detail: {detail[0].strip()}")
        report.fail("Django version: unknown (the engine did not run)", "Fix the engine error above.")
    else:
        project = envelope.project
        report.ok(f"Django version: {project['django_version']}")
        ninja = project["ninja_version"]
        report.ok(f"Ninja version: {ninja}" if ninja else "Ninja: not installed")
        report.ok(f"Engine ran OK in {elapsed:.2f}s")
        if envelope.warnings:
            report.warn(
                f"{len(envelope.warnings)} warnings from the engine",
                "Run djx and press w to read them, or `djx --json`.",
            )
            for warning in envelope.warnings:
                print(f"         - {warning['collector']}: {warning['message']}")
        else:
            report.ok("Warnings: 0")

    template = resolve_template(args.editor, os.environ, shutil.which)
    if template:
        report.ok(f"Editor: {template}")
    else:
        report.warn(
            "Editor: none found (opening code from djx will not work)",
            "Set DJX_EDITOR, e.g. DJX_EDITOR='zed {file}:{line}', or pass --editor.",
        )

    print("\nSomething is broken. See the fix lines above." if report.broken else "\nAll good.")
    return 1 if report.broken else 0


def run_json_mode(path: str | None, args: argparse.Namespace) -> int:
    root = find_project_root(path)
    if root is None:
        return _no_project(path)
    python, _ = find_python_with_source(root, args.python)
    document = run_json(python, base_args("collect", root, args.settings))
    print(json.dumps(document, indent=2))
    return 0 if document.get("ok") else 2


def run_ui(path: str | None, args: argparse.Namespace) -> int:
    root = find_project_root(path)
    if root is None:
        return _no_project(path)
    python, _ = find_python_with_source(root, args.python)
    from djx.app import (
        DjxApp,  # imported late: Textual is slow to import, and doctor does not need it
    )

    DjxApp(EngineClient(root, python, args.settings), args.editor).run()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    targets = list(args.targets)
    if targets and targets[0] == "doctor":
        if len(targets) > 2:
            parser.error("doctor takes at most one PATH")
        return run_doctor(targets[1] if len(targets) > 1 else None, args)
    if len(targets) > 1:
        parser.error("expected at most one PATH")
    path = targets[0] if targets else None
    return run_json_mode(path, args) if args.json else run_ui(path, args)


if __name__ == "__main__":
    sys.exit(main())
