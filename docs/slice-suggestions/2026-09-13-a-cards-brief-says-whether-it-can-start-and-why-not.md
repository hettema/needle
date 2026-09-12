# A card's brief says whether it can start, and why not

**Kind:** defect
**Fix:** now — HOW-WE-WORK §11 says a column is a machine fact with its evidence, and this project's rule is that the routing state every reader shows comes from one source rather than each reader's own reading; `board/brief.py::render` is the face every session reads and it prints no readiness at all, so the state word and the closed door's sentence the page already computes are added there, which covers every state the brief omits and not the one hold that found it
**Found by:** the Discuss-door conversation on Needle card #42, 2026-09-13, after the brief's reader told the owner nothing was blocking a card the page was refusing to start

## The intent it breaks

The board has two faces: the page the owner reads, and the brief a session
reads through `needle card`. They are meant to be the same board. The page
shows a card's readiness — the state word and, when a door is closed, the
sentence saying why — because a card that cannot start is a fact about the
card, not a decoration on a button.

The brief shows none of it. `board/brief.py::render` prints the column, what
the card serves, its rows, its gate, its handouts and their verdict, the
document, the citations, the folded suggestions and the lane's name. It
never prints `detail.readiness`, nor the doors, so a session cannot see from
the board's own reader that the board is refusing to start the card.

## Observation

Needle #42's Sequencing line reads "after 12 … and 13", Needle's own plan
numbers, which no board holds. Card #69's item 4 gave the board the words for
exactly this: the page shows `hold unread` and closes Start with "Something
is wrong: its Sequencing line means a hold on '12' and '13', which the board
cannot place, so it cannot start."

`uv run needle card needle 42` on the same card, the same minute, printed
twelve lines and not one of them said so. The session read the brief, saw a
card in Planned with a high gate and no impediment, and told the owner the
card was waiting only on his click. He had the page open in front of him with
the refusal on it.

## Why it matters

A session that cannot see a closed door reports the card as startable, and
the owner is the one who finds out. Worse, a session that tries to start it
meets the refusal at the door with no idea why the board is saying no, and
the plan-side fix — which is one line in a head field — looks like a bug in
the board.

The failure is silent in the direction that matters: the brief omits, it does
not lie, so nothing about the output looks wrong.

## What would hold it

`render` prints the readiness the page shows — the state word, and, when a
door is closed, its sentence — from `detail` as the page reads it, never from
a second reading of the plan. A test on the fixture board holds that a card
whose Start is closed says so in its brief, in the same words the page uses.

## Rejected

Printing only the doors' labels: the label without the sentence is the button
without its reason, and the sentence is the half a session needs to act.
