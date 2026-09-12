# You close the laptop and the work finishes without you

**Kind:** defect
**Fix:** now — the owner's ruling of 2026-09-11 on card #83 is the written intent ("ordinary expiry, disconnection and account limits must not require manual rescue"), the fix stays inside the rented machine's record and the runtime's existing account authority, and it removes the class — every unattended session on that machine — rather than the one card that met it

**Found by:** the discuss session on Needle card #83 on 2026-09-13, splitting that card on the owner's word after the evening's reading found the rented machine running unattended work with nothing installed to renew or resume it

## The intent it breaks

Work sent to the rented machine should finish whether or not the laptop is
open. Today it only finishes while someone is watching. The laptop runs two
things that keep work alive — one renews an account's access before it lapses,
one picks up a session whose connection dropped — and the rented machine runs
neither. So an allowance that runs out, a line that drops, or an account that
signs itself out leaves work stopped on a machine nobody is looking at, and the
first the owner knows of it is a card that says nothing happened.

This is the half of card #83 that was never built. That card moved execution to
the machine, and that part works: the placement rule already sends Hello Revenue
and Needle work there and keeps the laptop's own cards at home. What it does not
yet deliver is the sentence the owner used when he widened it — fire work off,
close the laptop, come back to finished work.

## Evidence

- On the rented machine, 2026-09-12 23:4xZ: `systemctl --user list-timers --all`
  answers `0 timers listed`. On the laptop the same command lists
  `claude-acct-recover.timer` (last run 47 s earlier) and
  `claude-allowance-refresh.timer` (last run 12 minutes earlier).
- All five accounts on the rented machine had their weekly Fable allowance spent
  that evening, and the reader card #83's own daily check calls — `login-check` —
  answered `not ok: You've reached your Fable limit`. It calls the default model,
  so a spent allowance and a broken sign-in read identically. The owner cannot
  tell "out of room until Tuesday" from "signed out, needs your browser".
- Card #83's first night on the machine, recorded in its own rulings: the laptop
  suspended with its lid, the board slept with it, a session on the rented machine
  finished its turn and waited for a board that never answered, its process left
  after eight hours idle, and the morning read it as died with nothing landed —
  twenty commits safe on its branch and none of them shared.
- Card #83's own reading of 2026-09-11 found the selector and the handoff present
  on the rented machine but no periodic renewal and no recovery installed, and
  recorded that a successful model call alone proves neither.

## What would hold it

The machine keeps work alive on its own, using the authority that already exists
rather than a second one beside it: the account tool's selection, renewal locks,
supervision and recovery (`omarchy-machine`'s `home/.local/bin/claude-acct` and
its two units), and the runtime's own rule, handoffs and service. What must be
true, each observable:

- An idle account's allowance is renewed with no editor open and no owner action,
  and the same account still answers from the laptop afterwards.
- Work that meets its allowance carries on under another eligible account with
  the model it was pinned to, once, with no second copy of it running, and an
  account with nothing left is passed over rather than chosen and stalled.
- Work interrupted by a dropped connection is picked up again with no owner
  action and no two supervisors resuming the same session.
- An account that has genuinely signed out, or a moment when no account has any
  room, says so where the owner will see it, in words that name which of the two
  it is and what it needs from him — never silence, and never a reader that calls
  a spent allowance a broken sign-in.
- What is installed survives a restart of the machine's own services, and the
  machine's drift check names it when it is missing.

Rehearsed without exhausting real allowances and without interrupting sessions
the owner is using, with the installed mechanism, the timed renewal evidence and
the rehearsal evidence recorded apart from each other.

What this is not: a second chooser, a copied sign-in, or a token file crossing
between machines — card #83 settled all three and they stand.
