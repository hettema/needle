# A session that ran out of allowance gives its memory back at once, so the machine has room to bring it back

**Kind:** defect
**Fix:** now — the intent is written (HOW-WE-WORK §11: a move that follows a machine fact is the machine's; the archived plan "a full machine admits nothing new and a lane that comes back is one lane", whose floor exists so that lanes flow without crashing the machine; and the owner's own words on 2026-09-09 15:40, "I want sessions to flow when they can without crashing the system, and I do want the sessions that have been building and are now stuck to get going again"); the fix stays inside the lane loop's rescue pass (`api/loops.py`, the park on the floor after a wall) and the runtime's stop; it removes the class — every walled session that waits for room while holding it — not the six lanes below.
**Found by:** the owner, 2026-09-09 15:24, from the walled window of Hello Revenue #456 ("It looks like session 9a7c49a7 is stuck"), and the session that read it

## The intent it breaks

Lanes flow when the machine has room, and the machine never crashes for them. The board holds the second half with a floor: no lane comes back until 5 GB has been free for a whole beat. It breaks the first half by itself: a session that hit its allowance has ended its turn and has nothing in flight, yet the board leaves it running, idle at its prompt, holding its memory, while it waits for the room that this very memory is part of. On a full laptop the six lanes that walled together at 15:15 sat for an hour with nothing wrong but the room, and the owner read them as stuck.

## Evidence

Read on 2026-09-09 between 15:24 and 15:45 from the served board, the registries and `/proc`.

- Six gmail lanes walled at 15:15 (`You've hit your session limit · resets 4:40pm`): Hello Revenue #409, #416, #419, #426, #456, #483. Each registry row reads `blocked … [wall: … → hrme]` or `→ hrclaude`: the hook filed the wall and chose the rung.
- Each card's face: *moving … the session on it ran out of allowance on gmail and is moving to hrme … the machine is full: 3.7 GB available, 5 GB needed … it comes back once the room has held for a whole beat.* The park's `waits_on` is `floor` (`api/loops.py::_park`, the `full=room` branch at the end of the rescue pass).
- The six walled processes are alive (`claude bg-spare …`, each in its `needle-card-<n>-….scope`, MemoryCurrent 75–172 MB at 15:44, PSS 150–270 MB resident plus 170–200 MB in swap each, from `/proc/<pid>/smaps_rollup`). Together about 1.1 GB resident and 1 GB swapped, on a machine reading 2.4 GB available and 10.4 GB of swap in use.
- The rescue pass (`api/loops.py` ~1040–1058) keeps the walled process alive on purpose while its wall is "young": `young = wall is not None and (now - wall.at) < RESCUE_HORIZON_SECONDS and session.pid is not None`, so that the rung the wall detector chose stays fresher than the rule's cache. The floor check comes after, and a full machine parks the lane with the process still running.
- A stopped session comes back only when the board can name its ending as the machine's: `_interruption` returns a cause for `LaneState.ENDED` only when `lane.cause in MACHINE_ENDED and lane.died`; `MACHINE_ENDED` holds `Cause.WALL` (`domain/ending.py:49`). So a hand `needle stop` on a walled session would read as the owner's stop and strand it, which is why nobody freed the room by hand.

## What would fix it

When the rescue pass parks a walled lane on the floor, the runtime stops the walled process first and records its ending as the wall (the death record's cause `WALL`, its words the wall's own line), so the memory is given back the moment the wait begins and the lane still reads as one the machine brings back. The rung the wall detector chose is kept on the handoff file, not on the live pid, so `young` reads the file's age rather than `session.pid`. A floor test shows a walled lane parked on a full machine with its process stopped, its face still "moving", and the lane relaunched on the chosen rung once the room holds; a second shows the six-at-once shape, where the room the first stop frees is counted for the next.
