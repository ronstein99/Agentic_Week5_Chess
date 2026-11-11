# Lab 5 review

Commit reviewed: 75cad39 · Reviewer: Claude Code, Claude Opus 5.5 · Unmerged branches: none

## Highlights

- Fix first: there is no `CLAUDE.md` or `AGENTS.md`, so nothing tells the next agent to run pytest, Ruff and `mypy --strict`. Nothing in `.claude/settings.json` runs them either.
- Well done: every check passes. 103 tests pass, coverage is 100%, Ruff passes with seven rule sets selected, and `mypy --strict` reports no issues. Feature interactions are tested thoroughly, for example `tests/test_redo.py:162` (redo against the computer after a save and load) and `tests/test_promotion.py:73` (undo of a capturing promotion).
- Game state: the position is still the starter's two-item list `[board, side]`, typed `list[Any]` (`game.py:11-13`). This weakens `mypy --strict` exactly where the state lives. Everything the features added sits on `Session` as named fields with a `MoveRecord` TypedDict (`session.py:33`).
- Redo arrived without tests (`be3f27a`). Its 197 lines of tests came two commits later (`75cad39`). Undo tests were also removed "for now" (`18ef907`) and only restored in `9d40b9a`.
- Well done: save and load validate the file by replaying every move, including the redo moves, on a scratch session before changing the game (`session.py:172-196`).

## At a glance

| Check | Result |
| --- | --- |
| Tests | 103 passed, 0 failed, in 15.2 s |
| Coverage | 100% total; lowest: all four files 100% |
| `ruff check` | 0 findings |
| `ruff format --check` | 0 files would change |
| `mypy --strict` | 0 errors in 11 files |
| Game state | list or tuple of 2 items (2 in the starter) |
| Game state restructured in the lab | no |
| Instruction file | none |

## The week's practices

1. ✅ Tests for each feature: save/load, undo, redo, captured pieces and promotion each have tests (`tests/test_session.py`, `test_redo.py`, `test_captured.py`, `test_promotion.py`). Sounds (`static/app.js:19`) have none, because they are browser-only.
2. ✅ Tests of features together: `test_undo_after_load_matches_undo_before_save` (`tests/test_session.py:133`), `test_undo_removes_capture_from_display` (`tests/test_captured.py:15`), `test_undo_save_load_redo` (`tests/test_redo.py:87`).
3. ✅ Assertions that check results: the spot-checked tests assert on the board, turn, notation and redo contents (`tests/test_session.py:72-80`). No `print` appears in the tests.
4. ⚠️ Fast and repeatable: 15.2 s in total, and `test_ties_vary_with_the_random_source` alone takes 3.7 s. `computer-move` uses the unseeded global `random` (`session.py:232`), so the computer tests depend on random play and check only counts and turns.
5. ⚠️ Bugs became tests: `1a72fae` and `30f2627` touch `tests/`. `ff768ad` (the empty-file fix on save) changes only `static/app.js`.
6. ✅ No weakened tests: the two removed `assert`s are in `38c8126` (ruff format) and were reflowed, not removed. The four undo tests deleted in `18ef907` returned in `9d40b9a`.
7. ✅ Coverage: 100% (325 statements). `__main__` blocks are excluded in `pyproject.toml`.
8. ✅ Linted beyond the defaults: `select = ["E", "W", "F", "I", "B", "UP", "SIM"]`, with 0 findings and 0 `# noqa`.
9. ✅ Formatted: "13 files already formatted".
10. ⚠️ Type-checked: 0 errors and 0 `# type: ignore`. However, 7 `Any`s remain in the application code, including `Position = list[Any]` (`game.py:13`) and `restore(self, data: Any)`.
11. ⚠️ From the start or at the end: tools were configured mid-lab (`1a72fae`), but all the annotations came in one commit near the end (`f9e6be7`).
12. ❌ Checks in the instruction file: there is no `CLAUDE.md` or `AGENTS.md`, and no `.claude/settings.json` hook.

## The game state

The board and the side to move are a two-item list read by position (`position[0]`, `position[1]`), the same as in the starter commit `45f06c1`. The features added named fields on `Session`: `history` and `redo` as lists of `MoveRecord`, plus `opponent`. Captured pieces and notation are derived properties (`session.py:66-80`), so they cannot drift from the history. `saved()` writes the version, opponent, history and redo, which is everything needed to rebuild the game. The browser keeps only UI state (`static/app.js:4`). `git log -- game.py session.py` shows the state growing but never changing shape, so there was no restructuring to trace.

## Other findings

- The redo records in a loaded file are stored as given (`self.redo = list(redo)`, `session.py:196`). Their legality is checked, but their stored `label` and `captured` fields are not checked or rebuilt.
- A move against the computer is a separate `computer-move` request. If that request fails, the game is left waiting with Black to move. The tests cover this through `computer_to_move`, but a player would see a stuck board. This was not checked in the browser.
- `Position` as `list[Any]` means mypy cannot catch a swapped board and side. A small dataclass or a `tuple[Board, str]` would let the type checker guard the core state.
