# Engine contract

`python -m djx_engine <command>` prints exactly one JSON document to stdout. Logs and anything user code prints go to stderr. Exit code `0` on success, `2` on error. Types live in `src/djx_engine/contract.py`.

`schema_version` is `1`. Renaming or removing a field bumps it.

## Commands

| Command | Args | Result |
|---|---|---|
| `collect` | `--root PATH [--settings MOD]` | success envelope |
| `reverse` | `--root PATH --name NAME [--arg V ...] [--kwarg K=V ...]` | `{schema_version, ok: true, data: {url}}` or error envelope (`NoReverseMatch`) |
| `resolve` | `--root PATH --path /url/` | `{schema_version, ok: true, data: {view, url_name, kwargs, methods, source}}` or error envelope (`Resolver404`) |

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

`ninja_version` is `null` when django-ninja is not installed. A failing collector yields `[]` plus one warning; the others still run.
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

## `data.endpoints[]`

Sorted by `kind`, `path`, first method.

```json
{
  "id": "ninja:api-v1:GET:/api/v1/products/{product_id}",
  "kind": "ninja",
  "methods": ["GET"],
  "path": "/api/v1/products/{product_id}",
  "route": "/api/v1/products/<int:product_id>",
  "url_name": "api-v1:get_product",
  "view": "shop.api.products.get_product",
  "summary": "Fetch one product.",
  "tags": ["products"],
  "api": { "title": "Shop API", "version": "1.0.0", "namespace": "api-v1" },
  "is_async": false,
  "signature": "(request, product_id: int)",
  "origin": "local",
  "source": { "file": "/abs/shop/api/products.py", "line": 18 }
}
```

- `kind` is `"ninja"` or `"django"`. Ninja paths expand to one endpoint per operation and method. `id` is `django:<METHODS or ANY>:<path>` for Django views.
- `methods` is `[]` for Django function views (any method). For class-based views it lists the HTTP methods the class defines.
- `route` is the concatenated Django route with a leading `/`; regex anchors are removed. `path` is the display form: `<conv:name>`, `<name>` and `(?P<name>...)` become `{name}`.
- `url_name` includes namespaces (`blog:post-detail`).
- `summary`: Ninja summary if set explicitly, else the first line of the view's own docstring (never inherited), else `""`.
- `api` is `null` for Django views. Django-ninja's own docs/openapi URLs are listed as `django` endpoints.
- `origin` (also on `url_names[]`) comes from the real, unwrapped view: module `django.*` -> `"django"`; module `ninja.*` or a file inside `site-packages` -> `"third_party"`; a file under the project root -> `"local"`; anything else -> `"third_party"`. Ninja operations are judged by their own function, so operations written in the project are `"local"` while Ninja's docs/openapi URLs are `"third_party"`.
- Class-based views: `view` and `source` point at the class.
- Ninja: django-ninja 1.7 gives Django a closure that captures its `PathView`, and creates one URL pattern per operation. The engine finds the `PathView` in the closure (bound methods are also supported) and maps the Nth pattern of a `PathView` to its Nth operation.

## `data.url_names[]`

Every named pattern, namespaced names included (Ninja operations too). Sorted by name.

```json
{ "name": "blog:post-detail", "namespace": "blog", "route": "/blog/<slug:slug>/",
  "args": ["slug"], "unnamed_groups": 0, "view": "blog.views.PostDetailView",
  "origin": "local",
  "source": { "file": "/abs/blog/views.py", "line": 14 } }
```

`unnamed_groups` counts unnamed regex groups over all levels (`0` for route patterns); a reverse form cannot fill those, use `resolve`. `namespace` is `null` without one. `args` are the group names of every level, outermost first. For regex routes `route` is the concatenated regex (not a Django route string) with the `^` and `$` anchors removed, so `args` and `unnamed_groups` describe it.

## `reverse` and `resolve` output

`reverse --name blog:post-detail --kwarg slug=hello` gives `{"data": {"url": "/blog/hello/"}}`. `resolve --path /blog/hello/` gives `view` (dotted path of the unwrapped callable), `url_name` (with namespaces), `kwargs`, `methods` (Ninja only, all methods on that path) and `source`. For a Ninja path with several operations, `view` is the first operation, matching the pattern Django picks.

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

Error types raised by the engine itself: `ProjectNotFound`, `SettingsNotFound`, `NoReverseMatch`, `Resolver404`, `ValueError` (both `--arg` and `--kwarg` given). Otherwise `type` is the exception class name.

## Shared `source` object

```json
{ "file": "/abs/path.py" , "line": 42 }
```

Both fields are `null` when unknown.

## Launcher

`djx_engine.launcher.run_cmd(python, argv)` returns `[python, "-c", <bootstrap>, *argv]`. The bootstrap loads `djx_engine` from its file location, so the engine's parent directory is never added to `sys.path`.
