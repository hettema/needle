# No test ever opens the board's own store, because the floor pins it for every test

**Kind:** defect
**Fix:** now — the intent is written (the floor's own docstring in `tests/conftest.py`: no path the runtime reads is the laptop's; card #51's ruling that a test never migrates the shared store); the fix is one line in the floor's fixture — `NEEDLE_DB` pinned under the floor for every test, as `NEEDLE_SLOT_ROOT` and the rest are — and removes the class, where today each test module that touches the store sets it for itself and one that forgets writes beside the laptop's store.
**Found by:** the lane on card #83 (docs/reviews/2026-09-09-the-work-runs-where-the-horsepower-is.md, the fold of item 3's half, 2026-09-10): a new test module ran once before it imported the store-pinning fixture of `tests/runtime/test_machines.py`, and `needle board rented` in it wrote `~/.local/share/needle/board.json` beside the real store; the served board refused to start at the fold's restart ("the board serves from rented") until `needle board here` removed it.

## The intent it breaks

Every path the runtime reads under a test stands on the floor (`tests/floor.py`); the ratchet `test_every_path_the_runtime_reads_is_under_the_floor` holds that for the paths `runtime/machine.py` reads through `NEEDLE_*` variables. The store's path is read by `infrastructure/paths.py::db_path` from `NEEDLE_DB`, which the floor does not set: `tests/runtime/test_machines.py::quick` sets it per module, other modules use the `store` fixture with an explicit path, and a module that does neither — or a test that calls `api.cli.main` — opens the laptop's store, migrates it, and since card #83 can write the board-elsewhere file beside it.

## Evidence

- `tests/floor.py::ENVIRONMENT` names thirteen variables and not `NEEDLE_DB`; `tests/conftest.py::machine_floor` sets those and no store.
- `tests/runtime/test_machines.py::quick` (autouse, module-local) sets `NEEDLE_DB` to `tmp_path / "board.db"`; `tests/runtime/test_board_elsewhere.py` imports it by name, which is the convention that failed once.
- `~/.local/share/needle/board.json`, written 2026-09-10 09:04Z by that run, named the rented machine with the lane's own `uv --project …/worktrees/card-83-… run needle` as the command.

## What done looks like

`machine_floor` sets `NEEDLE_DB` (and `NEEDLE_DATA_DIR`) under the floor for every test, the ratchet reads `infrastructure.paths.db_path()` and `board_path()` beside the runtime's paths, and the module-local `quick` fixture loses its store line.
