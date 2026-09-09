# Nothing at the top of the board is pushed off screen when the machine is full

**Kind:** defect
**Fix:** now — `docs/plans/done/2026-09-04-the-colour-language.md` item 1 writes the head as one line that holds the lens and the Idea box, and its ruling 5 says it stays one line; the fix stays in the head's own components and removes a class, text of no fixed width on that line, which the two `said` spans were each capped against by hand
**Found by:** the owner, from the board's Idea door on 2026-09-09 (conversation ef63c2aa)

## The intent it breaks

The line across the top of the board is one line that always fits: the project, the three words that filter the board, the auto-fix setting, the lens switch and the Idea box, all on screen at once. When the board says the machine is full, that warning is written into the same line, in full, and it may not shrink or wrap. On the laptop it is wider than the room left, so the lens switch and the Idea box are shoved past the right edge of the window, and because the page never scrolls sideways there is no way to reach them. The warning exists so the owner can read which session the machine is waiting on; today, while it shows, he cannot switch the lens or open an idea.

## Evidence

- `frontend/src/components/ui/index.tsx:226` renders the sentence as `dial-full` inside the auto-fix control, and `frontend/src/components/ui/primitives.css:151` gives it `white-space: nowrap` with no width cap. The two `said` spans beside it were capped one at a time (`primitives.css:130` at 420 px, `:152` at 260 px): the same failure met twice and fixed per instance, which is the method signal.
- `primitives.css:28` lays the head out as a flex row that does not wrap, and `:18` sets `body { overflow: hidden }`, so what overflows the row is unreachable rather than scrolled to. The head's own comment (`index.tsx:50`) says it never expands, so nothing catches the overflow.
- `board/dial.py:261` (`headroom`) composes the sentence: the numbers short of the floor, the floor, and the biggest session's name and what it holds, e.g. *the machine is full: 1.2 GB available, 0.8 GB swap free, 3 GB needed; hello-revenue #477's lane holds 3.4 GB, past the 3 GB floor* — some 120 characters, around 780 px at the head's 11 px mono, on a laptop whose viewport is 1600 px wide (`hyprctl monitors`: 2560 × 1600 at scale 1.6). The head without it already fills most of that width.
- `tools/scroll_check.py` is the only check that lays the head out (jsdom lays nothing out); it runs at 1440 × 900 and asserts the head does not move, never that its last control is inside the viewport. `frontend/tests/board.test.tsx:511` asserts the head's words and that the facts sit behind the project pill; nothing asserts the head's width holds under its fullest state.

## What would fix it

The head carries only text of fixed width. The auto-fix control keeps a short word in the broken colour — *machine full* — with the sentence as its tooltip, so the setting's state is read at a glance where the setting is. The sentence itself goes where the board already puts a long sentence about the machine: the alert strip under the head, beside the trunk note and the re-read error (`Board.tsx:383`), which wraps and never pushes a control. Rejected: an ellipsis on the sentence, because plan 53's reason for the sentence is that the owner reads *which* session the machine waits on, and an ellipsis eats exactly that; letting the head wrap to a second line, because ruling 5 of the colour language made the head one line that stays one line, and a head that grows brings back the fold it removed.

Held by two checks, so the class does not return: `tools/scroll_check.py` also loads the head in its fullest state (held, full, both `said` spans at their longest) at the laptop's size and asserts the Idea box's right edge lies inside the viewport, since only a laid-out page can say so; the vitest head test asserts the sentence renders in the alert strip and the auto-fix control shows the short word and carries the sentence as its title.
