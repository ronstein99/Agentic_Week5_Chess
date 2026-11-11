# CLAUDE.md

A small chess game: game rules in `game.py`, the computer opponent in `computer.py`, application
actions and save/load in `session.py`, a local server in `server.py`, the browser interface in
`static/`, and pytest tests in `tests/`.

## Checks

Run all of these before saying a change is done, and fix what they report. All four must pass:

```sh
.venv/bin/python -m pytest -q --cov=. --cov-report=term
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy --strict .
```

- Every feature or bug fix comes with a test that asserts on the result. Test features that share
  state together, for example undo after a capture or a promotion, or redo after a save and load.
- Keep coverage at 100%.
- Never delete or weaken an assertion to make a test pass.
- Don't add `# noqa`, `# type: ignore` or new `Any`.
- Seed the computer opponent in tests by passing a `random.Random(seed)` to `choose_move`.
