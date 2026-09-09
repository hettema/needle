# The words under a suggestion's head are never read as part of its head

**Kind:** defect
**Fix:** now — plan 11's item 6 (`docs/plans/done/2026-09-04-11-defects-fix-themselves.md`, "whether a defect was filed against it") and #48's definition of *against* ("a suggestion whose finder is someone else and whose head names the card") are the written intent, and a head line ends at the blank line under it in every reading of the shape `docs/plans/README.md` teaches; the fix stays inside `board/parse.py::_head_fields`, which today joins every non-heading line before the first section into the last head field across blank lines, and removes the class on every board — a blank line ends the head, as a section heading already does
**Found by:** #34's reading, 2026-09-09

## The intent it breaks

What a suggestion says about who found it is one line at its top, and the board acts on that line: it decides whether a fix was later found wanting, and who is filing defects. Today the board reads a suggestion's opening paragraph as part of that line whenever the paragraph comes before the first section heading, so a card mentioned in passing in the paragraph counts as a card the suggestion was filed against. On Hello Revenue that makes the fix on #402 read as undone when nobody filed anything against it, and fourteen live suggestions on two boards carry their opening paragraph inside their last head line.

## Evidence

- `needle fixes all`, read 2026-09-09: `hellorevenue #402 … defect filed against it`. No live suggestion in Hello Revenue's docs/slice-suggestions has a Found by line naming #402 or its lane; the one match is `2026-09-05-every-branding-derivation-can-be-read-on-its-own-even-one-that-retried.md`, whose Found by says *the lane on card #433* and whose opening paragraph, two lines below a blank line, mentions "the WATCH reader on card #402". Parsed with the board's own `_head_fields`, its Found by value is that line plus the whole paragraph.
- `board/parse.py::_head_fields` (its docstring: "continuation lines joined") appends any non-empty line that is not a heading to the last field until it meets `## ` or `---`; a blank line does not end the field. No test pins that rule either way (searched `tests/` for `_head_fields` and `continuation`, 2026-09-09: nothing).
- Counted the same way on 2026-09-09: 7 of Hello Revenue's 47 live suggestions with a Found by line and 7 of Omarchy's 12 carry their opening paragraph inside a head field; Needle's own 32 carry none, because its filing brief opens the body with a section heading.
- `api/dial.py::fixes` searches that value for the card's number or its lane name to set *defect filed against it*; `board/dial.py::filer_of` reads its opening words for the filer count. Both read the paragraph as the line.

## What would fix it

A head field ends at the first blank line, the way the section heading already ends it; a wrapped line with no blank line between still joins, so a long Found by written over two lines keeps reading as one. A test feeds a head followed by a blank line and a paragraph and asserts the paragraph is not in any field, and one with a wrapped line and asserts it is. Every reading of a head field on every board is corrected by that one change; the fourteen suggestions need no edit.
