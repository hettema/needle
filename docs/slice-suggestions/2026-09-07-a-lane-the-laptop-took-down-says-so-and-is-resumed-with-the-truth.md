# A lane the laptop took down says so, and is resumed with the truth

**Found by:** the machine session, 2026-09-07 22:10, reading the board after the laptop's battery drained in flight (lid closed 18:51 on a low battery, normal sleep, power gone before 22:06; boot 5438b1ea)
**Kind:** defect
**Fix:** now — §11 is the written intent (*every other move is a machine fact with named evidence, or the board lies while they are away*) and §8's rule that a load-bearing claim says how it was known; the fix is inside `runtime/service.py::why_ended` and `board/lane.py`'s death line, plus `runtime/launch.py`'s `CONTINUE`; it removes the class — every session whose process vanished with a boot — not these four lanes.

## Observation

Four background lanes had hands on their work when the lid closed: Hello Revenue #459, #461, #462 and Needle #74 (their scopes started 18:14–18:37, never stopped, in the previous boot's user journal). After the reboot `needle lanes` reads every one of them as *Lane ended 3 h ago: the session finished its turn and was not resumed.* None finished a turn; their transcripts end at 18:51, mid-turn, and #74's worktree holds eight modified files. The board offered the same sentence for the oom-killed lanes' neighbours, so a reader cannot tell a lane that stopped from a lane the machine took down.

Bringing them back was `needle move <short>` on each dead session, which worked (all four alive in their own scopes within 6 s each). But a moved session with no wall is told `CONTINUE`: *"The subscription you were running on ran out, so the runtime moved you to one that has headroom — nothing else changed."* Neither clause was true: no subscription ran out, and everything changed — the machine rebooted, the clock moved three hours, and the lane's last turn is truncated.

## Evidence

- `journalctl --list-boots`: boot -1 ran 2026-09-03 01:54 → 2026-09-07 18:51; boot 0 from 22:06.
- `journalctl -b -1`: last lines are `Lid closed`, `Suspending...`, `Performing sleep operation 'suspend'`; no resume follows. `localsearch-3` logged *Running on LOW Battery, pausing* at 18:27.
- `journalctl -b -1 --user | grep needle-card`: `Started needle-card-74-…scope` at 18:16:24, `Started needle-card-461-…scope` at 18:37:33, #459 at 18:14:04, #462 at 18:15:02 — no matching `Consumed`/`Failed` line for any of them.
- `needle lanes needle` at 22:10: `#74 ended … Lane ended 4 min ago: the registry says: item 4 committed; wiring title reads into board flow. nothing folded.` — the registry's last line, but the *why* is the same fallback sentence.
- `runtime/launch.py:68` `CONTINUE`; `runtime/launch.py:600` "a resume after an answer or a death prefers to stay put" — a death is already a case the move knows, and it is given the wall's words.
- `claude-acct recover` (`~/.local/bin/claude-acct:1358`) drops its record when the pid is gone: *process gone, record dropped* — so nothing on the machine resumes a lane after a boot either; that half is filed on the machine's board as an idea (omarchy-machine `docs/slice-suggestions/2026-09-07-after-the-laptop-goes-down-every-session-comes-back-where-it-was.md`).

## Why it matters

The board's death line is what the owner reads to decide whether to resume, and *finished its turn* says "nothing to do here". Four lanes gated into execution sat as if they had chosen to stop. And a session resumed with a false reason will reason from it: check its allowance, believe its last tool result landed, not re-read a worktree the clock says is three hours older than its memory.

## What would fix it

A session whose pid belongs to a previous boot (the runtime can read `/proc/sys/kernel/random/boot_id` at record time and compare, or read `journalctl --list-boots`) died with the machine, and its lane says so: *the laptop went down at 18:51 (sleep, power lost) and came back at 22:06; the session's last turn is cut at 18:51.* The resume for such a session carries that sentence, not `CONTINUE`, and tells it to read its worktree before trusting its memory of it. `CONTINUE` stays for the one case it describes — a wall. The fixture gains a session from an old boot and asserts both the lane's line and the brief.
