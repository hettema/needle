# 15 — A card that finishes or needs you rings, and stays on screen until you dismiss it

**Found by:** the owner, from the board's Idea door on 2026-09-04 (conversation 1ae6dcc3)
**Status:** PENDING
**Written:** 2026-09-05, from the owner at Needle's Idea door: "can we play a sound and show a notification I have to dismiss when a card finishes executing?" He agreed with the shape proposed back — the popup says where the card went and why, carries one button that puts the board in front of him, and a running card that asks him a question rings the same bell — and asked for the card in Up next.
**Effort gate:** low — one runtime door, one audit kind, and a call at the two places the board already decides the thing worth telling him. The judgment is which moments ring, and that is ruled below; everything else has a fixture.
**Sequencing:** beside 14 (both add a call in `api/loops.py`; 14 counts signals, this one tells him at the machine move; no function is shared). Nothing else waits on it.

## Intent

INTENT says the owner watches the team's moves and that one move, Start, is his. Today the board learns a lane ended within a minute and moves the card on; the owner learns it when he next looks. Between the two, a free slot sits idle and a question sits unanswered, and nothing on this machine tells him. The machine already knows how to interrupt him for what cannot wait: the account watcher raises a critical notification with no timeout, quickshell keeps it on screen until pressed and offers a button (omarchy plan 08, "a signed-out account says so"). Needle has never used it.

What will be true when this is done: **the moment the board moves a card out of Executing, or a running card starts waiting on him, a sound plays and a notification that says where the card went and why stays on screen until he dismisses it, with one button that puts the board in front of him.** Nothing rings for a move he made himself: he was there.

## What rings, in three lines

- **The board's own move out of Executing** — folded and closed, closed with no signal the board can read, folded but not written up, ended with nothing folded (and how it died: a wall, a crash, a worktree gone). The popup carries the move's own words, the detail the audit row already holds.
- **A running card that starts waiting on him** — the lane's state turns to one the board shows as *waiting on you* (asked a question, stopped, hit a prompt) and the board does not already call the lane spent. The popup carries the question's last line, or that it stopped.
- **Never his own move, and never twice for one thing.** A stop that becomes an exit inside the same minute is one ring, the exit's.

### 1. The runtime can tell him

Done means: the runtime has one door, `tell`, that takes a typed notice (project, card number, title, the words, whether the card moved on or needs him) and raises it through `runtime/machine.py` as `notify-send -u critical -t 0`, app name Needle, summary `#<n> <title>` on the project, body the words, one action *Open the board*. `notify-send --action` blocks until the notification is answered or dismissed, so it is spawned detached and the runtime never waits on it. Pressing the button focuses the board's window through the compositor door the runtime already has (`present` and `focus_script` in `runtime/windows.py`, on the app-id the board's desktop entry gives its Chromium window) and launches that desktop entry when no such window exists. At the same moment `pw-play` plays a stock freedesktop sound: `complete` for a card that moved on, `message-new-instant` for one that needs him. A machine without `notify-send` or `pw-play`, or a notifier that refuses, is one warning in the log and a `told` row (item 2) reading *could not tell you: <why>*; nothing rises up the loop. Fakes for `notify-send` and `pw-play` under `tests/fakes/bin/` record their argv on the floor, the way `hyprctl` and `omarchy-launch-tui` do.

Rejected: the page raising a browser notification from the stream — it needs the tab open and its audio unmuted, fires once per open tab, and the browser's dismissal is not the desktop's. Rejected: the session's Stop hook raising it — the hook cannot know whether the fold landed, and a popup that contradicts the board is the 2026-09-04 09:31 incident, when one told him to relaunch a lane the board had already moved.

### 2. Every machine move out of Executing rings, and leaves its trace

Done means: in the loop's machine moves, a move out of Executing by the machine calls `tell` with the exit's column and reason once the store has taken the move, and the card's record gains an audit row of a new kind, `told` (searched: `ended`, `stopped`, `moved` and `signal` say what happened; none says the owner was told), whose detail is the popup's words or why it could not be raised. The ring is owed while the card's last machine move out of Executing has no `told` row after it, so a crash between the move and the ring rings at the next reconcile, and a second reconcile of the same exit rings nothing. On the floor: a lane that folds and closes rings *the close landed…* as the card enters Executed; one that dies rings with the machine's reason; a wall with nothing folded rings; the owner's own Stop, drag or answer rings nothing; the same exit reconciled twice rings once. The `told` row shows on the card's face like any row, so the record says what he was told and when; the kind reaches the page through the typed mirror (`api/typegen.py`), no new component.

