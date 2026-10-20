"""Where does this object live in the user's code, and is that code local or third party."""

from __future__ import annotations

import functools
import inspect
import os
from pathlib import Path
from typing import Any

from djx_engine import bootstrap
from djx_engine.contract import Source


def unwrap(obj: Any) -> Any:
    """Peel partials, Django `view_class`, and `functools.wraps` layers."""
    for _ in range(20):
        if isinstance(obj, functools.partial):
            obj = obj.func
        elif getattr(obj, "view_class", None) is not None:
            obj = obj.view_class
        elif getattr(obj, "__wrapped__", None) is not None:
            obj = obj.__wrapped__
        elif inspect.ismethod(obj):
            obj = obj.__func__
        else:
            break
    return obj


def source_of(obj: Any) -> Source:
    """Never raises. Returns nulls when the location cannot be found."""
    try:
        target = unwrap(obj)
        file = inspect.getsourcefile(target)
        if file is None:
            return {"file": None, "line": None}
        _, line = inspect.getsourcelines(target)
        return {"file": os.path.abspath(file), "line": int(line) or 1}
    except (TypeError, OSError, ValueError):
        return {"file": None, "line": None}


def app_origin(name: str, path: str | None) -> str:
    """'django' for django.*, 'local' for code under the project root, else 'third_party'."""
    if name.startswith("django."):
        return "django"
    root = bootstrap.PROJECT_ROOT
    if root is not None and path:
        resolved = Path(path).resolve()
        in_site_packages = any(p in ("site-packages", "dist-packages") for p in resolved.parts)
        if resolved.is_relative_to(root) and not in_site_packages:
            return "local"
    return "third_party"
