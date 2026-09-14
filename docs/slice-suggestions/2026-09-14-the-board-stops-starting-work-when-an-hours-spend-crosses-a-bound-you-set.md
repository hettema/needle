# The board stops starting work when an hour's spend crosses a bound you set

**Kind:** idea
**Fix:** his — the bound is a spend limit, and only the owner can say how many
times a normal hour's spend the machine may burn before it stops starting
work; nothing written authorises a number today, so a session setting one
would be deciding his exposure for him
**Found by:** the owner, 2026-09-14, at the Discuss door of Hello Revenue #524,
asking how we make sure we never get into another token bonfire like the one
of 2026-09-12/13

## The intent

A runaway on the board is stopped by the board, within an hour, whatever its
shape — never by the subscriptions running dry.

## What happened, and what holds it now

Between 2026-09-12 18:52 and 2026-09-13 18:04 UTC the reading seat re-read
the same three Hello Revenue cards 850 times: 629 million tokens, 79 per cent
of everything ever spent from that checkout, across five subscriptions, until
every one of them hit its wall. Nothing on the board looked at the bill. The
cause is closed: the guard landed on 2026-09-13 (`6efa8db`, card #138's
item 1), the fuse is in #138's lane, and #138's Loop reads for thirty days
that no card is read more than twice on one text.

That closes one shape. The next runaway will have another — a lane that
loops on a retry, a reading ten times the size, a beat that opens the same
planning session again — and today it runs exactly as long as this one did:
until the wall. The runtime already counts what every session cost, after
the fact (`runtime/transcripts.py::tokens`, the rule `needle tokens` prints
and card #138's plan measured with); the beat never reads it
(`api/dial.py` names no token, spend or limit). `needle limits` reads a
slot's own wall, which is the thing this intent says must never be the stop.
The three suggestions about allowances (2026-09-11 and two of 2026-09-13)
are about coming back after a wall, not about stopping before one.

## What this proposes

The beat reads the machine's spend over the last hour, across every session
of every board, by the counting rule `needle tokens` already uses. Past a
bound, it opens nothing new — no reading, no planning session, no lane — and
the head says so in the owner's words: what the hour cost, what the bound
is, and what starts the board again (the hour falling under the bound, or him
raising it). Running lanes finish; nothing is killed. The bound is a number
beside the lane number in `domain/dial.py`, read the way the number is read,
and turned the way the number is turned.

The number is not guessed. Once the Defects columns have been read down and
the readings are the ordinary cost of the board, the machine reads a week of
hours and prints the busiest normal one; the owner rules the multiple. The
recommendation to bring to him: three times the busiest normal hour, because
the bonfire ran at roughly 26 million tokens an hour, which is what four
lanes and a reading seat should not reach in an ordinary hour, and a bound
that trips on an ordinary night is a switch he turns off again.

## Loop

We think a spend fuse on the rate, beside #138's fuse on the cause, stops the
next runaway within an hour of its start; if a week passes with the fuse
tripping on an ordinary night, the bound is too low and the multiple rises
rather than the fuse being removed; if a runaway of a new shape runs past an
hour without tripping it, the counting rule missed a session and the reader
is the defect, not the bound.
