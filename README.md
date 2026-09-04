# Needle

A kanban over a corpus of plans, for a team made of one owner and many AI
sessions that share no memory. The board is the memory.

- `docs/INTENT.md` — why this exists and what it must be true about. Start there.
- `docs/plans/` — the slices, with the folder as their status; `docs/plans/done/` is the archive.
- `docs/design/` — the signed comps each surface was built from.
- `docs/reviews/` — the review record every code-shipping slice closes with.
- `CLAUDE.md` — the working rules for the sessions that build it.

## Run it

Three commands put a project on the board and serve it.

```bash
uv run needle add /path/to/repo --name "Harbourmaster"   # register; import the 0.1 card file if there is one; card every plan and suggestion
(cd frontend && npm ci && npm run build)                  # build the page once
uv run needle serve                                       # http://127.0.0.1:8480
```

`add` reads `docs/plans/`, `docs/plans/done/`, `docs/slice-suggestions/` and
its `done/` in the repository and never writes to it; on a path already on the
board it re-reads the corpus and says what changed. The board's own state
lives in `~/.local/share/needle/needle.db` (`NEEDLE_DB` overrides), outside
every project's tree. While `serve` runs, a plan or suggestion written into
the corpus is a card within seconds — from the first file of a folder created
after the start — and a project added with `needle add` is in the page's
project switcher without a restart. Each project's board is at `/p/<slug>`.
`serve` stops on SIGTERM within a second, so it can run under a supervisor.

## The runtime, from the command line

The runtime is a service with four jobs, each a `needle` verb the owner's own
terminal can use before the board ever calls it. Add `--json` to any of them.

```bash
uv run needle sessions                 # every session on this machine, across every subscription, as one list
uv run needle where --from armana      # where work runs next, as claude-acct's one rule answers it
uv run needle start /path/to/repo card-42-a-slug "the brief"   # a lane in its own worktree and scope
uv run needle window <short>           # a window into a session; close it without ending the session
uv run needle move <short> --to hrme   # stop where it runs, resume where the rule names
uv run needle stop <short>             # end a session through its slot, proved gone
```

The model rule and the limit detector live in `claude-acct`
(`claude-acct best`, and the `StopFailure` handoff hook); the runtime asks and
acts and never re-implements them. A start runs in a transient systemd scope of
its own, so nothing the board does can end it.

## The doors and the loops

From a card the owner presses Start, and everything else about the card's
life happens without him: the card enters Executing because a session has
hands on its worktree, leaves it to where the work says (Executed when the
close landed, Decision moment when the work folded but nobody wrote it up,
back where it came from when nothing folded), and moves on to Done when the
signal its WATCH row names arrives. Every door on the card — Start, Watch,
Answer, Discuss, Look, Resume, Stop — opens through the runtime, proves its
effect, and fails loudly by name. Every machine move is an audit row with its
reason in one sentence, in the card's history.

Sessions push; the board never polls a session. The hook in
`hooks/needle_hook.py` is registered in each project's `.claude/settings.json`
(`uv run needle hook install /path/to/repo`) for SessionStart, Stop,
SessionEnd and StopFailure; it queues on disk and drains to `/api/hooks`, so a
board that was down loses nothing. A session writes its outcome back through
the command line, never by editing a file:

```bash
uv run needle card hellorevenue 253                  # the brief a lane opens with
uv run needle row hellorevenue 253 WAITS "the deploy"  # one row on the card
uv run needle close hellorevenue 253 --delivered "…" \
    --watch "prod answers — url https://… expect \"ok\" by 2026-09-12 every 6h" \
    --review docs/reviews/2026-09-10-the-work.md      # rows and the move, one act
uv run needle fold [--main]                          # from the lane: fast-forward push to origin/develop, trunk levelled
uv run needle start-card hellorevenue 253            # Start, through the running board (what a discussion's "go" runs)
uv run needle sync | signals | lanes hellorevenue    # the loops, by hand
```

A card enters Executed only with a WATCH row that names its signal — what
will be observed, where, and by when — in the grammar `WATCH: <what> —
url|file|command|owner <target> [expect <value>] by <YYYY-MM-DD> [every
<N>h|<N>d]`. The board reads URLs, files and commands on the row's cadence and
moves the card on what they say; a signal only the owner can read is put to
him as a question at its due time.

## Check it

```bash
uv run pytest -q                       # backend + ratchets
cd frontend && npx tsc --noEmit        # types
cd frontend && npx vitest run          # frontend tests
```

## How it is laid out

| Where | What |
|---|---|
| `domain/` | What things are: every type, as a Pydantic model or an enum. Nothing here acts. |
| `board/` | What happens: the rules, pure over domain values — parsing a document, reconciling the corpus with the cards, placing a move, assembling the page's view, reading the 0.1 card file. |
| `infrastructure/` | The store (SQLite, migrated by Alembic), the corpus on disk and its watcher, the running board. |
| `runtime/` | The thing that runs: sessions as one list across subscriptions, the model rule (asked of `claude-acct`, never re-implemented), starting a lane in its own transient scope, a window into any session. Everything that touches the machine goes through `runtime/machine.py`, the one door the tests stand in for. |
| `api/` | The HTTP API, the doors (`doors.py`) and the loops (`loops.py`) where the board and the runtime meet, the `needle` command line (the board's verbs, the runtime's, and a session's), and the generator that mirrors `domain/` into `frontend/src/types/`. |
| `hooks/` | The session hook every project registers: standard library only, never blocks, queues while the board is down. |
| `frontend/` | The page: React, one design system in `src/components/ui/`, the board in `src/board/`. |
| `tests/ratchets/` | Every boundary in `CLAUDE.md`, held by a test. |
| `tests/floor.py`, `tests/fakes/bin/` | The fixture floor: a machine the runtime stands on without touching this one — every path redirected, every command a stand-in. A ratchet holds that no test reaches the real machine. |
| `tests/fixtures/harbourmaster/` | Harbourmaster: a synthetic project — corpus and 0.1 card file — that the backend fixtures, the page's tests (`frontend/tests/fixture.json`, generated by `tools/board_fixture.py`) and the comps all draw on. No real project's content is in the tree. |

When a domain type changes, run `uv run needle types`; a ratchet fails until the
frontend's mirror matches.
