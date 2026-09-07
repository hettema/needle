# Every plan carries the words that asked for it

**Kind:** defect
**Fix:** now — `docs/HOW-WE-WORK.md` §10 says a plan carries "the words that asked for it" (the owner's ruling of 2026-09-07 on row 43c of `docs/design/2026-09-05-hello-revenues-file-read-against-the-one-text.md`), and `docs/plans/README.md` does not name the field, so the contract and the grammar disagree; the fix is the grammar plus a reader that refuses a plan dated after this suggestion without the field or its written absence, which ends the class for every plan on every project rather than adding one field to one plan
**Found by:** the lane on card #60 (docs/plans/done/2026-09-05-every-session-of-any-make-follows-the-doctrine-at-least-as-well-as-hello-revenues-did.md), in the review's boundaries pass, from the owner's ruling

## Observation

The rebuilt one text's §10 lists what a plan carries: "the words that asked
for it, an intent, an effort gate that names why, a 'done means' per item …".
Needle's plan grammar (`docs/plans/README.md`) names Status, Written, Effort
gate, Sequencing, Carries, the done-means, Met/Deviated and Hands out — not
the ask. Hello Revenue holds the same intent with a head field,
`**Owner's words:** "<the ask, verbatim>" — <date>` or `none — <where the
plan originated>`, and a ratchet on plans dated on or after 2026-09-05.

## Why it matters

The ask that started a piece of work survives nowhere unless the plan records
it: the session that heard it is gone at the next start, and the Intent
section is already a translation. Hello Revenue counts amendments to the field
as its intent-drift measure. With the one text saying plans carry it and the
grammar silent, a session on Needle reads two contracts.

## Fix

`docs/plans/README.md` gains the field in Hello Revenue's form, with the
written-absence form so nobody manufactures a quote; `board/parse.py` reads it
onto the card beside the Written line; a ratchet refuses a live plan dated on
or after the day this lands without one of the two forms. Plans from before
are history and are not rewritten.
