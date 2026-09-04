# 03 — The doors and the loops

**Status:** DONE — built 2026-09-04 by the build session (Claude Fable 5.1 at high), reviewed in `docs/reviews/2026-09-04-the-doors-and-the-loops.md`, folded to `origin/develop` the same day. Behaviour 7 (the owner's own run of one Hello Revenue card) is his, and its verdict goes below when he has run it.
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

### 6. The fold reaches origin, and the checkout follows

Done means: a lane folds by fast-forward push to `origin/develop` from its own worktree (the worktree guard refuses local merges); the runtime keeps every registered project's main checkout level with `origin/develop` on a poll and after each fold, refusing — and saying so on the attention rail — when that checkout has uncommitted work that is not its own; `main` is promoted from `develop` at a slice close by the close door, never by hand; the card shows "folded, trunk synced, main synced" as three facts, each written only when true. This is Hello Revenue's convention (`develop` trunk, `main` stable, the main-sync ritual), adopted for every project on the board so one fold serves all.

### 7. Rescue, said out loud

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

Recorded as the build made them (Claude Fable 5.1 at high, 2026-09-04), each with the alternative rejected. The first is the coordinating session's launch instruction; the rest are the build's.

1. **The model rule and the limit detector stay in `claude-acct`; the doors and the loops ask and act.** A ratchet holds that a `Placement` is constructed only where the rule's answer is parsed and where the handoff is read. Rejected: a preview chooser for the Start button (two answers, 0.1's trap); the button reads the same call, cached.

2. **The board and the runtime meet in `api/`, in two modules: the doors and the loops.** The layers ratchet allows only `api/` to import both `board/` and `runtime/`, so that is where a card's lane is derived from the runtime's list and where a machine move is made. Rejected: a loop inside the runtime (it would have to know cards — the runtime stays pure of the board, plan 02); a loop inside `infrastructure/` (it cannot import the runtime without a reverse edge).

3. **A lane is the worktree named for the card, and it follows that worktree's whole chain of session ids.** Verified live 2026-09-04: `claude --bg --resume` forks the session id (a94f09d3 → d113504c on the same slot), and 0.1 had noted the same. So hands-on, windows and rescues are read across every session that has held the worktree, the ledger is written under the id that lives, and a session's dead id carries nothing. Rejected: keying the lane by session id (an Answer would orphan the card from its own resumed session); the floor's earlier fake that kept the id on resume, corrected to fork.

4. **The lane's state comes from the runtime's list, the registry's word and the hook's word together, and a Stop the hook pushed after the registry last moved wins.** Verified live: a resumed session read `blocked` with the previous life's detail after its own turn had ended; the registry also records a stopped question as `blocked` with the question as detail, so a question reaches the card even before the hook does. Rejected: the hook alone (a lane started before the hook was registered, or a killed session, would be dark); the registry alone (stale across a resume).

5. **Every door and every read of the machine take one lock.** A test that called the loop directly raced the registry watcher and opened two windows for one rescue; under the lock a rescue happens once and a door never acts on a lane the loop is moving. Rejected: per-lane locks (a door and a rescue on the same lane are the collision the lock exists to prevent, and one lock costs nothing at this scale).

6. **The machine's moves are the three-way exit 0.1 learned, with positive evidence of a death, and the machine never fights a hand move.** Into Executing on hands; out to Executed when the close landed in this life of the lane and the WATCH row names a signal, to Decision moment when the work folded but nobody wrote it up or the close has no readable signal, back where it came from when nothing folded; a card the owner took out of Executing after this life of the lane began stays where he put it and the card says hands are still on it. Rejected: Executed without a readable signal (Done is a closed loop; the card would sit where cards go to be forgotten); Up next as the only way back (the history says where the card came from).

7. **Fold evidence is the lane's tip in origin/develop and moved from its birth, with the birth recorded at the lane's first sighting.** Verified live: a stopped lane whose zero-commit branch had been deleted read as folded until the birth was recorded, because bare ancestry is true from birth. Rejected: the trunk's reflog (0.1's evidence, written by a local merge; the fold is now a push and leaves no merge entry); trusting `DELIVERED` alone (a row is a claim, the trunk is the fact).

