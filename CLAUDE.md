# Needle — working rules

The doctrine we work under — intent over orders, the two kinds of decisions,
the inverted labour economics, the /clear cliff, closed loops — lives in the
owner's global `CLAUDE.md` and loads in every session. This file holds only
what is true of Needle.

## What this is

Needle is a kanban over a corpus of plans: the shared memory of a team made of
one owner and many AI sessions with no memory of each other. The fixed point
is `docs/INTENT.md`. Read it before anything else; when a rule here and that
document disagree, the intent wins and this file gets fixed.

## The rules

**Intent first, plan second, code third.** Every slice has a plan in
`docs/plans/` with an `Effort gate:` line and a "done means" per item. The
folder is the status: `docs/plans/*.md` is live work, `docs/plans/done/` is
the archive. No separate status list — a hand-kept one drifts.

**Execution takes a lane, and the trunk is `develop`.** Work that becomes
commits runs in a git worktree under `.claude/worktrees/`, named
`card-<id>-<slug>` once the board can see it, on a short-lived branch. The
fold is a fast-forward push to `origin/develop` (`git push origin HEAD:develop`)
when the suite is green; the branch is deleted at the fold. Claude Code's
worktree guard refuses a lane any git command aimed at the main checkout, so
a lane never merges locally — origin is the meeting point, and the local
checkout follows `origin/develop` (kept level by the runtime once slice 03
lands; by the coordinating session until then). `main` is promoted from
`develop` at each slice close and is what the public repository shows as
stable; nothing commits to `main` directly. The main checkout is for reading,
docs and the sync. Same shape as Hello Revenue, so one convention serves
every project on the board.

**The board reads what runs; it never is the thing that runs.** Nothing under
`board/` spawns a process, opens a window or chooses a model. That is the
runtime's job (`runtime/`), reached through a typed interface. A test refuses
`subprocess` imports under `board/`.

**One way to do each thing.** Two ways is failed alignment; consolidate. A new
primitive — type, endpoint, component, event — is born after a search for the
existing one, and the proof of search goes in the plan or the commit body.

**Typed edges, lossless.** Backend types are Pydantic and are the contract;
the frontend mirrors them one module per backend concept, no `any`, no
`Record<string, unknown>`. If the backend shape changes, TypeScript fails.

**Boundaries that matter are ratchets, not conventions.** A test under
`tests/ratchets/` holds every boundary named in this file. Ratchet the intent,
never the method: a ratchet that would have to change for a better method to
ship was written at the wrong altitude.

**Nothing ships half-done.** No TODO, no "later", no deferral markers; a
ratchet refuses them. Say precisely what is not done instead.

**Nothing is done without a review record, and a review is a loop, not a
pass.** A code-shipping slice closes with a review under `docs/reviews/`. The
review runs in passes: each pass reads the work through one lens, names its
findings with file and line, the fixes land, and the next pass reads the
fixed work again — until a pass finds nothing new. The lenses, in order: the
feature against its plan's "done means"; the seams (concurrency and races,
failure and restart, the truth of what the board shows); the boundaries this
file names. The record lists every pass with what it found and what changed.
One clean pass after a pass with findings is the floor; a review that stopped
at its first pass is not a review (owner ruling 2026-09-04, from watching a
nine-pass close on the first board: "review, fix, review again").

Findings fall in three rings, and the ring decides what happens to them (owner
ruling 2026-09-04). **Inside the change:** fixed in the lane, and the next
pass re-reads. **Adjacent — the seams the change touches:** fixed in the lane
when the fix serves this slice's intent, otherwise filed as a suggestion in
the corpus with the finding as its evidence and `**Kind:** defect` on its
second line, so it lands on the defects rail, not among the ideas. **Outside the change:** never
fixed in the lane; filed as a suggestion, which is a card by the next read.
The fix loop runs over the inner two rings until a pass finds nothing new; the
outer ring never loops, it files. A lane that fixes outside its change is the
scope creep the effort gate warned about, however good the fix.

**Docstrings say why, commits say what prompted.** Every commit has a body:
what prompted the change and what the diff cannot convey.

## Stack

Backend: Python via `uv`, FastAPI, Pydantic, SQLAlchemy + Alembic on SQLite.
Frontend: React + TypeScript + Vite, Tailwind, a small design system in
`frontend/src/components/ui/` that is the only visual language. The exact
versions live in `pyproject.toml` and `frontend/package.json`, never here.

## Commands

```bash
uv run pytest -q                       # backend + ratchets
cd frontend && npx tsc --noEmit        # types
cd frontend && npx vitest run          # frontend tests
```

## Commit messages

```
<type>(<scope>): <what changed>

<What prompted it, 1–2 sentences. What the diff alone cannot convey.>

Co-Authored-By: <model> <noreply@anthropic.com>
```
