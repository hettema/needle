# The words a card title never uses

*Written 2026-09-07 on card #74, from the owner reading his own board: "the
card titles are very difficult for me to understand … I am not technical so
e.g. tech jargon in there doesn't help me."*

A card's title says what will be true when the card is done, in the owner's
words (`docs/plans/README.md`, the title rule). The words below are the ones
the board and the code define and he does not use: each is a fact about the
machinery, never about what he gets. A title that needs one of them is a
title about the mechanism, and the intent it serves is what the title should
say instead. The list is the floor and not the test — a title can avoid every
word here and still say nothing he can place — so the cold read at a card's
birth applies his test ("could he place it against every other card without
opening it?") and this list only catches the cheap failure loudly.

One line per word: what the board means by it, and how to say the outcome
without it. Both readers read this file and neither carries a copy: the
ratchet `tests/ratchets/test_every_title_is_in_the_owners_words.py` refuses a
live title on Needle's own board that uses one, and the planning brief and
the birth reading in `board/brief.py` name it by path.

- **lane** — the isolated worktree and short-lived branch a session works in.
  Say who is working, or that work is under way: "a session", "work on a card".
- **make** — which kind of colleague a session is (Claude, Codex). Say
  "colleague", "of either kind", or name the colleague. The ratchet reads it
  only as a noun ("its make", "another make"); "make" the verb is his word.
- **fold** — the fast-forward push that lands a lane's work on the trunk. Say
  "finished", "landed", "shipped".
- **dial** — the owner's standing ruling that a verified defect enters
  execution without him — a switch per board, and one number of lanes for
  the machine. Say "defects fix themselves", "the auto-fix setting", "this
  board's auto-fix".
- **ring** — which of the three circles a review finding falls in. Say "inside
  the change", "next to it", "outside it".
- **door** — an action a card offers or refuses (Start, Answer, Watch). Say
  the action: "can start", "asks you".
- **wall** — a subscription's usage limit. Say "the allowance runs out", "a
  session runs out of budget".
- **pill** — the one-word readiness state on a collapsed card. Say what the
  card says: "the card says", "at a glance".
- **gate** — the effort level a plan names and the owner's click confirms. Say
  "how much thinking it gets", "the effort level".
- **scope** — the process group the machine runs a session in. Say "the
  session's memory", "its own space on the machine".
- **corpus** — the plans and suggestions under a project's `docs/`. Say "the
  plans", "the documents", "the written record".
- **fixture** — the synthetic project the tests run against. Say "the test
  board", "the test project".
- **migration** — a change to the store's schema. Say "a change to the
  board's memory", or say the outcome the change serves.
- **store** — the board's own database. Say "the board's memory", "what the
  board remembers".
- **trunk** — the shared branch every lane lands on. Say "the shared work",
  "what everyone builds on".
- **slot** — one subscription on the machine. Say "an account", "a
  subscription".
- **seam** — where one part of the code meets another. Say what the two
  parts are, or leave it out.
- **ratchet** — a test that holds a boundary named in the rules. Say "a check
  that refuses", "held by a test".
- **triage** — the independent reading that verifies a defect's mark. Say "a
  second reading", "read again cold".
- **worktree** — the isolated checkout a lane works in. Say "its own copy of
  the code".
- **hook** — the script the harness runs at a session's start, stop or
  prompt. Say what it does for him: "every session reads", "the rule holds
  at start".
- **rebase** — replaying a lane's commits over the moved trunk. Say "catches
  up with the shared work".
- **headroom** — the memory left on the machine under the floor. Say "room on
  the machine", "the machine is full".
- **windowless** — a session that runs with no window (a reading, a planning
  session). Say "a session nobody watches", "in the background".
- **rail** — what the defects were before they had a column of their own
  (card #100): a strip pinned at the top of Backlog. Say "the defects",
  "the Defects column".
