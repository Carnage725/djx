"""Everything that reads django-ninja INTERNALS lives in this file.

Ninja has no public API to list the operations behind a Django URL pattern, so this relies on
private details. Tested with django-ninja 1.7.1 (see TESTED_NINJA_VERSION):

- Ninja hands Django a closure (`sync_view_wrapper` / `async_view_wrapper`) that captures its
  `ninja.operation.PathView` as `self`. Older versions used a bound method; both are handled.
- `Router.urls_paths` yields one URLPattern per operation, in the order of `PathView.operations`,
  all sharing one PathView. So the Nth pattern of a PathView belongs to its Nth operation.

Safety net: after matching, the operation count per API is compared with Ninja's PUBLIC
`NinjaAPI.get_openapi_schema()`. A mismatch becomes a warning, and
tests/engine/test_ninja_canary.py fails loudly when the sandbox stops yielding 12 + 2 operations.
"""

from __future__ import annotations

from importlib import metadata
from typing import Any

TESTED_NINJA_VERSION = "1.7.1"

_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def path_view_class() -> Any:
    try:
        from ninja.operation import PathView
    except ImportError:
        return None
    return PathView


def find_path_view(callback: Any, view_class: Any = None) -> Any:
    view_class = view_class or path_view_class()
    if view_class is None:
        return None
    owner = getattr(callback, "__self__", None)
    if isinstance(owner, view_class):
        return owner
    for cell in getattr(callback, "__closure__", None) or ():
        try:
            value = cell.cell_contents
        except ValueError:  # empty cell
            continue
        if isinstance(value, view_class):
            return value
    return None


def _ninja_version() -> str:
    try:
        return metadata.version("django-ninja")
    except metadata.PackageNotFoundError:
        return "unknown"


def _is_ninja_operation_view(callback: Any) -> bool:
    """A callback from ninja's operation machinery (not its docs/openapi views)."""
    module = getattr(callback, "__module__", None) or ""
    return module.startswith("ninja.") and not module.startswith("ninja.openapi")


class NinjaMatcher:
    """Maps URL patterns to Ninja operations and checks the result."""

    def __init__(self) -> None:
        self._view_class = path_view_class()
        self._counters: dict[int, int] = {}
        self._operations: list[Any] = []
        self._unrecognised = 0

    def operation_for(self, callback: Any) -> Any:
        """The Ninja operation behind this URL pattern, or None for a plain Django view."""
        path_view = find_path_view(callback, self._view_class)
        if path_view is None:
            if _is_ninja_operation_view(callback):
                self._unrecognised += 1
            return None
        index = self._counters.get(id(path_view), 0)
        self._counters[id(path_view)] = index + 1
        if index >= len(path_view.operations):
            return None
        operation = path_view.operations[index]
        self._operations.append(operation)
        return operation

    def warnings(self) -> list[str]:
        version = _ninja_version()
        if self._unrecognised and not self._operations:
            message = (
                f"Ninja {version} detected but its internals were not recognised; "
                "Ninja routes are shown as plain Django endpoints."
            )
            return [message]
        return self._openapi_mismatches(version)

    def _openapi_mismatches(self, version: str) -> list[str]:
        by_api: dict[int, tuple[Any, list[Any]]] = {}
        for operation in self._operations:
            if operation.api is not None:
                by_api.setdefault(id(operation.api), (operation.api, []))[1].append(operation)
        messages = []
        for api, operations in by_api.values():
            found = sum(len(op.methods) for op in operations if op.include_in_schema)
            label = f"{api.title} {api.version}"
            try:
                paths = api.get_openapi_schema()["paths"]
            except Exception as exc:  # noqa: BLE001 - a broken schema must not break the explorer
                messages.append(f"Ninja {version}: could not read the OpenAPI schema for {label}: {exc}")
                continue
            documented = sum(1 for item in paths.values() for m in item if m in _HTTP_METHODS)
            if found != documented:
                messages.append(
                    f"Ninja {version}: found {found} operations, "
                    f"OpenAPI says {documented} for {label}"
                )
        return messages
