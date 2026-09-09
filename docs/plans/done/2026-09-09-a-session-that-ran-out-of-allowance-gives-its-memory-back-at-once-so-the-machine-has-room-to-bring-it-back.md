# A session that ran out of allowance gives its memory back at once, so the machine has room to bring it back

**Status:** DONE — shipped 2026-09-09 by the lane on card #107 (the interactive session hrme 89b15944, at the owner's word); every item stanced below.
**Written:** 2026-09-09, from the owner's words on the same afternoon. First, at 15:24, with a screenshot of Hello Revenue #456's window: "It looks like session Claude:9a7c49a7 is stuck? it's been going for a long time. Will claude-acct-auto pick it up and switch it to an account that isn't hitting its limit?" Then: "Same issue for Claude:a5c9d649." Then, on the brief that the six lanes were waiting for room that their own idle processes held: "I don't really understand the things you spoke about with the stuck sessions. I want sessions to flow when they can without crashing the system... And I do want the sessions that have been building and are now stuck to get going again." And on the two rulings put to him: "1. yes. 2. I have no idea if 5gb is good or bad, it's a tech thing so you own it :) I can say that we have had crashes since we introduced it I think."
**Carries:** docs/slice-suggestions/2026-09-09-a-session-that-ran-out-of-allowance-gives-its-memory-back-at-once-so-the-machine-has-room-to-bring-it-back.md
**Effort gate:** medium — the code is one stop moved earlier in a pass that already exists and one property on a call that already exists; the judgment is the floor's number, which the owner handed over on 2026-09-09, and it is written here with its reason and its loop rather than guessed again next month. A wrong stop costs a lane one resume from its own transcript; a wrong number costs him either idle lanes or a killed browser, and the loop below is what tells the two apart.
**Sequencing:** none holds this. Beside `docs/plans/2026-09-05-16-every-loop-a-plan-names-is-watched-until-it-closes.md` (the `Loop:` lines below are read as prose until that plan folds, and become WATCH rows at the close after it).

## Intent

