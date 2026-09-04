# What the first board held mechanically that Needle does not yet

**Found by:** the session retiring Hello Revenue's first board
(`hellorevenue/docs/plans/2026-09-04-retire-the-first-board.md`, card #387),
which had to stance every ratchet of that board on its intent before deleting
it. Four intents were held by a test there and are held by nothing here.
Each is written so a Needle session can decide it; none is urgent enough to
have blocked the retirement.

## 1. Start is his click — held by no ratchet

0.1's `test_board_gates_stay_the_owners.py` read the server's AST: the one
function that launches a fresh lane was reachable only from an HTTP route the
owner pressed, never from the reconcile loop; a recommendation was read only
when the request said `as_recommended`; the toast and the bar widget carried
no control that changes state; a machine-born card carried no gate.

Needle's `INTENT.md` says the same thing ("one move is his"), and
`tests/ratchets/test_the_board_never_runs.py` keeps `board/`, `domain/`,
`infrastructure/` and `api/` from spawning anything — but `api/doors.py` and
`api/loops.py` both reach `runtime.start`, and nothing distinguishes a door
from a loop mechanically. The rot 0.1 named still applies: a loop that starts
the top card when the machine is idle is one line, locally reasonable, and
would fail no test. Shape that fits Needle's layout: a ratchet that the
runtime's `start` is called from `api/doors.py` only, never from `api/loops.py`.

## 2. A close answers every promise — held at Hello Revenue's archive gate now, not at Needle's close

0.1's close door refused a close whose archived plan carried unstanced
promises. Needle's `close` refuses Executed while the plan is live or the
WATCH row names no signal, and reads nothing else of the plan. The retirement
re-homed the presence check at Hello Revenue's `scripts/archive_docs.py`
(`scripts/plan_close_out.py` holds the grammar), which works because Needle's
close requires the archive. It is project-local; a second project on the
board has no such gate unless it writes one. Worth ruling whether the
close-out grammar belongs in Needle's `board/parse.py` beside the plan header
parsers, read by `close`.

## 3. The founders' morning note lost its DELIVERED sentences

Hello Revenue's `scripts/whats_new_shipped.py` used to read the card file's
DELIVERED rows out of git; Needle keeps rows in `~/.local/share/needle/needle.db`,
which the GitHub Actions run cannot reach. The note now reads archived plans
only (every close archives its plan) and names the loss in its docstring. If
Needle ever exports a project's day of closes somewhere git can see, the note
can regain the sentence a closing session wrote for the owner.

## 4. The bar widget

0.1 shipped an Omarchy bar widget (`scripts/omarchy/needle-board/`) that was
never installed and polled the whole board state every eight seconds
(0.1's own open finding). It was removed with the board rather than
re-pointed, because a bar surface belongs to the board that renders it. If
Needle wants one, `/api` on 8480 is the source and the widget draws nothing
when the board is down.
