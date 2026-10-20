"""Engine CLI. Prints exactly one JSON document to the real stdout; everything else is stderr."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

from djx_engine import bootstrap, collectors, diagnostics, lookup
from djx_engine.contract import SCHEMA_VERSION, error_envelope


def _kwarg(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"expected K=V, got {text!r}")
    return key, value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="djx_engine")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", required=True, help="directory containing manage.py")
    common.add_argument("--settings", help="settings module (overrides detection)")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("collect", parents=[common])

    rev = sub.add_parser("reverse", parents=[common])
    rev.add_argument("--name", required=True)
    rev.add_argument("--arg", action="append", default=[], metavar="V")
    rev.add_argument("--kwarg", action="append", default=[], type=_kwarg, metavar="K=V")

    res = sub.add_parser("resolve", parents=[common])
    res.add_argument("--path", required=True)
    return parser


def _collect(project: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    diagnostics.reset()
    for key, collector in collectors.COLLECTORS:
        try:
            data[key] = collector()
        except Exception as exc:  # noqa: BLE001 - one bad collector must not kill the rest
            data[key] = []
            diagnostics.warn(key, f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "project": project,
        "data": data,
        "warnings": diagnostics.WARNINGS,
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    project = bootstrap.setup(args.root, args.settings)
    if args.command == "collect":
        return _collect(project)
    if args.command == "reverse":
        return lookup.reverse_url(args.name, args.arg, args.kwarg)
    return lookup.resolve_path(args.path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    real_stdout = sys.stdout
    sys.stdout = sys.stderr  # user code may print() while we import it
    try:
        envelope = _run(args)
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - always emit an error envelope
        hint = exc.hint if isinstance(exc, bootstrap.EngineError) else ""
        message = exc.message if isinstance(exc, bootstrap.EngineError) else str(exc)
        envelope = error_envelope(type(exc).__name__, message, hint, traceback.format_exc())
        if isinstance(exc, bootstrap.EngineError):
            envelope["error"]["type"] = exc.type
        traceback.print_exc()
    finally:
        sys.stdout = real_stdout
    real_stdout.write(json.dumps(envelope, default=str) + "\n")
    real_stdout.flush()
    return 0 if envelope["ok"] else 2
