# 01b — The map's loose ends

**Status:** DONE — built 2026-09-04 by the build session (Claude Fable 5.1 at high), reviewed in `docs/reviews/2026-09-04-the-maps-loose-ends.md`, folded into main the same day.
**Written:** 2026-09-04, from the first morning of using the map: one defect fixed by hand (a project deep link 404'd), two recorded as a suggestion, one gap the owner asked for, and one condition on the public repo.
**Effort gate:** high — five small, well-specified items; the one judgment is the switcher's place on the page, decided below so the build does not stop to ask.
**Sequencing:** before 02. Slice 02 restarts the server and adds a second reader of the project list; both are cheaper on a server that stops cleanly and reads its projects live.

## Intent

The map does what 01 promised at its edges too: a second project is one click away, the server restarts like a service should, the corpus is the way in from the very first file, and the public repo carries no other project's content.

### 1. A project switcher on the page (owner ask, 2026-09-04)

Two projects are on the board and the page shows one at a time by path. Done means: the wordmark area carries the project's name and a switcher that lists every project on the board and navigates to `/p/<slug>`; the current project is marked; the page remembers nothing (the path is the state), so a reload and a link land where they say. **Ruling:** a switcher in the head, not tabs across the top, because the columns already own the top of the page and a second project is an occasional move, not a constant one. Alternative rejected: a project column on the left, which costs width the five working columns do not have on a laptop.

### 2. `needle serve` stops on SIGTERM

Done means: the process exits within two seconds of SIGTERM with the watcher and every open stream closed, exit code 0; a test starts it as a subprocess and asserts the deadline. Evidence: `docs/slice-suggestions/2026-09-04-serve-does-not-stop-on-sigterm.md`.

### 3. The corpus is the way in from the first file

Done means: a corpus folder created after the server started is watched from its first file (watch the project root or `docs/`, filter by path, or re-evaluate roots on change); `needle add` on a registered project re-reads its corpus instead of refusing; the running server reads the project list live, so a project added while it runs is on the page without a restart. Evidence: the same suggestion's second section.

### 4. The comps and the test fixtures carry a synthetic project, not Hello Revenue

The signed comps in `docs/design/` and `frontend/tests/fixture.ts` were built from Hello Revenue's real card file and carry its card titles. The repo is public. Done means: a synthetic project in `tests/fixtures/` (a plausible product with twenty-odd plans and suggestions in the corpus shape, none of them Hello Revenue's) feeds the comps, the frontend tests and the backend fixtures; the comps are regenerated from it with the design unchanged; a ratchet greps the tracked tree for the known Hello Revenue card titles and fails on any. **Ruling:** the slice history since the founding commits is squashed to one commit before main is first pushed, because the earlier commits carry the real data; the trail the owner asked for lives in the plans, rulings and reviews, not in commit granularity. Alternative rejected: rewriting file contents through history, which is fragile on HTML.

### 5. The close

Done means: the review record, the suite green, the plan archived, and the two suggestions from 2026-09-04 moved to `docs/slice-suggestions/done/` with a line naming this plan.

## Terrain

- The deep-link fix already on main: `api/app.py` (`project_page` ahead of the static mount) and its test in `tests/api/test_api.py`; extend, do not duplicate.
- `frontend/src/App.tsx` reads `/p/<slug>`; `frontend/src/components/ui/` is the design system the switcher is built from; `AppHead` and `Wordmark` are where it goes.
- `infrastructure/corpus.py::watch` (roots chosen once), `api/app.py` (the projects list and the lifespan), the `needle` command line in `api/`.
- The signal handling: uvicorn's own shutdown plus whatever holds the loop open (the watcher task, the SSE generators); measure first with `SIGTERM` and `py-spy dump` or a faulthandler trace before guessing.
- `frontend/tests/fixture.ts`, `tests/conftest.py` (the corpus fixture writer), `docs/design/*.html`.

## Acceptance criteria (behaviours)

1. On the page, the project switcher lists both projects; choosing one lands on its board; a reload stays there.
2. `systemctl --user restart needle-serve` completes in under five seconds.
3. Create `docs/slice-suggestions/` in a registered project while the server runs and drop a file in it: a card within seconds, no restart. `needle add` on a registered path re-reads and reports what changed.
4. `git grep` for three known Hello Revenue card titles finds nothing in the tracked tree; the ratchet holds it.
5. The suite is green; the review record exists; the plan and the two suggestions are archived.

## Close-out

Each item's "done means", stanced before the fold, with the evidence.

1. **A project switcher on the page** — met. The project pill in the head is the switcher: a select listing every project on the board, the current one chosen, landing on `/p/<slug>` by `pushState`; the back button and a reload read the path, and the page holds no other state. Three vitest scenarios (`frontend/tests/board.test.tsx`: choose, deep link and back, a project appearing after a board change); live over DevTools against a two-project store: chosen → `/p/second` with its one card, reload stays there.
2. **`needle serve` stops on SIGTERM** — met. Measured before the fix: 0.2 s and exit 143 with no client; never, with one stream open (killed at 12 s). After: 0.41 s and exit 0 in both cases, from the same script; `tests/api/test_serve.py` starts the real process, holds a stream open, sends SIGTERM and asserts exit 0 inside two seconds with the stream closed by the server. Not run here: `systemctl --user restart needle-serve` — the unit is the owner's transient scope; SIGTERM is what it sends.
3. **The corpus is the way in from the first file** — met. The watcher subscribes to `docs/` whole and filters to the four folders, so a folder created after start is heard from its first file (`tests/infrastructure/test_live.py`; live: 0.3 s from file to card in a `docs/slice-suggestions/` made while serving). `needle add` on a registered path re-reads the corpus and reports what changed (`tests/api/test_cli.py`). The running server re-reads the project list on every request for it and when the store's file changes, and the open page re-reads it on every board change: a project added with `needle add` was in the switcher without a restart or a reload (live check, step 3).
4. **A synthetic project in the comps and the fixtures** — met. Harbourmaster (`tests/fixtures/harbourmaster/`: 27 documents, 11 live plans, 8 live suggestions, 8 archived, and a 0.1 card file of 21 cards plus one machine ask) feeds the backend fixtures, the page's tests through a generated snapshot (`tools/board_fixture.py` → `frontend/tests/fixture.json`, a ratchet regenerates and compares) and both comps, re-seated with the design unchanged. `tests/ratchets/test_the_fixture_project_is_synthetic.py` holds 112 fingerprinted titles of the first real project against every tracked text line; it caught 37 lines before the purge and zero after.
5. **The close** — met by this section, the review record, a green suite (104 backend tests with the 18 ratchets, `tsc`, 13 vitest scenarios), the plan in `done/`, and the one suggestion file of 2026-09-04 — it carries both suggestions as two sections — in `docs/slice-suggestions/done/` naming this plan.

