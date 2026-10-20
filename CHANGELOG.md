# Changelog

## 0.1.0

First release: a read-only explorer for Django and Django Ninja projects.

### Added

- **Engine** (`djx_engine`): runs in the project's own Python, asks the real Django (URL resolver, app registry, management registry) and prints one JSON document. Standard library plus the project's Django only; never opens a database connection or writes to the project. JSON contract documented in `docs/engine-contract.md` (`schema_version` 1).
- **Collectors**: apps, models (fields, relations, reverse relations), management commands, endpoints (Django URLs and every Django Ninja operation) and URL names. Each has an `origin` (`local`, `third_party`, `django`). A failing collector becomes a warning; the others still run.
- **`reverse` and `resolve`** engine commands.
- **Ninja safety net**: all Ninja-internals code lives in `collectors/ninja_introspect.py`; operation counts are cross-checked against Ninja's OpenAPI schema, and a canary test fails when a Ninja upgrade changes the internals.
- **Terminal UI** (Textual): Endpoints, Models, Apps, Commands and URLs sections with live search, a two-pane layout on wide terminals and a one-pane drill-in layout that works at 50 columns, an error screen with hint and traceback, a warnings list, and a help screen.
- **Cross-links**: follow a model relation or an app's models with Enter, go back with Backspace.
- **URLs section**: type URL arguments to see the reversed path; type a path to see which view handles it.
- **Jump to code**: `o` (and Enter on a wide list) opens the selected item's source in Zed, VS Code or any editor template.
- **CLI**: `djx [PATH]`, `djx --json`, `djx doctor`, `djx --version`; flags `--python`, `--settings`, `--editor`.
- **Sandbox** Django + Ninja project full of edge cases, used by the tests.

### Notes

- djx looks for the project's Python in `--python`, `DJX_PYTHON`, a `.venv` in the project folder or any parent folder, `$VIRTUAL_ENV`, then its own Python.
- Keys pressed while the engine is still loading (for example `?` or `q`) work; the search boxes only become active once data has loaded.

### Not included

Running the server, tests or a shell; trying endpoints; anything that touches the database; live-server hooks; middleware, signals and permissions maps; an MCP server.
