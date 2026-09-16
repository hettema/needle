# A note reaches a colleague whichever machine either of you is on

**Kind:** defect
**Fix:** when a call made on one machine is a row the board can read — file /home/dennis/Work/needle/docs/plans/done/ by 2026-11-13 every 14d
**Found by:** the lane on card #137 (docs/plans/done/2026-09-13-colleagues-ask-each-other-for-help-without-disturbing-each-others-work.md), in the independent review

## The intent it breaks

A colleague should be able to ask any colleague on the team for help and get
an answer. It can, as long as both of them are sitting on the machine the
board runs from. Every lane runs on the other one, so in practice the way
colleagues ask each other for help works everywhere except where the work
happens — and the owner is back to carrying questions between them himself,
which is the thing card #137 was for.

## The evidence

Card #137 shipped the note on 2026-09-13: a colleague that cannot be resumed
— one in a terminal the owner opened himself, one in the middle of its turn
— is handed the note instead of refused, and reads it as its next word.

It was verified live minutes after the fold, from the rented machine, and
the verification is what found this:

- The note was handed to card #139's session (call 127). `needle wait 127`
  reported it correctly: "handed over … has not been picked up".
- The board's head showed no note standing, then or a beat later.
- The stores say why. The rented machine's store held calls 125 and 127; the
  board's store on the laptop held nothing past call 93.
  `needle call` is a runtime verb — `api/cli.py::main` hands only the board
  verbs over to the board's machine — so it runs where it is typed and writes
  that machine's own records.
- The note is carried by the board's word (`api/loops.py::Loops.word`, which
  reads `self.live.store`), served by the board on the laptop. Every rented
  session's hook reaches it through a tunnel
  (`needle-tunnel.socket`: `systemd-socket-proxyd … 100.88.60.5:8480`). So
  the board that would deliver the note cannot see the row, and the note
  could not have arrived however long it stood.
- The same locality is why `_tend_calls` never tends a call made on another
  machine, and why the answer and note files — local paths on the calling
  machine — are not where the board could read them either.

Not the note's own doing: the call row has been per-machine since plan 17,
and the gap belongs with the one card #83 already names — "a colleague on
another machine cannot be called from here yet"
(`runtime/service.py::call`), item 4. What card #137 added is a second thing
that needs the row to travel, so the cost of not travelling is now larger.

Until it travels, `needle call` refuses to hand a note from a machine the
board does not serve from, by name and with nothing written
(`runtime/service.py::call`, card #137's own repair) — so a caller learns at
the door instead of waiting on a note nothing will carry. That refusal is
the honest floor, not the fix.

## What would hold it

A call is one row wherever it is made: written where the board reads it, so
the board delivers the note, tends the call and shows a standing one on its
head, and `needle wait` reads the same row from anywhere. The note and the
answer are files, so either they travel with the row or the row names the
machine that holds them — that choice belongs with card #83's item 4, which
has to answer it for the warm call too.

A test on the floor: a note handed from a machine that is not the board's is
delivered to its colleague's next word, and stands on the board's head until
it is, exactly as one handed from the board's own machine does.

## More evidence, from card #155 (2026-09-16): a reviewer read as the worker

The same root — a call made on the rented machine is a row in that machine's
store, which the board never reads — has a second face, seen on Hello Revenue
#601 on 2026-09-16 and written on Needle's watercooler by the session that
diagnosed it at 18:07Z and 18:18Z. A fresh Codex reviewer (call 242) was
launched on rented in #601's own worktree, read-only, to check a repair. The
board showed that reviewer as the card's own session and main worker: the
card's true implementer (a Claude session, still alive on rented) was not the
face's session, the board tried at 18:04:15Z to move the reviewer from its
own call scope into the card's occupied scope, and the owner's Watch on the
card opened a terminal that closed at once, because the attach command the
window runs is Claude's (`runtime/windows.py::attach_command` emits `claude
attach <short id>` for any session, a Codex thread included). When the
reviewer ended, the lane would have read that as the lane's own ending.

Why it is this root and not another: `board/lane.py::elsewhere` is the reader
that says a session sitting in a card's copy of the code is not that card's
— it reads the board's own call rows (`facts.calls`, from the board's store)
and the card each session was started on (`facts.started_on`). Both come
from the laptop's store. A call launched on rented writes its row on rented,
so the board sees no call for that session and no started-on record, and
`board/lane.py::_winner` takes the first live background session in the
directory, which was the reviewer. Card #137 made the reader; what it reads
is missing on every call made where the lanes run, which is this card's
finding exactly. Neighbours on this ground: #114 (a card shows another
project's session as its own — the same face lie, a different cause), #120
(a copy of the work read where its record says), #137 (shipped the reader),
#155 (the exit that found this while closing).

Not checked here: whether Watch on a legitimate Codex lane (a card whose own
session is a Codex thread) is broken by the same attach command regardless of
this misreading; the attach command has no branch on the session's make.