### 3. A card that starts waiting on him rings the same bell

Done means: when a reconcile finds a lane in a *waiting on you* state (the set `board/assemble.py` already holds) that the board does not call spent, and the card's last `told` row is older than the hook event that put it there, `tell` is called with the question's last line (or *stopped without a question*, or *waiting on a prompt*) and the `told` row is written. A new question is a new ring; the same question seen again is not. A stop followed by the session's end inside one short grace — one constant, named with its why — is one ring, the exit's. On the floor: a Stop hook whose last message ends on a question rings with that line; a second reconcile rings nothing; a Stop then a SessionEnd within the grace rings once, with the exit's words.

### 4. The measure exists before the change does

The thesis: we think a popup that stays until dismissed and says what happened will shorten the time between a card leaving Executing and his next act on that project, because today that time is however long until he looks at the board. Done means: before the lane's fold, the executing session computes from the audit trail the median minutes, over the fourteen days before the fold, from a machine move out of Executing to the owner's next act on the same project (a Start, an answer, a move), on Hello Revenue's and Needle's boards, and writes it into this plan's close-out. The WATCH row is `session — after twenty told rows across the boards, read the audit trail for the same median, after`. The readings, named now: if the median halves, the ring holds and the sound stays; if it does not move and the popups were dismissed within a minute of appearing, the ring is noise and becomes a sound alone; if it does not move and the popups sat for hours, he was away, the ring is not the fix, and the reading says so rather than tuning it.

## Terrain
- `runtime/notice.py` (new: the notice type and `tell`; the only file that names `notify-send` and `pw-play`), `runtime/service.py` (`tell`), `runtime/windows.py` (the focus, reused by the button), `api/runtime_cli.py` (the verb the button's action runs, so the focus is one command), `api/loops.py` (the two call sites), `domain/audit.py` (`TOLD`), `infrastructure/store.py` (the row), `frontend/src/` (the mirrored kind; the record renders it as any row), `tests/fakes/bin/notify-send` and `pw-play`, `tests/runtime/`, `tests/api/`.
- The desktop entry and the notifier are the machine's (`~/Work/omarchy-machine`): read and reused, never changed here.
- Hello Revenue's and Omarchy's boards ring through the same code; the popup names the project.

## Acceptance criteria
1. On the floor, a `tell` leaves one `notify-send` argv with `-u critical -t 0` and the action, and one `pw-play` argv naming the sound; with the fakes off PATH it leaves a `told` row saying why not, and the reconcile finishes.
2. A folded-and-closed lane, a dead lane and a walled lane each ring once with the exit's words; the owner's own moves ring nothing; the ring and the `told` row cannot disagree.
3. A question rings once with its last line; a stop that ends within the grace rings once.
4. Live, on this machine: a card of the fixture project started and stopped by hand puts a notification on screen that stays until dismissed, plays the sound, and its button puts the board in front of him.
5. The baseline median is in the close-out; the suite, the ratchets and `tsc` are green.

## Rulings
Recorded before the build, from the conversation; each overturnable by the owner on the card.
- **The popup says where the card went and why, never "finished".** A card leaves Executing four ways and each asks something different of him; a bare "done" sends him to the board to find out which. He agreed.
- **A question rings the same bell.** The intent is *the board needs your hand*, and a question is that moment as much as an exit is. He agreed.
- **Raised by the board's own move, through the runtime.** Not the page, not the session hook (item 1 says why each was rejected). The ring is a consequence of a state change the board recorded, never of a read: 0.1's toasts from a poll were its deepest trap (INTENT, lesson 3).
- **His own moves never ring.** He was there. Rejected: ringing on every move so the rule is simple; a bell for his own drag teaches him to ignore the bell.
- **One popup per thing, never a digest.** A card needing him is not a count. Rejected: one resident notification listing every waiting card, the account watcher's shape; there the slots are few and fixed, here the cards are not, and a list he has to read is the board he was not looking at.
- **Critical, no timeout, and a sound.** His words: a notification he has to dismiss. quickshell advertises persistence and actions, and the account watcher proved both on this machine.