What this close leaves for the owner: try `systemctl --user restart needle-serve` and time it; then open the page and switch projects from the pill in the head.

## Rulings

Recorded as the build made them, each with the alternative rejected. The first (the switcher's place) is the plan's own, above.

**1. The project pill is the switcher: a native select wearing the pill.** Build session, 2026-09-04. One keyboard-reachable control with no menu of its own to manage, and the comp already drew the pill with a caret. Rejected: a popover of links (focus management, a second way to navigate beside the select the open card already uses for Move to); tabs across the top (the columns own it).

**2. Switching pushes a path; the back button pops it; there is no router.** Build session, 2026-09-04. `App` holds the slug read from the path, `pushState` on a switch, `popstate` to read it back; the board remounts on the slug. Rejected: a full navigation per switch (works, but reconnects the stream and re-reads everything for an occasional move); a router library (one more place state could live).

**3. The page re-reads the project list on every board change, never on a timer.** Build session, 2026-09-04. The board version is the one signal the page has that the store moved, and a project appears at the next one. Rejected: polling; a second stream for projects.

**4. Streams end on the stop signal, from a server subclass; the graceful-shutdown ceiling is one second.** Build session, 2026-09-04. `NeedleServer.handle_exit` closes the board so every `wait_for_change` returns and every stream generator ends before uvicorn drains; `timeout_graceful_shutdown=1.0` bounds anything that does not. Rejected: the ceiling alone (streams would be cut by cancellation after it, not closed by design); a signal handler of our own beside uvicorn's (uvicorn installs its own over it for the duration of `serve`).

**5. The process exits 0 after a signalled stop.** Build session, 2026-09-04. uvicorn re-raises the captured signal after a clean stop so the process ends by it (143); a no-op handler installed before `serve` is what it restores and re-raises into, and the process returns 0. Rejected: keeping 143 (systemd tolerates it; the plan's done-means and any script reading the status do not).

**6. The watcher subscribes to `docs/` whole and filters to the four folders.** Build session, 2026-09-04. A folder that does not exist yet cannot be subscribed to; its parent can. Rejected: re-evaluating the roots on each change (the change that creates the folder is never heard); watching the project root (`.git` and `node_modules` churn on a real repository).

**7. The project list is read from the store on each request for it, and re-read when the store's file changes.** Build session, 2026-09-04. The store is the one channel `needle add` and the server already share, and a write to it is an inotify event. Rejected: `needle add` posting to the server (needs a host, a port and a running server); polling the store.

**8. On a store change, only a project whose own watcher has failed is rescanned.** Build session, 2026-09-04. That is the one case a `needle add` re-read from the command line could know something the server does not; a healthy watcher already heard the file. Rejected: rescanning every project on every store write (the server's own moves would rescan 690 documents each).

**9. `needle add` on a registered path re-reads the corpus, with `--name` and `--slug` ignored and said so.** Build session, 2026-09-04. Cards born at a re-read are arrivals, as they are for the watcher. Rejected: refusing (the old behaviour, which left no rescan short of a restart); renaming in place (a different verb, not asked for).

**10. The synthetic project is Harbourmaster, keeping the first project's card numbers and board topology.** Build session, 2026-09-04. A berth booking and billing product for small marinas: far enough from an ad-campaign product that nothing reads as a rename, close enough in shape — the same groups' roles, the same gone citations, notes, archived plans and machine ask — that every scenario 0.1 taught still holds with new words. Rejected: generated filler (the comp rule is real data, and filler hides what a comp exists to find); anonymising the real titles in place (still the real project's content).

**11. The page's fixture is a snapshot generated from the synthetic project through the real pipeline, held by a ratchet.** Build session, 2026-09-04. Registration, import and sweep run in a temporary store; one arrival is staged by holding a plan back from the founding sweep. Rejected: a hand-typed fixture (it had drifted from the API's shape and carried the real titles).

**12. The title ratchet holds fingerprints, not titles, and slides word windows over every tracked text line.** Build session, 2026-09-04. The 112 titles of four words or more, the board-and-lane vocabulary left out so Needle's own prose cannot collide. Rejected: grepping literal titles (the ratchet would carry the content it forbids); whole-line hashes (titles sit inside markup).

**13. The comps were re-seated, not redrawn.** Build session, 2026-09-04. The screens between the comp bar and the judging list were re-authored with Harbourmaster's cards, every staged state and pin kept where it was, stylesheet and script untouched; the comp bar and the design README say so. Rejected: leaving them (the repository is public); generating them from the snapshot (a comp stages states no snapshot holds).

## Estimate

Execution clock: half a lane-day. Gate clock: none. Actual: one session, 2026-09-04 morning.
