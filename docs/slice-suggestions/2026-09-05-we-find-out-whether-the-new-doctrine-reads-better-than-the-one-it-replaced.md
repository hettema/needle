# We find out whether the new doctrine reads better than the one it replaced, before a bad month tells us

**Kind:** defect
**Fix:** his
**Found by:** the main thread on Omarchy #23, from the owner's question on 2026-09-05: "if interaction I have with you or codex feels notably worse than before then I guess our starting instructions are notably worse."

## Observation

Needle #54 rewrote the doctrine every session on this laptop obeys, and Omarchy
#23 deleted the 287-line text it replaced. Both cards closed with loops that
measure **delivery** and nothing else: `readlink -f` resolves to one text,
`needle add` says `entrance: one-text`, `machine check` reports no doctrine
finding. Every one of those is now green.

None of them can tell whether the new text is **better**. The words changed —
41 paragraphs dropped, 20 added, 5 moved to a steering section — and the only
thing standing behind "the new ones are at least as good" is that the owner
ruled the table row by row before the data existed. That is a good reason to
believe it. It is not a result.

By HOW-WE-WORK §7 this is a bet whose failure would be silent: nothing breaks,
no check refuses, sessions simply get slightly worse at the thing a dropped
paragraph used to hold, and the first signal is the owner noticing months later
that working with a colleague feels heavier than it used to. Silent, and
compounding, because every project on every machine reads this text.

## The owner's gut, and the number behind it

Asked the same day whether this should be measured, he added: *"My gut says
that how we work is too verbose. The core message is on point I think but not
every word earns its place. That is just a gut feel for me though."*

It is not just a gut feel. Counted:

| text | words | what read it |
| --- | --- | --- |
| `HOW-WE-WORK.md` before #54 | 1,947 | Needle sessions, via the board |
| the retired global `CLAUDE.md` | 2,683 | **every session, every project** |
| `HOW-WE-WORK.md` now | 3,259 | **every session, every project, both makes** |

Across both documents #54 consolidated 4,630 words into 3,259, a 30% cut, and
by that measure it did exactly what it set out to do. But the number a session
actually carries is the third row against the second: **the doctrine every
session loads grew 21%**, from 2,683 words to 3,259. The consolidation removed
duplication *between* the documents and added length *to the one that ships*.

So the owner's gut names a real and specific regression, and it points at the
`missing portable doctrine` rows — the 20 paragraphs #54 added — as where to
look first, since they are what grew it. The `drop` rows cannot be the cause;
they only removed.

This also has a mechanical cost, small today and worth stating: the text loads
into every Codex session's chain, which truncates silently at
`project_doc_max_bytes = 131072`. Card #23's +3,484 bytes left about 19%
headroom on Hello Revenue's deepest chain.

## Why the obvious fix is the wrong one

The tempting answer is a channel for the owner to say "that felt worse". It has
the exact defect this organisation just diagnosed in Hello Revenue's backbrief
hook (`from-e767e02e-doctrine-first-hit.md`, Q5): it fires only when he
remembers to reach for it, so it samples complaints and never the quiet
degradation, and §7 rules it out in a sentence — *the measure step never
depends on the person's memory.*

## Fix

**Run the comparison the model doctrine already prescribes, on the text instead
of the model.** The retired doctrine is not gone: `git show
7894dfc:home/.claude/CLAUDE.md` in `~/Work/omarchy-machine` is all 287 lines of
it. Both texts can be put in front of a fresh session **today**, so this does
not have to wait for a month of feeling.

Same brief, two fresh sessions of the same make and model, one entered on the
retired text and one on HOW-WE-WORK. **A third arm tests the verbosity
hypothesis directly:** the same brief on a trimmed HOW-WE-WORK that keeps every
intent and cuts the words that do not earn their place. If the trim wins or
ties, length was costing us and the trim becomes a card; if it loses, the words
were load-bearing and the owner's gut is answered with evidence rather than
deference.

The owner reads the arms' outputs shuffled and unlabelled, and says which he
would sign. Repeat across a small set of
briefs chosen to exercise the paragraphs that were **dropped**, since those are
where a loss would live — a backbrief on an ambiguous request, a plan, a report
of a partly-finished job, a technical call the session should make alone.

This is the blind method the model doctrine already defines for judging a model
("same brief, two sessions, Dennis reads both backbriefs without knowing which
wrote which"), applied to the variable that actually changed. It holds
everything else constant, which is what the transcript record cannot do —
cards 19, 20 and 23 and a model change all land inside the same before/after
window, so a raw rate comparison could never attribute a drop to the text.

Marked **his** because he is the instrument: the judgment is taste and his own
experience, which §7 says is the one thing to ask a person for — once, batched,
with the evidence attached. Everything around it (checking out the old text,
running the pairs, stripping the labels, presenting them shuffled) is a
session's work and should be done before he is asked for anything.

**If the new text loses on a brief, the fix is an edit to HOW-WE-WORK on a
Needle card, never a revert of Omarchy #23** — the link is right whichever text
wins, and the two questions are genuinely separable.

The standing watch that catches slow drift *after* this one-off comparison is a
separate suggestion on the machine's board: the doctrine names *corrections* as
its downstream quality measure and nothing counts them
(`omarchy-machine/docs/slice-suggestions/2026-09-05-the-board-can-see-when-sessions-start-needing-more-redirecting.md`).