The owner's two halves, in his words: sessions flow when they can, and the
system does not crash. The board holds the second half with a floor (the
archived plan "a full machine admits nothing new and a lane that comes back
is one lane", 2026-09-05): no lane is started or brought back until 5 GB of
memory has been free for a whole beat. It breaks the first half by itself: a
background session that hit its allowance has ended its turn and has nothing
in flight, yet the board leaves it running, idle at its prompt, holding its
memory, while it waits for room that this very memory is part of. On
2026-09-09 six Hello Revenue lanes walled together at 15:15 and sat parked
for an hour with nothing wrong but the room; their idle processes held about
1.1 GB resident and 1 GB of swap on a machine reading 2.4 GB available.

The crashes he remembers are real and are not the floor's doing. Three times
since 2026-09-08 the userspace out-of-memory killer took an application when
memory and swap both passed 90 percent of the machine (`journalctl -u
systemd-oomd`: 09-08 13:29 and 09-09 15:06 a Chromium window, 09-09 13:50 VS
Code). The floor gates only what the board admits; it does nothing once
lanes have been admitted and grow, and it does not decide who is killed when
the machine is full — the killer takes the biggest thing it can see, which
is his browser. The number stays 5 GB, and this plan writes why: it is a
third of a 15.6 GB laptop that already runs a browser, an editor and half its
swap, and lowering it trades idle lanes for a slower machine, not for a
crash; what stops the crashes is that lanes, which come back by themselves,
are the thing the machine sheds first and never his own windows. That part
belongs to the machine's own record and is filed there as a defect by this
plan, not built here.

After this plan: a session that ran out of allowance gives its memory back
the moment the board starts waiting for room, its card says it is coming
back and what it waits on, and it comes back on the account the wall chose
as soon as the room holds, or on the rule's if that account's own reading
says its allowance has since gone. A lane is throttled at the floor before
anything else is: its own space carries the floor as its high mark, so a
runaway lane presses on itself first rather than on the browser — a
throttle, which the kernel may still let it exceed under pressure, never a
cap. The floor's number and its reason are written where the board reads
them, with a loop that says whether the kills stopped and whether the lanes
flow.

## Items

1. **A session that ran out of allowance gives its memory back at once.**
   When the rescue pass parks a walled background lane because the machine
   is full, it stops the walled process first and says so on the card, so
   the wait begins with the memory returned. The stopped session still reads
   as a wall (the death is named from the standing handoff, not the
   registry's "stopped"), the rung the wall detector chose is kept from the
   handoff's age rather than from a live pid, and the lane is brought back on
   that rung once the room holds. Done means: on the floor, a walled lane
   parked on a full machine has its process gone in the same pass, its face
   says it is coming back with the wait's words, and after the room holds for a beat
   it is relaunched on the handoff's account; the six-at-once shape shows the
   room the first stop frees counted for the next. Hands out: execution — the
   floor suite and the api suite; verifies the failing test's file and line
   before touching anything.
   **Deviated:** met on every clause but the last — `api/loops.py::Loops._give_memory_back`, called at the floor park in the rescue pass, and `tests/api/test_work_the_laptop_interrupted_comes_back.py::test_a_walled_lane_on_a_full_machine_gives_its_memory_back_and_comes_back_on_the_handoffs_rung` shows the process gone in the parking pass, the ending named a wall on the next, and the relaunch on the handoff's account (beta) once the room held; the face after the stop reads "coming back", the board's word for a parked lane whose process is gone, not "moving", which is the word for a live one. The six-at-once clause is held by the pass reading the machine afresh for every lane (`self.headroom_now()` inside the loop over lanes) and is not shown by a test: the floor's memory is a file the pass reads, and a test that changes it between two lanes of one pass would be testing the test. The execution role was not dispatched: the suites were run by the building session, with the lane's own `uv run pytest`.

2. **A lane is throttled at the floor before anything else is.** Every
   lane's space is created with the floor as its high mark, so a lane past
   it is throttled and reclaimed inside its own space first — a throttle the
   kernel may still let it exceed under pressure, never a kill — and is
   never, by itself, the reason a window is. Done means: after Start, the
   manager's own reading of the lane's space (`systemctl --user show <scope>
   -p MemoryHigh`) says the floor's number, the floor test records the
   property on the adoption call, and a lane at the mark still reads as
   full on the head with its name, as today.
   **Met:** `runtime/machine.py::adopt` takes `memory_high` and every lane adoption in `runtime/launch.py` passes `MEMORY_FLOOR_BYTES`; the floor test asserts the property on the adoption call (`tests/api/test_a_full_machine_admits_nothing_new.py`); rehearsed 2026-09-09 15:5x on a throwaway scope of this machine's user manager (systemd 261), where `systemctl --user show -p MemoryHigh` read 5368709120 after the call. Read live a minute after the fold: Hello Revenue #409's scope, adopted by the loop, read 5368709120; #483's, which stood before its session was put back and took the next in, read infinity — so the loop now reads every lane's scope's mark on every pass and sets it where it is missing (`runtime/machine.py::hold_scopes_at`, from `Loops.headroom_now`, said once on the card); the second live reading, after that fix folded, is in the review record's last section.

3. **The floor's number carries its reason and its loop, and the machine is
   asked to shed lanes first.** The constant's docstring says why 5 GB, in
   the words above, and names this plan; a defect is filed in the machine's
   record asking that his own windows be marked as the last thing the
   killer takes, with the three kills as evidence. Done means: the docstring
   reads the reason and the date, the machine's suggestions folder holds the
   defect with `**Kind:** defect` and a `**Fix:**` line, and both loops
   below stand as WATCH rows at the close.
   **Met:** `domain/dial.py::MEMORY_FLOOR_BYTES` carries the number with its history and the 2026-09-09 reason (it moved from `board/dial.py` because the runtime sets it and cannot import the board); the machine's defect is `/home/dennis/Work/omarchy-machine/docs/slice-suggestions/2026-09-09-when-the-laptop-runs-out-of-memory-it-lets-go-of-a-background-session-before-a-window-you-are-using.md` (commit 0de0913 there); the two loops are written as WATCH rows at the close.

## Terrain

- `api/loops.py`, the lane loop's rescue pass (`Loops._rescue…`, the
  `young` gate and the `full=room` park at its end; `_park`; `_park_lifts`
  for the floor's wait; the resume through `self.runtime.resume`).
- `runtime/reasons.py::cause_of`: a session whose handoff stands is named a
  wall death before anything else, so a stopped walled session is brought
  back; `domain/ending.py::MACHINE_ENDED` holds `Cause.WALL`.
- `runtime/launch.py::move` and `::stop`: a move stops only a live pid and
  takes the rung from the handoff when it is given none.
- `runtime/machine.py::adopt`: the `StartTransientUnit` call with `PIDs`;
  the ceiling is one more property on it. `board/dial.py::MEMORY_FLOOR_BYTES`
  is the number.
- Tests: `tests/api/test_a_full_machine_admits_nothing_new.py` (the floor,
  the fake `systemctl` and `busctl` under `tests/fakes/bin`),
  `tests/api/test_work_the_laptop_interrupted_comes_back.py` (walls, parks,
  `Floor.write_handoff`), `tests/floor.py`.
- The machine's record: `/home/dennis/Work/omarchy-machine`, its
  `docs/slice-suggestions/` and `home/.config/systemd/user/app.slice.d/50-memory-guard.conf`
  (the 11 GB ceiling on all applications, 2026-09-03, which is why pressure
  becomes swap and swap becomes the kill).

## Acceptance

- A walled lane on a full machine: its process is gone within the pass that
  parks it, the card says it is coming back and what it waits on, and it
  comes back on the wall's account once the room holds — unless that
  account's own latest reading says its allowance is gone, then on the
  rule's.
- A lane parked on the floor before this landed, its walled process still
  standing: stopped on the next pass, and said once.
- A walled lane on a machine with room: unchanged, moved in the same pass as
  today.
- A hand `needle stop`, or the Stop door, on a walled session: the owner's
  stop; the handoff is removed with it, so the lane stays down.
- Every new lane space reads `MemoryHigh` equal to the floor.
- The suite is green and the ratchets hold.

## Loops

Loop: an application window killed by the machine's out-of-memory killer in the last day — command journalctl -u systemd-oomd --since -24h -o cat | awk '/Marked .*app-(Hyprland|code)/{n++} END{print n+0}' expect 0 by 2026-09-23 every 1d
Loop: a walled background session still alive while its card waits for room — command uv --project /home/dennis/Work/needle run needle sessions | awk '/blocked +background/ && /wall:/{n++} END{print n+0}' expect 0 by 2026-09-23 every 1d
