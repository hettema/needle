# A card keeps its birth title after its document changes

**Carried by:** docs/plans/2026-09-04-08-identity-and-the-record.md — folded from the board's Idea door on 2026-09-05 (conversation 6b683c8b), which read it as plan 08's item 1 from the title's side
**Kind:** defect
**Fix:** now
**Found by:** the owner, from the board's Idea door on 2026-09-04 (conversation
56f7b05f), reading Up next after plan 11 landed: "I don't see that card? I
think something is wrong with card titles? Card #34 is the right one right?
That is the one at the top but the title doesn't show me at all what I think
the card is about."

## Observation

Card #34 on Needle's board was born from a suggestion titled *A standing
ruling lets a defect enter execution without him*. Plan 11 (*Defects fix
themselves*) then carried that suggestion, and the board did what plan 06,
item 7 says: the card became the plan's card. Its link now reads

```
link: {kind: plan, stem: 2026-09-04-11-defects-fix-themselves,
       title: "11 — Defects fix themselves"}
history: Linked to docs/plans/2026-09-04-11-defects-fix-themselves.md,
         which carries this card's suggestion.
```

and its face still says *A standing ruling lets a defect enter execution
without him*. The gate on the face is the plan's (`xhigh`); the title is the
suggestion's. The owner could not find the card he had just asked for.

`CardRow.title` (`infrastructure/schema.py:73`) is written once, at birth
(`infrastructure/store.py:500`, the `born` effect), and read for the face
(`store.py:1301`, `title=row.title`). The two effects that change what a card
cites both update `link_title` and leave `title` alone: the rename branch
(`store.py:390–397`) and the relink branch a carry produces
(`store.py:410–418`). So a card's face names the document it was born from
for the rest of its life, whatever it cites now — and the link beside it, which
the page does not show as the title, is the only place the truth sits.

## Why it matters

The title is how the owner ranks: *"I need to be able to derive from the card
title what the intent of the card is."* A plan's title is written to that bar
(`docs/plans/README.md`, the title rule); a card that hides it behind the
suggestion's working title defeats the rule at the one place it is read. And
it is the silent shape — nothing errors, the board shows a plausible title,
and the wrong card gets ranked.

## What would hold it

1. A card's title is the title of the document it cites, on every effect that
   changes the link — born, renamed, relinked — with the birth title kept in
   the history (the `linked` audit line already names the document; it can
   name the title change too).
2. A test: a suggestion's card carried by a plan reads the plan's title on
   its face and keeps its number; a renamed document's card reads the new
   title.
3. Nothing else on the face needs the rule: the essence line on #34 already
   reads the plan's intent ("INTENT says one move is the owner's…"), as does
   the gate — which is what makes the title the one stale word, and the face
   a card reading two documents at once.

## Adjacent

Plan 08, item 1 (*A rename keeps the card*) is about identity surviving a
rename; this is the other half — the face following the document — and the
two touch the same rename branch. Whichever lands second re-reads the other.
