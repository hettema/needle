# Review — the map's loose ends (slice 01b)

**Plan:** docs/plans/done/2026-09-04-01b-the-maps-loose-ends.md
**Reviewer:** the build session (Claude Fable 5.1 at high), reviewing its own diff before the fold. No second session was in the loop; the owner's restart of his own unit and his read of the switcher are the sign-off this record cannot replace.
**Diff range:** fa07b65..190eeb2 (the two build commits; the close commit after them carries this record, the plan's close-out and the archive moves, and no code)
**Findings:** 7

## What was checked

- **The stop, measured before and after** with one script against the real process (`.venv/bin/python -m api.cli serve`, faulthandler on SIGUSR1 for the stacks): before, 0.2 s and exit 143 with no client, no exit in 12 s with one stream open, the main thread parked in uvicorn's shutdown wait; after, 0.41 s and exit 0 in both cases. `tests/api/test_serve.py` repeats it as a subprocess with a stream held open over `http.client`.
- **The watcher, from the first file**: `tests/infrastructure/test_live.py` deletes `docs/slice-suggestions/` from the fixture, starts the board, creates the folder and writes one file, and reads the card; live, against the served page, a folder made in a project registered while serving produced a card on screen in 0.3 s.
- **The project list, live**: `tests/infrastructure/test_live.py` registers a second project through a second `Store` on the same file, as `needle add` does from another process, and reads it on the running board, watching, with the version bumped; `tests/api/test_cli.py` runs `needle add` twice on one path and reads what the re-read reports, before and after a plan is written offline.
- **The switcher**: three vitest scenarios — choose a project and land on its path, a deep link and a `popstate` back, a project appearing in the list after a board change — and the live drive over DevTools: options at load, `needle add` from the command line, the option appearing after a file landed, the switch to `/p/second` with its one card, a reload staying there. Screenshots at 1440×900 of both boards, dark, compared by eye with the comps: the pill is where the comp drew it, with the caret.
- **The synthetic project through every reader**: scan (19 live, 8 archived), the 0.1 import (21 cards, one machine ask skipped, two gone citations, one malformed), the founding sweep (6 born), the snapshot generator, and the whole backend suite on the new fixture. The 112-title ratchet was run before the purge and named 37 lines in the comps and the page's fixture, and none after; its self-test plants a fingerprint and finds it.
- **The comps**, opened after the re-seat: every staged state (lift, gap, failed write, definition open, the gone document, the arrival), every pin and every judged call in place; a final scan for the real project's vocabulary (its name, its customers, its platforms) finds nothing.
- **The ratchets** (18): the seventeen from slice 01 unchanged and green, plus the new one in two halves — no real title in the tracked tree, and the page's snapshot equal to what the generator renders.

## Dispositions

1. `needle serve` exited 143 after a clean stop with no client: uvicorn re-raises the signal it stopped on — FIXED in 190eeb2 (a no-op handler installed before `serve`, ruling 5).
2. `needle serve` never stopped with a stream open: the stream generator waited on the next board change while its client stayed connected, and uvicorn's drain has no deadline — FIXED in 190eeb2 (`NeedleServer.handle_exit` closes the board; every `wait_for_change` returns at once; graceful ceiling 1 s).
3. A corpus folder created after start was never watched — FIXED in 190eeb2 (`docs/` watched whole, filtered by `in_corpus`).
4. `needle add` refused a path already on the board, so there was no rescan short of a restart — FIXED in 190eeb2 (a re-read with the effects reported).
5. The command line never closed the store it opened; under the suite's warnings-as-errors this surfaced as a `ResourceWarning` the moment the CLI had tests — FIXED in 190eeb2.
6. One-shot mock answers queued by one vitest scenario outlived it and broke the next; the old `mockClear` kept the queue — FIXED in 6bdaa72 (`mockReset` per scenario).
7. The plan's acceptance criterion 2, `systemctl --user restart needle-serve` under five seconds, was not run: the unit is a transient scope in the owner's session — NO CHANGE: SIGTERM is what systemd sends, and it is measured at 0.41 s; the owner's restart is the first thing to try after the fold.

## What the build learned the plan got wrong

- "The two suggestions from 2026-09-04" are one file with two sections; it moved to `done/` as one file naming this plan.
- "Exit code 0" is not what uvicorn does after a clean signalled stop by design; meeting it means answering the re-raised signal ourselves (ruling 5). It is a small override of a library's deliberate behaviour and it is documented at the function that does it.
- The comp rule "frozen once signed" met the ruling "no real project's content in a public repo"; the comps were edited once, and the design README now says so and why.

## Not done, stated

- The owner's `systemctl --user restart needle-serve` timing (finding 7).
- A project that leaves the store is not a verb the board has; `sync_projects` adds and never removes.
- The store-file watcher failing is logged at warning, not shown on the page: with it down, a project added while serving is in the switcher at the next reload rather than at once. Showing it would add a field to `BoardState`; the fallback holds and the case is a filesystem that refuses inotify.
- The live check script that drove DevTools for this record lives in the session's temporary directory; `tools/drag_check.py` remains the repository's pattern for it.