8. **The WATCH grammar is one line: what, a reader, a target, a due date, a cadence.** Four readers — `url`, `file`, `command`, `owner` — and a refusal with the grammar in the message for anything else; a card cannot enter Executed without a row that parses, whoever moves it. Rejected: reading free text (0.1's WATCH rows were prose the board could only age); more readers (the three kinds the corpus uses, plus the owner's own reading, cover every WATCH row 0.1 holds; a new kind is a ruling).

9. **The hook is a standalone standard-library script that queues on disk and drains to the board, registered per project by `needle hook install`.** Rejected: `uv run needle hook` (a Python environment and a repository path per event, on every session's every stop); posting only (the board being down would lose the event; the queue is what makes lesson 3 true when Needle restarts).

10. **Rows are written by sessions through `needle row` and `needle close` into the store directly, and the running board hears the store change.** One writer, the store; the server's own writes bump the page and a write from outside bumps it through the file watcher and runs the lane loop. Rejected: the command line posting to the server (a session on a machine where the board is down could not write its own outcome); a second row store.

11. **`needle close` moves the card itself; the machine is the backstop.** The closing session is still alive when it closes, so the machine cannot read the exit yet; the close writes the rows and moves the card in one act and refuses Executed while the plan is live or the WATCH row names no signal. Rejected: waiting for the machine (the card would sit in Executing until the session ended, saying nothing).

12. **A signal only the owner can read is put to him at its due time as two buttons, and his reading is a reading.** Rejected: an owner signal aging silently (0.1's AGING chip at fourteen days was a reminder, not a loop).

13. **A discussion runs in the project root under its own session id, recorded so it never counts as hands on the tree, at xhigh.** Rejected: a discussion in the lane's worktree (two sessions in one tree, 0.1's #238); the card's own gate (talking a card through is thinking work, 0.1's rule).

14. **A dead lane whose worktree is gone is a card that can start again; one whose worktree stands offers Resume and Look.** Verified live: after the owner removed the worktree the card still said "already exists" until the door read the disk rather than the record. Rejected: the record's word alone.

15. **"Open the plan" stays in-card.** Slice 01's ruling 16 stands: the file renders on the card and proves itself by being there; an `xdg-open` through the runtime has no effect the board can prove. Rejected: the reader door as named in the plan.

16. **The journal speaks for a death only in a kill or a failure line; a scope's accounting lines are how every scope ends.** Verified live: a lane the owner stopped read "the journal says: Consumed 2.6 s CPU time" until the accounting words were dropped. Rejected: any journal line as the reason.

17. **The loops run once, in order, before the board is served, and their timers wait first.** A timer that ran its work at once raced the first request in the tests and read a card's signal between its close and the assertion. Rejected: timers that fire at start (the first read already happens in the lifespan).

## Close-out

Built 2026-09-04 by the build session (Claude Fable 5.1 at high). Review: `docs/reviews/2026-09-04-the-doors-and-the-loops.md`. Each acceptance behaviour, stanced before the fold, with the evidence. The live evidence is from two lanes run against the real machine with a throwaway store, a throwaway project and a real subscription (hrclaude, the one this build ran on): one plan whose intent said "reply READY, ask one question, reply THANKS", started, answered, watched and stopped through the API, twice.

1. **Start launches a lane the board sees at once, on the slot and model the button said** — met. The card's Start read "Start · fable on hrclaude — Fable headroom on hrclaude (62% of Fable used)", the same answer `claude-acct best --cached` gives; the click launched a94f09d3 at low in `card-1-say-ready-and-ask-one-question`, in `needle-card-1-say-ready-and-ask-one-question.scope`, verified in 8.3 s; `needle sessions` listed it with the worktree and the scope; the brief it opened with was the card rendered as text plus the gate line (`tests/api/test_doors.py`). A gateless card, a card outside Up next and Planned, a rule with nowhere to run, a dead launch (502 with the machine's words) and a collision (blocked, then overridden with the reason in the brief) are on the floor.
2. **The machine moves the card and says why** — met. Start moved the card into Executing with "hands on: a94f09d3 on hrclaude in card-1-…" as the machine, in the same second; Stop moved it back to Planned with "the lane ended with nothing folded (the session was stopped)". Executed when the close landed, Decision moment when folded but unwritten or when the WATCH row names no signal, a hand move out of Executing left alone, and a re-opened card's previous life not counting are on the floor (`tests/board/test_lane.py`, `tests/api/test_doors.py`).
3. **Sessions push; the card carries their words** — met. With the hook committed into the project, the lane's SessionStart, Stop ("READY\n\nWhich colour?") and SessionEnd events reached `/api/hooks` attributed to card #1, the queue drained to zero bytes, and the card read "Asking you: Which colour?" with the verbatim question and the attention line counted one asking. Before the hook was in the worktree the registry alone carried the question, so the card asked either way. The brief a lane opens with is `needle card --lane`; rows are written by `needle row` and `needle close` (`tests/infrastructure/test_store_doors.py`, `tests/api/test_hook_script.py`).
4. **The doors** — met. Answer "Blue." stopped a94f09d3 and resumed it as d113504c with exactly one live copy; the resumed session replied THANKS (read in its transcript and, in the second pass, in the hook's Stop). Watch opened `org.omarchy.board-watch-card-1-…` on workspace 3, proved by the compositor; a second Watch was refused by name; the window was closed by hand and the session kept working; after the close Watch was offered again. Stop ended the session in 1.4 s and said where the card was. Look and Discuss are on the floor (a window under `board-look-`/`board-discuss-` with the banner as its first line; Discuss never blocks Start). "Open the plan" stays the in-card render (ruling 15).
5. **Done is a closed loop** — met on the floor. A hand move to Executed without a WATCH signal is refused with the grammar; `needle close` writes DELIVERED, WATCH and REVIEW and moves the card in one act, refusing Executed while the plan is live; a `file` signal read as delivered moved the card to Done with the reading in its history; an unreadable `url` signal past its due date moved it to Decision moment with the finding; an `owner` signal at its due time opened the two-button question and counted on the attention line, and "Not delivered" moved the card to Decision moment (`tests/api/test_doors.py`, `tests/board/test_signals.py`, `tests/runtime/test_signal_readers.py`).
6. **The fold reaches origin and the checkout follows** — met on real git in temporary repositories: `needle fold` pushes HEAD to origin/develop and proves it by origin/develop equalling HEAD; the main checkout is levelled by fast-forward and refused, with the files named, when it holds uncommitted tracked work; `--main` promotes; a lane's fold is proved by its tip in origin/develop and moved from its birth (`tests/runtime/test_git.py`). Live, the throwaway project's trunk read "level with origin/develop" on the attention line. The first pass wrongly stamped a stopped lane "folded, trunk synced, main synced" — the zero-commit-branch hole, closed by ruling 7 before the second pass.
7. **Rescue, said out loud** — met on the floor, not live. A lane whose registry read `blocked` with a handoff filed was moved to beta, the card's history gained "Moved to fable on beta, new window opened." and a new window under the lane's app-id; a lane killed by SIGKILL with an OOM line in its scope's journal read "Lane ended … Killed process 4242 (claude)" with Resume and Look offered, and Resume brought it back (`tests/api/test_doors.py`). No real limit wall occurred during the build, as in slice 02.

**Behaviour 7 of the acceptance list (the owner's end-to-end run)** is his: with 0.1 stopped, start one Hello Revenue card from the page and watch it through Done; the verdict goes here.

**What this close leaves for the owner's read.** The hook is registered in Hello Revenue's `.claude/settings.json` beside 0.1's (commit 3d0a8269 on that repository's develop, not pushed) and in Needle's own; it posts to port 8480, so the served board must be the one at that port. The rescue walk and the OOM reason are proven on the floor only. The page's new elements — the band, the lane section, the doors row, the signal question — were built without a comp, because the plan's gate named where each door lives as the judgment the owner makes after use; the design system carries them and a ratchet holds it.

## Estimate

Execution clock: two lane-days. Actual: one session, 2026-09-04, about four hours. Gate clock: the owner's end-to-end run at the close, and one ruling on the signal readers if the three kinds prove insufficient.
