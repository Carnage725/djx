"""JSON contract between the engine and the UI. See docs/engine-contract.md.

Bump SCHEMA_VERSION whenever a field is renamed or removed.
"""

from __future__ import annotations

from typing import Any, TypedDict

SCHEMA_VERSION = 1


class Source(TypedDict):
    file: str | None
    line: int | None


class Project(TypedDict):
    root: str
    settings_module: str
    python: str
    django_version: str
    ninja_version: str | None


class Warning(TypedDict):
    collector: str
    message: str


class Data(TypedDict):
    apps: list[dict[str, Any]]
    models: list[dict[str, Any]]
    endpoints: list[dict[str, Any]]
    url_names: list[dict[str, Any]]
    commands: list[dict[str, Any]]


class SuccessEnvelope(TypedDict):
    schema_version: int
    ok: bool
    generated_at: str
    project: Project
    data: Data
    warnings: list[Warning]


class ErrorBody(TypedDict):
    type: str
    message: str
    hint: str
    traceback: str


class ErrorEnvelope(TypedDict):
    schema_version: int
    ok: bool
    error: ErrorBody


def error_envelope(type_: str, message: str, hint: str, traceback: str) -> ErrorEnvelope:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "error": {"type": type_, "message": message, "hint": hint, "traceback": traceback},
    }
