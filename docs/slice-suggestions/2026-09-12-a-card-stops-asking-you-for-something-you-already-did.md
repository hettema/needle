# A card stops asking you for something you already did

**Kind:** defect
**Fix:** now — `docs/HOW-WE-WORK.md` §11 already says it ("a machine fact that outlives its evidence doubts itself on the page before anything moves"), the fix stays inside the board's ring, and it removes the class: every row kind that states a condition, not the three rows on card #83 tonight

**Found by:** the discuss session on Needle card #83 on 2026-09-12, when the owner asked what was left on his side and the card answered with work he had finished two days earlier

## The intent it breaks

The board is the team's memory, and what it says is what the owner acts on.
A WAITS row states a condition: *this is waiting on you*. When the condition
comes true, nothing on the board notices and the row stays exactly as it was
written. There is no verb that retires a row — `add_row` replaces only
DELIVERED, WATCH and REVIEW (`infrastructure/store.py::add_row`, `ONE_PER_CARD`);
every other kind appends, so the true sentence lands underneath the false ones
and the card reads oldest-first.

So a card accumulates conditions that were once true, and the owner, who
cannot inspect the work, reads them as the state. That is the failure §6
names: not an unfinished thing, a wrong thing, and every decision built on it
inherits the error.

## Evidence

Card #83 on 2026-09-12 carried three WAITS rows. The second asked the owner
for three sudo lines on the laptop — lay the sshd drop-in, `sshd -t`, enable
sshd, open port 22 — as the thing blocking the board's move. He had done all
of it on 2026-09-10 at 14:38: read from the rented machine over the tunnel
that evening, `/etc/ssh/sshd_config.d/90-needle-tailnet-only.conf` is in place
and `systemctl is-enabled sshd` / `is-active sshd` both answer. The third
WAITS row says the board serves from the rented machine since 15:44Z; `needle
board` on 2026-09-12 answers `the board serves from laptop`, because it was
moved back the same evening.

Asked what was left on his side, the honest answer had to begin by telling him
that one of the three things the card was asking for was already done and
another was no longer true. The row written tonight has to open with "the two
rows above are out of date" — a workaround in prose, in the one place that is
supposed to be the memory.

## What would hold it

A row that states a condition carries what makes it true, the way a WATCH line
carries its command, and the pass that already reads every machine reads that
too: a condition that has come true leaves the brief and lands in the card's
history with the reading that retired it, so the card shows what is waiting and
the history shows what waited. Where a condition cannot be machine-read, the
row can still be retired by a session with its reason, which is a row leaving
by a named hand rather than a row nobody can remove.

What this is not: a second status list beside the corpus, and not an owner
action. §11's test applies to the row as it does to the column — the row is
either his ruling or a machine fact with its evidence, and a machine fact that
outlives its evidence must doubt itself on the page.
