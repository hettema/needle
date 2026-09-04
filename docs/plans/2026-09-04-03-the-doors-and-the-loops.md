# 03 — The doors and the loops

**Status:** PENDING
**Written:** 2026-09-04, from `docs/INTENT.md` (one move is his, every other move is teamwork; Done is a closed loop) and from what 0.1's doors did on 2026-09-03.
**Effort gate:** high — the mechanics are specified by slices 01 and 02 and by 0.1's grammar; the judgment left is where each door lives on the card and what the card says at each moment, which the owner will judge in product terms after use.
**Sequencing:** after 02. This slice is the board using the runtime. When it lands, Needle replaces 0.1 for Hello Revenue and 0.1's service is stopped.

## Intent

The owner presses one button, Start, and everything else about a card's life happens without him: the card moves into Executing because hands are on it, out of it to where the work says, and on to Done when the signal it named arrives. From any card he can step into the running work, answer its question, or discuss it, and the card tells him what is happening in one sentence. Sessions write their outcome back to the card, and the next session reads it as its brief.

### 1. Start is one click, and the click is the gate

Done means: a card with an effort gate in Up next or Planned offers Start; the button says the slot and model the runtime's rule will actually use (the same function, not a second one); Start launches through the runtime in the card's own worktree named `card-<n>-<slug>`, with the card's brief as the prompt and the gate as the effort; a card with no gate is not startable and says why; a card whose plan's declared files overlap a running lane's is blocked with the collision named, and "Start anyway" is the owner's override with the reason in front of him; the click is the effort-gate confirmation and the brief says so.

### 2. The machine moves the card, and says why

Done means: a card enters Executing when a live session has hands on its worktree, and leaves it by itself: to Executed when the close landed (plan archived, DELIVERED written), to Decision moment when the work folded but no session wrote it up, back to where it came from when nothing folded; every machine move writes an audit row the card's history shows, with the reason in one sentence; the owner can move any card by hand and the machine never fights him, but a hand move out of Executing while hands are on it is named on the card.

### 3. Sessions push; the card carries their words

Done means: a hook registered in each project's Claude settings (session start, stop, end, stop failure) posts to Needle's API with the session id, the working directory and the last assistant message; the card shows the lane's state from those events and the runtime's session list together; a session that stops with a question puts the card in the attention rail as "asking you", with the question; the card's rows (DELIVERED, WATCH, REVIEW, WAITS, RULING) are written by sessions through the `needle` command line, never by editing the card file, and the brief a lane opens with is the card rendered as text.

### 4. The doors

Done means, per door, all reached from the card without leaving the board:
- **Watch:** a window into the live session, through the runtime, through the session's own slot; never offered on a session that is not live; closing it ends nothing.
- **Answer:** one sentence typed on the card resumes the lane with it, through the runtime's stop-then-resume; the card shows the answer in its history.
- **Discuss:** a fresh session in a window with the card's brief, on a slot and model the rule chooses, marked on the card as discussing so it never counts as hands on the tree; a discussion's "go" launches the lane the same way Start does.
- **Look:** offered only for a session live nowhere; opens a fresh session in the worktree with the transcript as context and says so in its first line.
- **Stop:** ends the session through its slot and says what state the card is now in.
- **Open the plan / the record:** opens the document in the owner's reader.
Every door proves its effect by evidence and fails loudly by name; none is a silent no-op.

### 5. Done is a closed loop

Done means: a card cannot enter Executed without a WATCH row naming its signal (what will be observed, where, and by when); Needle reads the signals it can (a URL returning a value, a file appearing, a command's output, a count in a project's own data) on a cadence the row states, and moves the card to Done when the signal says delivered, or to Decision moment with the finding when it says not; a signal only the owner can read is shown to him as a question in the attention rail at its due time, with one click each way; nothing sits in Executed past its due time without the board saying so.

### 6. Rescue, said out loud

Done means: a lane that dies on a model or subscription limit is moved by the runtime's rule and the card says "moved to <model> on <slot>, new window opened" at that moment; a lane that dies for any other reason (memory kill, exit, the machine restarting) carries the machine's reason in one line read from the journal or the job record, and the owner's choice is Resume or Look, never a guess; one automatic retry per run-out, and the ledger that holds that line is separate from the record of where the lane lives.

## What this slice does not do

It does not add a second project, a second owner, or any door not listed above. It does not replace the hook mechanism with polling. It does not build alarms about the written record beyond what slices 01 and 02 already raise (documents gone, documents without cards, sessions without processes).

## Terrain

- **0.1's doors, as the record:** in the Hello Revenue repository, `scripts/needle_board_server.py` — `start_lane`, `rule_card`, `answer_lane`, `watch_lane`, `look_at_lane`, `discuss_card`, `/api/talk`, `_launch_background`, `_refuse_open_lane`, `_resume_lane`, `_moved_sentence`, the reconcile that moves cards (`_mirror_plan_gates` and its siblings), `_verdict_for` and the footprint logic; `scripts/board_bridge_hook.py` (the session hook, the mailbox); `docs/board/README.md` for the column grammar's machine rules ("Executing is a machine fact", "shipped means archived", the three origins of a card). `tests/scripts/test_needle_board*.py` for every door's scenarios.
- **Needle's own:** `runtime/` (slice 02) for sessions, the rule, start, window; `board/` for moves and views (slice 01); the audit row and the corpus watcher already in `infrastructure/`; the `needle` command line for rows.
- **Hooks:** Claude Code's settings hooks (`Stop`, `SessionStart`, `SessionEnd`, `StopFailure`), registered per project in `.claude/settings.json`; the hook must never block a session and must survive Needle being down (queue on disk, drain on the next event).
- **The signal readers for item 5** are the one open design question; start with the three kinds the corpus already uses (a URL check, a file in `docs/plans/done/`, a count from a project command) and refuse the rest with a written decline, per the coverage rule.

## Acceptance criteria (behaviours)

1. Start on a gated card launches a lane whose session appears in `needle sessions` within the verify window, in a worktree named for the card, on the slot and model the button said.
2. The card enters Executing by itself within one read of the session appearing, and leaves it by itself when the lane folds, to the column its rows imply, with an audit row each way.
3. A stopped session with a question puts the card in the attention rail with the question; Answer resumes it with the typed sentence and leaves exactly one live copy.
4. Watch on a live card opens a tab that outlives the door; closing it leaves the session working. Watch is absent on a card whose session is not live; Look is present instead and its window's first line says it starts a new session.
5. A card cannot be moved to Executed without a WATCH row naming a signal; a signal that reads as delivered moves the card to Done with the reading in its history; a signal only the owner can read appears as a question at its due time.
6. A lane killed by a limit is moved and the card says where; a lane killed otherwise carries the machine's reason.
7. By hand at the close: the owner runs one Hello Revenue card from Start through Done in Needle, with 0.1 stopped, and writes the verdict in the close-out.

## Rulings

Recorded as the build makes them, each with the alternative rejected.

## Estimate

Execution clock: two lane-days. Gate clock: the owner's end-to-end run at the close, and one ruling on the signal readers if the three kinds prove insufficient.
