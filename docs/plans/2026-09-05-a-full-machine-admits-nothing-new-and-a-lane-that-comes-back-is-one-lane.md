# A full machine admits nothing new, and a lane that comes back after a kill is one lane, not a subscription

**Carries:** docs/slice-suggestions/2026-09-05-a-lane-that-grows-toward-the-machines-ceiling-pauses-new-starts-before-oomd-has-to-kill-it.md, docs/slice-suggestions/2026-09-05-a-lane-resumed-after-a-kill-runs-in-its-own-scope-again-so-a-second-kill-takes-one-lane-not-a-subscription.md
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation 6b683c8b), folding two Up next cards born of one conversation into one lane
**Status:** PENDING
**Written:** 2026-09-05. Both suggestions came from card #50's close-out conversation the same morning, from the owner's one line: "I want to stop the machine from crashing and I want to work at max capacity." They are one loop pass: the board reads the machine on every pass, and a session it finds running outside its lane's scope it puts back. By the evening of the day they were filed, oomd had killed nine lane scopes and three daemon scopes on this machine (`journalctl`, 2026-09-05: gmail's daemon at 14:31Z with 106 processes, hrclaude's at 16:02Z with 236, hrme's at 17:59Z with 162), and each daemon-scope kill — the second suggestion's prediction — took every resumed lane on that subscription at once; the 17:59Z one ended four Hello Revenue lanes in one second.
**Effort gate:** high — the memory read and the adopt both exist (`board/dial.py::MEMORY_FLOOR_BYTES`, `api/dial.py::_full`, `runtime/machine.py::adopt`); the judgment is what the head says while the machine holds, and keeping the floor the owner's number.
**Sequencing:** none as a hold. The plan carrying #68 (the board's memory of how a lane ended, and the machine resuming what it ended) sequences after this card, because a resume that lands in a daemon scope rebuilds the pile this plan removes.

## Intent

The machine never reaches the point where oomd chooses, and a lane that is killed and comes back comes back as itself. The plan "as many lanes as the machine can hold" set a floor the dial reads once per beat, before it opens anything; nothing reads the machine while lanes run, and nothing reads where a resumed session runs. After this plan the lane loop reads the machine on every pass and admits nothing while it is full, the head says which lane is growing and how far, and a session with hands on a lane's worktree is in that lane's scope whoever put it there — so a limit or a kill is always one lane's, and the floor keeps meaning what the owner set it to mean.

What does not change: the floor is the owner's number and the dial never raises it (ruling 4 of the many-lanes plan); the board never stops or pauses a running lane — its move is to stop admitting and to say so (the first suggestion's rejection); ruling 5 there stands — a dead lane's session is left as evidence.

### 1. The machine is read on every pass, and a full machine admits nothing
The lane loop reads available memory and free swap on every pass, not only at the dial's beat, and reads each lane scope's memory beside it (`systemctl --user show -p MemoryCurrent`, through the runtime's one door to the machine). While either is under the floor, or any lane's scope has grown past the peak the floor was set from, the dial opens no planning session and no Start, and the head says which lane is growing and by how much. Done means: on the floor, a pass with the machine under the floor opens nothing and the head carries the numbers and the lane; the next pass with the floor satisfied opens again; the reading happens on every pass whether or not the dial is on a beat; the floor is read from the one constant the owner sets and no code path raises it. Hands out: `execution` — the fake `systemctl` under `tests/fakes/bin/` answers `MemoryCurrent` per scope and records its argv; verifies by reading the recorded argv before the reading is trusted.

### 2. A session with hands on a lane runs in the lane's scope, whoever put it back
On every read, a session with hands on a lane's worktree whose cgroup is not the lane's scope is adopted into it (`runtime/machine.py::adopt`, the call the launch already makes), under the scope's name as at Start, and the card says so in one row. The runtime's rescue after a wall already re-adopts; the machine's recover unit and a hand-resumed session take the same path. Done means: on the fixture, a session resumed outside its scope reads adopted after one pass and the card carries the row; live, a lane oomd killed and the machine's recover unit put back is found by `systemctl --user show needle-card-<n>….scope` within a minute of its return, and `/proc/<pid>/cgroup` of the resumed session names the lane's scope; the daemon scope holds no lane session after a pass.

### 3. The close reads the kills, before and after
Done means: the close-out tables oomd's kills from `journalctl` for the twenty-four hours before the fold and the twenty-four after, per scope kind (lane, daemon, other), with the memory and swap the kill line names; the memory held by lane scopes is read before and after, as card #50's close-out did. Hands out: `search` — the journal's kill lines and the scopes' `MemoryPeak`, as lines with their times; verifies by reading the two kill lines nearest the fold before the table is written.

## Terrain
- `board/dial.py` (`MEMORY_FLOOR_BYTES`, `is_quiet`, `why_left`), `api/dial.py::_full` (the once-per-beat read this plan makes every-pass), `api/loops.py` (the lane loop's pass), `runtime/machine.py::adopt`, `runtime/launch.py::scope_session`, `tests/fakes/bin/systemctl`.
- The two carried suggestions hold the evidence: the 10:59Z kill of #386 and its resume into `claude-daemon-hrme.scope`, and the floor that saw none of the growth.
- Proof of search: the memory read exists once (`api/dial.py::_full`) and the adopt exists once (`runtime/machine.py::adopt`); this plan widens when each is called, and adds neither a second reader of the machine nor a second way into a scope.

## Acceptance criteria
1. On the fixture, a pass under the floor opens nothing and the head says which lane and how far; the next pass above it opens again.
2. A session outside its lane's scope is adopted on the next pass and the card says so; live, a recovered lane is in its own scope within a minute.
3. The close-out carries the kill table for the day before and the day after, and the lane-scope memory before and after.
4. The suite, the ratchets and `tsc` are green.

## Loop
We think reading the machine on every pass and keeping resumed lanes in their scopes will change daemon-scope kills on this machine from three a day toward zero, and lane-scope kills from nine toward the few the floor honestly allows, because every kill today came after a beat let a lane in that then grew, and every daemon-scope kill held lanes that had come back outside their scope. Loop: daemon-scope kills in the journal — command `journalctl --user --since -1d --no-pager | grep -c 'claude-daemon-.*oom-kill'` expect 0 by 2026-09-13 every 1d. If lane-scope kills continue with the floor satisfied at every pass, the floor is below the lanes' real peaks and rises by the killed scope's peak, and the reading says so. If daemon-scope kills continue, item 2 missed a path a session comes back by, and the reading names it from the cgroup.

## Rulings
Recorded before the build, from the conversations; each overturnable by the owner on the card.
1. **The board stops admitting; it never stops a lane.** A lane's work is its own and the fold judges it. Rejected: pausing or killing the biggest lane when the machine is full — that is oomd with a friendlier face.
2. **The floor is the owner's number.** Rejected: a floor the board learns from the kills — a dial that turns itself was the first board's deepest trap (ruling 4, the many-lanes plan).
3. **One lane for two cards.** Both are the lane loop's read of the machine on one pass. Rejected: two lanes editing the same pass in the same week.

## Close-out
Written by the lane: a stance per item; the kill table; the memory before and after; the first recovered lane found in its own scope, with the time.
