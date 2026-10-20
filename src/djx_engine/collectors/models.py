from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db.models import NOT_PROVIDED

from djx_engine.sources import app_origin, source_of

RELATION_KINDS = (("many_to_many", "m2m"), ("one_to_one", "o2o"), ("many_to_one", "fk"))


def _default(field: Any) -> str | None:
    default = getattr(field, "default", NOT_PROVIDED)
    if default is NOT_PROVIDED:
        return None
    if callable(default):  # never call it
        return f"<{getattr(default, '__qualname__', type(default).__name__)}>"
    return repr(default)[:200]


def _relation(field: Any) -> dict[str, Any] | None:
    if not field.is_relation or field.related_model is None:
        return None
    for attr, kind in RELATION_KINDS:
        if getattr(field, attr, False):
            break
    else:
        return None
    remote = field.remote_field
    through = getattr(remote, "through", None)
    explicit_through = through is not None and not through._meta.auto_created
    return {
        "kind": kind,
        "to": field.related_model._meta.label,
        "on_delete": None if kind == "m2m" else remote.on_delete.__name__,
        "related_name": remote.related_name,
        "through": through._meta.label if explicit_through else None,
    }


def _field(field: Any) -> dict[str, Any]:
    return {
        "name": field.name,
        "column": getattr(field, "column", None),
        "type": type(field).__name__,
        "null": bool(getattr(field, "null", False)),
        "blank": bool(getattr(field, "blank", False)),
        "unique": bool(getattr(field, "unique", False)),
        "primary_key": bool(getattr(field, "primary_key", False)),
        "max_length": getattr(field, "max_length", None),
        "has_choices": bool(getattr(field, "choices", None)),
        "default": _default(field),
        "help_text": str(getattr(field, "help_text", "")),
        "relation": _relation(field),
    }


def _reverse_relations(opts: Any) -> list[dict[str, Any]]:
    result = []
    for rel in opts.get_fields():
        if not (rel.auto_created and not rel.concrete and rel.is_relation):
            continue
        name = rel.get_accessor_name()
        if name is None:  # related_name ends with "+"
            continue
        kind = "m2m" if rel.many_to_many else "o2o" if rel.one_to_one else "fk"
        result.append(
            {"name": name, "kind": kind, "from": rel.related_model._meta.label, "field": rel.field.name}
        )
    return sorted(result, key=lambda r: (r["from"], r["name"]))


def collect_models() -> list[dict[str, Any]]:
    result = []
    for model in apps.get_models():
        opts = model._meta
        forward = [f for f in opts.get_fields() if not f.auto_created or f.concrete]
        result.append(
            {
                "label": opts.label,
                "app": opts.app_label,
                "name": model.__name__,
                "db_table": opts.db_table,
                "verbose_name": str(opts.verbose_name),
                "pk": opts.pk.name if opts.pk else None,
                "ordering": [str(o) for o in opts.ordering],
                "proxy": opts.proxy,
                "proxy_for": opts.proxy_for_model._meta.label if opts.proxy else None,
                "origin": app_origin(opts.app_config.name, opts.app_config.path),
                "fields": [_field(f) for f in forward],
                "reverse_relations": _reverse_relations(opts),
                "source": source_of(model),
            }
        )
    return sorted(result, key=lambda m: m["label"])
