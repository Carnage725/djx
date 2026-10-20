# djx

A terminal app that shows your Django + Django Ninja project (endpoints, models, apps, management commands, URL names) and jumps to the code in Zed.

## Features (MVP1, read-only)

- **Endpoints**: Django URLs and every Django Ninja operation, grouped by API and path, with method badges and search.
- **Models**: fields, relations, and "referenced by"; follow a relation with Enter, go back with Backspace.
- **Apps** and **Commands**: local code first, framework items one key away.
- **URLs**: type arguments and see the reversed path; type a path and see which view handles it.
- **Jump to code**: `o` opens the selected item in Zed (or VS Code, or any editor you configure).
- Works in a narrow terminal: fully usable at 50 columns, so it fits in a Zed side panel.

djx never writes to your project and never touches your database.

## Install

From a clone of this repo:

```sh
uv tool install .      # or: pipx install .
```

For development: `uv sync`, then `uv run djx`.

## Quick start

```sh
cd path/to/your/django/project   # the folder with manage.py (a parent folder also works)
djx doctor                       # checks your setup, tells you how to fix problems
djx                              # opens the explorer
```

Or pass the folder: `djx path/to/project`. Try it on the bundled sample project: `uv run djx sandbox`.

## Key bindings

Press `?` in the app for the same list.

| Key | What it does |
|---|---|
| `1`-`5` | Endpoints, Models, Apps, Commands, URLs |
| `Tab` / `Shift-Tab` | Next / previous section |
| `/` | Search (filters as you type; several words must all match) |
| `Esc` | Clear search, leave a form or list, go back |
| `j` `k` / arrows | Move |
| `Enter` | Wide terminal: open in editor. Narrow terminal: show details (then Enter opens). |
| `o` | Open the selected item in your editor (always) |
| `b` | Show / hide framework items (Django built-ins, Ninja docs URLs, admin) |
| `l` / `→` | Models, Apps: focus the relation / model list. URLs: focus the args form |
| `Enter` on a relation | Go to that model |
| `Backspace` | Back after following a link |
| `p` | URLs: resolve a path |
| `r` | Refresh (re-runs the engine) |
| `w` | Warnings from the engine |
| `?` | Help |
| `q` | Quit |

With a window 100 columns or wider you get two panes (list and details). Narrower, you get one pane: Enter drills into the details and Esc goes back.

## Which Python does djx use?

djx must run the engine with **your project's Python**, because that is where Django lives. It picks the first of:

1. `--python PATH`
2. the `DJX_PYTHON` environment variable
3. a `.venv` folder in the project folder or in any parent folder
4. `$VIRTUAL_ENV`
5. the Python djx itself runs on (usually has no Django, so `djx doctor` will tell you)

## Configuration

| Flag | Environment variable | Meaning |
|---|---|---|
| `--python PATH` | `DJX_PYTHON` | Python of the project |
| `--settings MODULE` | `DJANGO_SETTINGS_MODULE` | Settings module. Default: read from `manage.py`. |
| `--editor TEMPLATE` | `DJX_EDITOR` | Editor command; `{file}` `{line}` `{col}` are filled in |
| `--json` | | Print the raw engine JSON and exit |
| `--version` | | Print the version |

Editor templates, for example: `zed {file}:{line}`, `code -g {file}:{line}`, `nvim +{line} {file}`. Without a flag or variable djx looks for `zed`, `zeditor`, `code`, then `$EDITOR`. Editors run detached, so use a graphical editor.

## Troubleshooting

Run `djx doctor` first. It prints a checklist; every `[FAIL]` line has a `fix:` line.

| Problem | What `djx doctor` says | Fix |
|---|---|---|
| Not in a project | `[FAIL] Project root: no manage.py in ... or any parent folder` | `cd` into the project or run `djx path/to/project` |
| Django is not in the Python djx chose | `[FAIL] Engine: ModuleNotFoundError: No module named 'django'`, `fix: Django is not importable from <python>. Point djx at the project's Python` | Activate the project's venv, or use `--python` / `DJX_PYTHON` |
| Settings module not found | `[FAIL] Settings module: Could not determine DJANGO_SETTINGS_MODULE.` | Pass `--settings`, or set `DJANGO_SETTINGS_MODULE` |
| Settings fail to import | `[FAIL] Engine: ... fix: Could not import settings module <name>` | Fix the import error shown; `djx --json` has the full traceback |
| Nothing opens when you press `o` | `[warn] Editor: none found` | Set `DJX_EDITOR` or pass `--editor` |

If the engine takes longer than 30 seconds, djx stops it and shows an `EngineTimeout` error: something in the project hangs when imported.

## Use with Zed

1. **Dock the terminal on the left.** In Zed's `settings.json`:

   ```json
   {
     "terminal": {
       "dock": "left"
     }
   }
   ```

2. **Add a task** that starts djx in a new terminal tab. Put it in your project's `.zed/tasks.json` (or in `~/.config/zed/tasks.json` for every project):

   ```json
   [
     {
       "label": "djx",
       "command": "djx",
       "use_new_terminal": true,
       "allow_concurrent_runs": true,
       "reveal": "always"
     }
   ]
   ```

   Run it with the `task: spawn` action. The task runs in the project root by default.

3. **Add a keybinding** in `keymap.json`, using the task's label:

   ```json
   [
     {
       "context": "Workspace",
       "bindings": {
         "alt-d": ["task::Spawn", { "task_name": "djx" }]
       }
     }
   ]
   ```

4. **Tip:** paths such as `shop/api/products.py:42` that djx prints can be opened from Zed's terminal with Cmd+Click (macOS) or Ctrl+Click (Linux/Windows). Pressing `o` in djx opens the same location.

This repo ships `.zed/tasks.json` with a task "djx (sandbox)" that runs `uv run djx sandbox`.

## How it works

djx is two Python packages. `djx_engine` runs inside **your project's Python** as a subprocess: it starts Django, asks the real URL resolver, app registry and management registry what exists, and prints exactly one JSON document to stdout (the contract is in [docs/engine-contract.md](docs/engine-contract.md)). It never parses your source to find routes, never opens a database connection and never writes to your project. `djx` is the Textual UI. It never imports Django: it runs the engine in a background worker and reads the JSON, so the screen stays responsive while a project loads.

Django Ninja has no public way to list the operations behind a URL, so the engine reads a few Ninja internals (`collectors/ninja_introspect.py`). It cross-checks the count against Ninja's OpenAPI schema and warns if they disagree, and a canary test fails if a Ninja upgrade changes them.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run python scripts/regen_fixture.py   # after changing the engine output
```

`sandbox/` is a sample Django + Ninja project full of edge cases; see its README.
