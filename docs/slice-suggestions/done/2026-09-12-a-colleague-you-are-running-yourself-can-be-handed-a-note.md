# A colleague you are running yourself can be handed a note

**Carried by:** docs/plans/done/2026-09-13-colleagues-ask-each-other-for-help-without-disturbing-each-others-work.md

**Kind:** defect
**Fix:** now — `docs/HOW-WE-WORK.md` §12 is the written intent ("a session that needs a colleague's judgment, or is asked for one, calls a colleague of either make warm through Needle's `call`"), the fix stays inside the call verb's ring beside the refusal it softens, and it removes the class — every interactive colleague of either make, bound to a card or not — rather than tonight's one Codex thread

**Found by:** the discuss session on Needle card #83 on 2026-09-12, after the owner asked why the coordination he had ordered with a Codex thread of his own had not happened

## The intent it breaks

The doctrine says a session that needs a colleague's judgment calls one warm,
and that a call is a row the loop reads. Today that holds only for colleagues
the runtime started. A session running in a terminal the owner opened himself
is refused by name — "runs in a terminal of its own; it is not resumed beside
itself" (`runtime/launch.py::call`) — and the refusal's own escape hatch,
"write the note and it hears it as its word", is `needle watercooler`, which
takes a project slug and a card number. A colleague bound to no card has no
address at all.

The refusal is right: resuming a session the owner is typing into would put a
second copy of that conversation beside the one he is using. What is missing
is the other half — a way to reach it that is not a resume.

## Evidence

The owner's ruling on card #83, 2026-09-11: "Owner asks coordination with Codex
01a08bd8-a899-7522-a848-5985072bffc7, which holds the experiment continuity
evidence." The card's own state line records the outcome: "Needle call to Codex
01a08bd8 was refused because it runs in its own interactive terminal; no
successful delivery or agreed ownership yet."

Asked about it on 2026-09-12, the honest answer was that the comms layer works
— two Codex workers were on the board's list that minute — and that it is blind
in exactly the spot he asked for. A colleague he can see on his own screen is
the one colleague we cannot say a word to.

## What would hold it

A note to a running interactive colleague, of either make, delivered where that
session reads its next word and recorded as the same row a call is, so the loop
reads it and `needle wait` can stand on it. Not a resume, so nothing is put
beside itself; not a card's channel, so a colleague bound to no card still has
an address.

Two edges it must respect. The owner's own terminal is his: a note lands as the
session's next word, never mid-turn, which is the refusal that already exists
for a session working on its turn. And a colleague on another machine still
cannot be called at all (`runtime/service.py::call`) — that gap belongs to card
#83's item 4 and is not this one.
