# Engine contract

`python -m djx_engine <command>` prints exactly one JSON document to stdout. Logs and anything user code prints go to stderr. Exit code `0` on success, `2` on error. Types live in `src/djx_engine/contract.py`.

`schema_version` is `1`. Renaming or removing a field bumps it.

## Commands

| Command | Args | Result |
|---|---|---|
| `collect` | `--root PATH [--settings MOD]` | success envelope |
| `reverse` | `--root PATH --name NAME [--arg V ...] [--kwarg K=V ...]` | stub: error envelope `NotImplemented` |
| `resolve` | `--root PATH --path /url/` | stub: error envelope `NotImplemented` |

Settings module: `--settings` > `DJANGO_SETTINGS_MODULE` env > `os.environ.setdefault(...)` in `manage.py`.

## Success envelope

```json
{
  "schema_version": 1,
  "ok": true,
  "generated_at": "2026-01-01T00:00:00+00:00",
  "project": {
    "root": "/abs/path",
    "settings_module": "config.settings",
    "python": "/abs/path/to/python",
    "django_version": "6.1.2",
    "ninja_version": "1.7.1"
  },
  "data": { "apps": [], "models": [], "endpoints": [], "url_names": [], "commands": [] },
  "warnings": [{ "collector": "models", "message": "..." }]
}
```

`ninja_version` is `null` when django-ninja is not installed. A failing collector yields `[]` plus one warning; the others still run. Collectors that are not implemented yet (`endpoints`, `url_names`) return `[]`.

## `data.apps[]`

```json
{ "label": "shop", "name": "shop", "verbose_name": "Shop", "path": "/abs/shop",
  "origin": "local", "model_count": 6, "command_count": 2 }
```

`origin`: `"django"` if the app name starts with `django.`; `"local"` if its path is under the project root and not in `site-packages`; else `"third_party"`. Order follows `INSTALLED_APPS`.

## `data.models[]`

Sorted by `label`. Abstract models are absent. Never touches the database.

```json
{
  "label": "shop.Product", "app": "shop", "name": "Product", "db_table": "shop_product",
  "verbose_name": "product", "pk": "id", "ordering": [], "proxy": false, "proxy_for": null,
  "origin": "local",
  "fields": [{
    "name": "category", "column": "category_id", "type": "ForeignKey",
    "null": false, "blank": false, "unique": false, "primary_key": false,
    "max_length": null, "has_choices": false, "default": null, "help_text": "",
    "relation": { "kind": "fk", "to": "shop.Category", "on_delete": "CASCADE",
                  "related_name": "products", "through": null }
  }],
  "reverse_relations": [{ "name": "items", "kind": "fk", "from": "shop.OrderItem", "field": "order" }],
  "source": { "file": "/abs/shop/models.py", "line": 12 }
}
```

- `fields` includes m2m fields (`column` is `null`). Proxy models list the concrete model's fields.
- `relation` is `null` for non-relation fields. `kind` is `fk`, `o2o` or `m2m`. `on_delete` is `null` for m2m. `related_name` is the declared value (`null` if not declared). `through` is set only for an explicit through model, `null` for auto-created ones.
- `default` is `null` for no default, `"<qualified name>"` for callables (never called), else `repr(default)` cut to 200 chars.
- `reverse_relations` skips relations hidden with `related_name="+"`. `name` is the accessor name.

## `data.commands[]`

Local commands first, then third-party, then Django built-ins; each group sorted by name.

```json
{ "name": "seed_shop", "app": "shop", "origin": "local", "help": "...",
  "source": { "file": "/abs/shop/management/commands/seed_shop.py", "line": 9 } }
```

`app` is the app label, or the raw module name (`django.core`) for commands not owned by an installed app. `source` points at the `Command` class. If a command fails to load it is kept with `help: ""` and a warning.

## `source_of` rules

Unwraps `functools.partial`, Django `view_class`, `__wrapped__` and bound methods before looking up the file and line. Returns `{"file": null, "line": null}` instead of raising.

## Error envelope (exit code 2)

```json
{
  "schema_version": 1,
  "ok": false,
  "error": {
    "type": "ModuleNotFoundError",
    "message": "No module named 'x'",
    "hint": "Could not import settings module config.settings_broken",
    "traceback": "<full traceback string>"
  }
}
```

Bootstrap error types raised by the engine itself: `ProjectNotFound`, `SettingsNotFound`, `NotImplemented`. Otherwise `type` is the exception class name.

## Shared `source` object

```json
{ "file": "/abs/path.py" , "line": 42 }
```

Both fields are `null` when unknown.

## Launcher

`djx_engine.launcher.run_cmd(python, argv)` returns `[python, "-c", <bootstrap>, *argv]`. The bootstrap loads `djx_engine` from its file location, so the engine's parent directory is never added to `sys.path`.
