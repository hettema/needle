# A full machine admits nothing new, and a lane that comes back after a kill is one lane, not a subscription

**Carries:** docs/slice-suggestions/2026-09-05-a-lane-that-grows-toward-the-machines-ceiling-pauses-new-starts-before-oomd-has-to-kill-it.md, docs/slice-suggestions/2026-09-05-a-lane-resumed-after-a-kill-runs-in-its-own-scope-again-so-a-second-kill-takes-one-lane-not-a-subscription.md
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation 6b683c8b), folding two Up next cards born of one conversation into one lane
**Status:** SHIPPED
**Written:** 2026-09-05. Both suggestions came from card #50's close-out conversation the same morning, from the owner's one line: "I want to stop the machine from crashing and I want to work at max capacity." They are one loop pass: the board reads the machine on every pass, and a session it finds running outside its lane's scope it puts back. By the evening of the day they were filed, oomd had killed nine lane scopes and three daemon scopes on this machine (`journalctl`, 2026-09-05: gmail's daemon at 14:31Z with 106 processes, hrclaude's at 16:02Z with 236, hrme's at 17:59Z with 162), and each daemon-scope kill — the second suggestion's prediction — took every resumed lane on that subscription at once; the 17:59Z one ended four Hello Revenue lanes in one second.
**Effort gate:** high — the memory read and the adopt both exist (`board/dial.py::MEMORY_FLOOR_BYTES`, `api/dial.py::_full`, `runtime/machine.py::adopt`); the judgment is what the head says while the machine holds, and keeping the floor the owner's number.
**Sequencing:** none as a hold. The plan carrying #68 (the board's memory of how a lane ended, and the machine resuming what it ended) sequences after this card, because a resume that lands in a daemon scope rebuilds the pile this plan removes.

## Intent

The machine never reaches the point where oomd chooses, and a lane that is killed and comes back comes back as itself. The plan "as many lanes as the machine can hold" set a floor the dial reads once per beat, before it opens anything; nothing reads the machine while lanes run, and nothing reads where a resumed session runs. After this plan the lane loop reads the machine on every pass and admits nothing while it is full, the head says which lane is growing and how far, and a session with hands on a lane's worktree is in that lane's scope whoever put it there — so a limit or a kill is always one lane's, and the floor keeps meaning what the owner set it to mean.

What does not change: the floor is the owner's number and the dial never raises it (ruling 4 of the many-lanes plan); the board never stops or pauses a running lane — its move is to stop admitting and to say so (the first suggestion's rejection); ruling 5 there stands — a dead lane's session is left as evidence.

