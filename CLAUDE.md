1. Think Before Coding
- State assumptions. If unsure or confused, stop and ask.
- If there are multiple interpretations, present them instead of picking silently.
- If a simpler approach exists, say so and push back when warranted.

2. Simplicity First
- Write the minimum code that solves the problem.
- No unrequested features, single-use abstractions, speculative configurability, or error handling for impossible cases.
- If 200 lines could be 50, rewrite it.

3. Surgical Changes
- Touch only what the request requires. Every changed line should trace back to it.
- Don't refactor, reformat, or "improve" adjacent code. Match existing style.
- Remove only the imports, variables, and functions your changes orphaned. Mention unrelated dead code instead of deleting it.

4. Goal-Driven Execution
- Turn tasks into verifiable goals: "fix the bug" becomes "write a reproducing test, then make it pass."
- For multi-step work, state a short plan with a check per step:
  ```
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
  ```
- Loop until the checks pass.

5. Accuracy and certain rules
- Before coding or planning always access the relevant docs using webfetch or context7
- Do not add co-authored by claude to any commits

# djx rules

## Architecture
- Two packages in src/: `djx_engine` and `djx`.
- `djx_engine` uses ONLY the Python standard library plus the target project's own Django. It must never import textual, rich, or anything from `djx`.
- `djx` (the UI) must NEVER import django or ninja. It talks to the engine by running it as a subprocess and reading JSON.
- The engine runs under the USER PROJECT's Python interpreter, not djx's own.
- The engine prints exactly one JSON document to stdout and nothing else. All logs go to stderr. While importing user code, redirect sys.stdout to stderr so stray print() calls in user code cannot corrupt the JSON.
- The engine must never open a database connection or run a query. MVP1 is read-only: it never writes to the user's project.
- Ask Django (URL resolver, app registry, management registry). NEVER parse source text to find routes or models. The only allowed text parsing is detecting DJANGO_SETTINGS_MODULE from manage.py.
- The JSON contract has `schema_version`. Never change field names silently. If you must, bump the version.
- One failing collector must not kill the others. Wrap each collector, record a warning, continue.

## UI
- Never block the UI thread. Engine calls run in a Textual worker.
- Narrow-first: the app must be fully usable at 50 columns wide. Wide terminals get two panes.
- Keyboard first, mouse also works.

## Quality
- Every change leaves `uv run pytest` and `uv run ruff check .` green.
- Small commits with clear messages.
- Prefer boring, simple code. No clever abstractions.
- If an assumption about a library's internals (django-ninja, Textual, Zed) is unverified, read the installed source or docs and verify before relying on it.
