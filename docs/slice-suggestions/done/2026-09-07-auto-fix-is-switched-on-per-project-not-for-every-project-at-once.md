# Auto-fix is switched on per project, not for every project at once

**Carried by:** docs/plans/2026-09-12-auto-fix-is-switched-on-per-project-not-for-every-project-at-once.md — written at the board's Idea door on 2026-09-12 (conversation 147cb888), where the owner asked for it again in his own words and for its plan
**Kind:** idea
**Fix:** now — the owner ruled it on 2026-09-07 (below), and HOW-WE-WORK §11 already says which project's work enters execution is his ruling while how much the machine can hold is a machine fact; the fix is one field on the dial's setting (the project it is on for) with the memory floor and the lane ceiling left machine-wide, which removes the class — a dial that spends the machine on a board he is not looking at — rather than adding a filter to one beat
**Found by:** the owner, on 2026-09-07, after the laptop had been pushed past its memory twice: "when auto fix is running, I want it to run for the selected needle, not across needles."
**Formerly:** The auto-fix dial runs for the board you are looking at, not every board at once (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)

## Observation

- The dial is one setting for the whole board. `api/app.py` line 254 posts to `/api/dial` with no project in the path or body; `infrastructure/store.py::turn_dial` takes no project; the control renders in the app head on every project page (`frontend/src/board/Board.tsx` line 354) and acts on the same one setting whichever page is open.
- It picks across every project. `api/dial.py::_take_next` walks `self.live.projects` and sorts every project's candidates into one list by age (`board/dial.py::age_key`: born first, then number), so the oldest verified defect on any board is taken, one per beat, and its lane count is board-wide.
- So the page the owner is looking at says nothing about what the dial will start. He turns it on while reading Hello Revenue and it may start a lane on Omarchy or Needle; he cannot spend the machine on one project's rail without spending it on all of them. On a laptop that the board itself reports as full (4.6 GB available against a 5 GB floor, 2026-09-07), that is the difference between finishing one board's defects and killing lanes on three.
- The one project-specific rule that exists is an exclusion: Needle's own defects are skipped unless no lane anywhere has hands on work (`api/dial.py` line 295, `board/dial.py::is_quiet`), which #43 already files as a rail that may never drain.

## The intent it breaks

HOW-WE-WORK §11: the person gates what enters execution; everything else is the machine's. Which board's rail drains is his ruling, and today he cannot make it per board. The machine's part — the memory floor, the total number of lanes the laptop holds — stays the machine's and stays one number for the whole laptop.

## What would fix it

1. The dial's setting is per project: on or off, and a lane count, for the board the page shows; turning it on the Hello Revenue page starts nothing on Omarchy. The store keeps one row per project; the audit says which board he turned.
2. The memory floor and the sum of lanes across all turned dials stay machine-wide: a second project's dial does not double what the laptop admits, and the floor is read once per beat for all of them.
3. The head shows the dial for the board on the page and, in one quiet word, which other boards have theirs on, so he never has to remember. A board with its dial off shows its rail count and nothing more.

What this does not decide: whether Needle's own rail still waits for a quiet machine (#43, his).