### 1. The machine is read on every pass, and a full machine admits nothing
The lane loop reads available memory and free swap on every pass, not only at the dial's beat, and reads each lane scope's memory beside it (`systemctl --user show -p MemoryCurrent`, through the runtime's one door to the machine). While either is under the floor, or any lane's scope has grown past the peak the floor was set from, the dial opens no planning session and no Start, and the head says which lane is growing and by how much. Done means: on the floor, a pass with the machine under the floor opens nothing and the head carries the numbers and the lane; the next pass with the floor satisfied opens again; the reading happens on every pass whether or not the dial is on a beat; the floor is read from the one constant the owner sets and no code path raises it. Hands out: `execution` — the fake `systemctl` under `tests/fakes/bin/` answers `MemoryCurrent` per scope and records its argv; verifies by reading the recorded argv before the reading is trusted.
**Met:** `api/loops.py::Loops.headroom_now` runs at the end of every pass and at the start of every beat, and is the one reader the terminal uses too; it asks the user manager what each lane with hands on holds, by the scope name the lane was given at Start, through `runtime/machine.py::scope_memory` (`systemctl --user show -p Id -p MemoryCurrent`, one call for every lane). `board/dial.py::headroom` reads full when memory or swap is under the floor, when a lane holds as much as the floor, or when the lanes could not be read, and its sentence names the lane and the number. `tests/api/test_a_full_machine_admits_nothing_new.py` shows a pass with no beat reading a 5.5 GB lane as full with the lane named, the beat opening nothing while it stands and again once it shrinks, the argv the fake `systemctl` recorded, and an unreadable manager reading full; `tests/board/test_dial.py` holds the sentences. The floor is still the one constant, and no code path writes it.

### 2. A session with hands on a lane runs in the lane's scope, whoever put it back
On every read, a session with hands on a lane's worktree whose cgroup is not the lane's scope is adopted into it (`runtime/machine.py::adopt`, the call the launch already makes), under the scope's name as at Start, and the card says so in one row. The runtime's rescue after a wall already re-adopts; the machine's recover unit and a hand-resumed session take the same path. Done means: on the fixture, a session resumed outside its scope reads adopted after one pass and the card carries the row; live, a lane oomd killed and the machine's recover unit put back is found by `systemctl --user show needle-card-<n>….scope` within a minute of its return, and `/proc/<pid>/cgroup` of the resumed session names the lane's scope; the daemon scope holds no lane session after a pass.
**Met:** on the fixture, `api/loops.py::Loops._keep_in_scope` runs on every pass beside the wall rescue: a background session with hands on a lane whose cgroup is not the lane's scope is put back through `runtime/launch.py::rescope` — the same `scope_session` a Start makes, recorded the same way — once per session, and the card carries one `scoped` row saying what was asked and whether /proc shows it. The adopt now resets a scope the manager still holds as failed first (`runtime/machine.py::adopt`, `reset_failed`): verified on this machine 2026-09-07 that a killed lane scope lingers as failed, that `StartTransientUnit` under its name is refused with "was already loaded", and that it lands after `systemctl --user reset-failed`. The two fixture tests in `tests/api/test_a_full_machine_admits_nothing_new.py` show the reset, the adopt argv with the session's pid, the row, the recorded scope, and that a refused move is said once. The live half — a recovered lane found in its own scope within a minute, the daemon scope empty of lane sessions — is in the close-out below.

### 3. The close reads the kills, before and after
Done means: the close-out tables oomd's kills from `journalctl` for the twenty-four hours before the fold and the twenty-four after, per scope kind (lane, daemon, other), with the memory and swap the kill line names; the memory held by lane scopes is read before and after, as card #50's close-out did. Hands out: `search` — the journal's kill lines and the scopes' `MemoryPeak`, as lines with their times; verifies by reading the two kill lines nearest the fold before the table is written.
**Deviated:** the before half is met — the close-out below tables every oomd kill in the forty-eight hours before the fold, per scope kind, with the memory and swap each kill line names, and the memory the lane scopes held at 13:41Z; the two kill lines nearest the fold were read by hand before the table was written (2026-09-07 13:07:07+02:00, a desktop app scope; 2026-09-05 22:29:32+02:00, the board's own service). The after half cannot exist at the close, by construction: it is the card's WATCH signal — the plan's loop, the daemon-scope kill count over the day after, read by the board on 2026-09-08 and every day to the 13th — and the first recovered lane found in its own scope is what that reading, or the owner's next kill, will show.

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
We think reading the machine on every pass and keeping resumed lanes in their scopes will change daemon-scope kills on this machine from three a day toward zero, and lane-scope kills from nine toward the few the floor honestly allows, because every kill today came after a beat let a lane in that then grew, and every daemon-scope kill held lanes that had come back outside their scope. Loop: daemon-scope kills in the journal — command `printf 'daemon-kills=%s\n' "$(journalctl --user --since -1d --no-pager | grep -c 'claude-daemon-.*oom-kill')"` expect daemon-kills=0 by 2026-09-13 every 1d. (The plan first wrote the bare `grep -c`, which exits 1 on a count of zero, and the board's command reader takes a non-zero exit as not delivered — the one outcome the loop wanted would never have read as delivered; found at the close, 2026-09-07.) If lane-scope kills continue with the floor satisfied at every pass, the floor is below the lanes' real peaks and rises by the killed scope's peak, and the reading says so. If daemon-scope kills continue, item 2 missed a path a session comes back by, and the reading names it from the cgroup.

## Rulings
Recorded before the build, from the conversations; each overturnable by the owner on the card.
1. **The board stops admitting; it never stops a lane.** A lane's work is its own and the fold judges it. Rejected: pausing or killing the biggest lane when the machine is full — that is oomd with a friendlier face.
2. **The floor is the owner's number.** Rejected: a floor the board learns from the kills — a dial that turns itself was the first board's deepest trap (ruling 4, the many-lanes plan).
3. **One lane for two cards.** Both are the lane loop's read of the machine on one pass. Rejected: two lanes editing the same pass in the same week.

## Close-out
Written by the lane on 2026-09-07, before the fold. Items 1 and 2 met, item 3 deviated (the stances above); the review record is `docs/reviews/2026-09-07-a-full-machine-admits-nothing-new.md`.

**Two facts found on the way that the plan did not know.** A scope oomd kills stays loaded as `failed` — nine lane scopes and three daemon scopes stood that way on this machine when the lane began, eight lanes and three daemons at the close after the probe cleared #386's — and the user manager refuses a new transient unit under a failed name ("was already loaded"), so no killed lane could ever have been put back in its own scope, and no killed daemon back in its: the adopt now resets the failed unit first, verified live on the dead #386 scope (which the probe cleared). And the recover unit's resumed sessions were not the only strays the daemon scopes held: every lane session alive at 13:41Z (four: omarchy #22 and #38, Hello Revenue #452, this lane) was in its own scope, so the first pass of the new loop will move nothing — the proof of item 2's live half waits for the next kill.

**The kills, the forty-eight hours before the fold** (system journal, `Marked … for killing due to memory used (M) / total (16437264384) and swap used (S) / total (16436412416) being more than 90.00%`; times +02:00). The two nearest the fold were read by hand first; the rest by the search role and checked against the user journal's `Failed with result 'oom-kill'` lines.

| when | unit | kind | processes | memory used | swap used |
|---|---|---|---|---|---|
| 09-05 16:29:05 | needle-card-54-18-a-new-project-follows-the-way.scope | lane | 34 | 15.65 GB | 14.81 GB |
| 09-05 16:31:55 | claude-daemon-gmail.scope | daemon | 106 | 15.35 GB | 14.84 GB |
| 09-05 17:56:50 | needle-card-410-….scope | lane | 311 | 15.57 GB | 14.87 GB |
| 09-05 18:00:05 | needle-card-421-….scope | lane | 54 | 15.73 GB | 14.86 GB |
| 09-05 18:02:44 | claude-daemon-hrclaude.scope | daemon | 236 | 15.29 GB | 14.83 GB |
| 09-05 18:51:09 | hr-suite-422.service | other | some | 14.93 GB | 14.80 GB |
| 09-05 18:54:19 | needle-card-426-….scope | lane | 66 | 15.41 GB | 14.84 GB |
| 09-05 18:55:09 | hr-suite-422b.service | other | 15 | 15.28 GB | 14.82 GB |
| 09-05 19:03:58 | hr-suite-425.service | other | 16 | 15.78 GB | 14.81 GB |
| 09-05 19:09:50 | hr-card417-foldsuite.service | other | 91 | 15.39 GB | 14.80 GB |
| 09-05 19:57:59 | needle-card-429-….scope | lane | 66 | 15.18 GB | 14.84 GB |
| 09-05 19:58:46 | needle-card-430-….scope | lane | 50 | 15.14 GB | 14.80 GB |
| 09-05 19:59:30 | claude-daemon-hrme.scope | daemon | 162 | 15.19 GB | 14.80 GB |
| 09-05 20:37:47 | needle-card-435-….scope | lane | 57 | 15.31 GB | 14.84 GB |
| 09-05 20:57:58 | app-Hyprland-gtk-launch-21e31108.scope | other | 492 | 15.15 GB | 14.83 GB |
| 09-05 20:58:24 | card433-foldsuite.service | other | 90 | 15.38 GB | 14.81 GB |
| 09-05 21:32:51 | needle-card-436-….scope | lane | 127 | 15.28 GB | 14.80 GB |
| 09-05 21:35:01 | hr-suite-434.service | other | 10 | 16.00 GB | 14.87 GB |
| 09-05 21:55:30 | hr-suite-434d.service | other | 82 | 15.80 GB | 14.82 GB |
| 09-05 22:29:32 | needle-serve.service | board | 115 | 15.57 GB | 14.79 GB |
| 09-07 13:07:07 | app-Hyprland-gtk-launch-95c63ba9.scope | other | 545 | 15.35 GB | 14.82 GB |

Twenty-two kills in forty-eight hours: nine lanes, three daemons, the board once, nine other (seven hand-run suite services, two desktop app scopes). Twenty-one fell on the 5th between 16:29 and 22:29; the twenty-four hours before the fold hold one kill, a desktop app scope at 13:07 on the 7th, and no lane or daemon. Every kill line names the same shape: memory at 15.1–16.0 of 16.4 GB and swap at 14.8–14.9 of 16.4 GB — the machine at both ceilings at once, which is the state the floor exists to keep it out of.

**What the lane scopes held before the fold** (`systemctl --user show -p MemoryCurrent -p MemoryPeak`, 13:40Z). Active: this lane 0.8 GB (peak 1.3), Hello Revenue #452 0.2 (1.9), omarchy #22 0.4 (1.3), omarchy #38 0.3 (0.6), Needle's old #38 scope 0.0 (1.0); the daemons armana 0.3 (0.9) and eduard 0.5 (0.9). Failed, with the peak they died at: #421 5.8 GB, #429 5.8, #436 5.7, #435 3.3, #426 3.2, #430 3.0, #410 2.9, #54 1.7; the daemon scopes gmail 9.1 GB, hrme 6.8, hrclaude 5.3 — the pile item 2 removes. The machine at the same moment: 4.1 GB available, 7.6 of 15.3 GB swap free — under the 5 GB floor, so the served board reads full as this closes.

**What the after half will read.** The WATCH row on the card is the plan's loop: the daemon-scope kill count over the last day, expected 0, read daily to 2026-09-13. The after-table, the memory after, and the first recovered lane found in its own scope with its time are what those readings carry; the lane cannot write them before the fold.
