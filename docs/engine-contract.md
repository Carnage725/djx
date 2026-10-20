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

`ninja_version` is `null` when django-ninja is not installed. A failing collector yields `[]` plus one warning; the others still run. Collector item shapes are added here as each collector lands.

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
