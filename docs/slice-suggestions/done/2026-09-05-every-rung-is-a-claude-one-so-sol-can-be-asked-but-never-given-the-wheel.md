# Every rung is a Claude one, so Sol can be asked but never given the wheel

**Carried by:** docs/plans/2026-09-05-the-strongest-model-with-headroom-drives-the-card-whatever-its-make.md — both rulings the `his` mark waited on were made in the Idea door on 2026-09-05 (conversation a4386ba3): a make the board cannot fully instrument may hold the wheel, and the ladder is a quality tier, so a top-tier rung of any make outranks Opus.
**Kind:** idea
**Fix:** his — two rulings come before this can be planned: whether a make the board cannot instrument the way it instruments Claude may hold a card's wheel at all, and whether a rung that spends no Claude allowance may outrank Opus, which changes the machine's ruling 1 in a repository that is not this one.
**Found by:** the owner, from the board's Idea door on 2026-09-05 (conversation f8e98e34)

## Observation

Nothing planned puts a colleague of another make in the driver's seat.

- **#57 made Sol callable, not accountable.** `needle call` resolves a warm
  Codex worker, `needle wait` judges its answer, `needle list` shows it at
  work (`runtime/codex.py`;
  `docs/plans/done/2026-09-05-a-colleague-of-any-make-can-be-called-warm-and-seen-at-work.md`).
  A called worker is a bounded question answered out of stdout under a
  read-only sandbox. It has never held a worktree, a branch or a card.
- **The live composition card chooses who challenges whom, and assumes the
  hand is Claude.**
  `docs/plans/2026-09-05-the-team-learns-which-composition-earns-its-place.md`
  item 1 assigns one composition at every Start — "accountable hand alone,
  same-make challenge, or different-make challenge, with the models named" —
  and refuses an unexecutable composition. Nothing can execute a Codex hand,
  so that router can never assign one. This suggestion is that card's
  prerequisite, not its rival.
- **The rule the runtime asks knows two rungs, both Claude.**
  `domain/slot.py::Model` is `fable | opus`; `runtime/rule.py` turns
  `claude-acct best` into a placement or a refusal; `runtime/launch.py::_walk`
  dies with the rule's reason when the rule finds nowhere. Four slots, one
  make.

**And the trigger in the question is already handled, routinely.** On
2026-09-05 at the time of writing, `claude-acct status` reports every one of
the four accounts at 100% Fable used (gmail, hrme, hrclaude, armana; weekly
50–60% used; armana's Fable back Sun 16:59). `claude-acct best --json`
answers `{"slot": "armana", "model": "opus", "why": "no Fable left anywhere;
armana has the most weekly headroom (55% used), so opus"}`. Fable is out right
now, the board has not stopped, and this conversation is running on the
fallback rung. "Fable is gone" means the ladder fell one step, not that there
is nowhere to run — nowhere would take all four weekly allowances, and they
are about half spent.

So what Sol would buy is not rescue from a wall. It is two other things:

- **A rung on a meter Claude work never touches.** Every rung today draws on
  one weekly pool per account, and every Opus hour under a spent Fable
  allowance drains that pool faster than a Fable hour would. Sol's
  subscription is not in the pool at all. This is the strongest argument for
  the capability and it has nothing to do with the wall.
- **A second make's judgment on the work itself**, which #54 and #57 already
  showed pays — Sol's positive-allowlist correction in the first warm exchange
  (`runtime/codex.py::WORKER_SOURCES`), its challenge of #59.

What it does not buy is the ranking in the question. "When Fable runs out, Sol
is the best model" is precisely the claim the composition card exists to earn
or refute per work shape, and Sol itself argued there that routing doctrine
must never encode an experimental arm (that plan's item 3). Writing Sol above
Opus into the ladder today would be the thing Sol objected to.

## What would change it

Two halves, and only the first is Needle's.

**1. A lane a Codex worker drives, that the board can see, steer and close.**
Every unknown here is instrumentation, and one is smaller than it looks:
Codex 0.152.1 has a hook system, and a `SessionStart` hook is already trusted
and firing on this machine (`~/.codex/hooks.json`, `[hooks.state]` in
`~/.codex/config.toml`), so the board's own hook may be installable there the
way `needle hook install` wires a Claude repository. What must be proved
before this is planned, not assumed:

- which events Codex fires beyond `SessionStart` — the board reads a lane's
  plan progress and its end, not only its birth (`api/app.py`'s `/api/hooks`,
  `hooks/needle_hook.py`);
- whether `codex exec` in a worktree, widened past its read-only default, can
  carry a lane's commits and its fold;
- what a Codex lane's scope is, since `runtime/launch.py::scope_session` puts
  every Claude lane in its own systemd scope so a kill or a limit takes one
  lane and not a subscription;
- what the board shows where a Claude row shows a wall, a rung and a fork.
  Codex has none of the three, and #57's ruling stands: Needle does not invent
  lifecycle parity it does not have.

**2. A rung the rule can name.** `claude-acct best` is the machine's one rule
and lives in the machine repository; a rung that is not a Claude subscription
changes its shape (`Model`, `Placement.slot`, the handoff ladder) and its
ruling 1. That is a card on the Omarchy board, and it should not be written
before (1) exists — a rule that names a rung nothing can execute is a rule
that lies.

## What would tell us it was worth building

The measurement is available before the build, from facts the board already
keeps. Over a fortnight: how many Starts found no rung at all (today, none
observed), and how many Opus-hours ran under a spent Fable allowance. If the
first is zero and the second is large, this card is about conserving the
Claude pool and about a second make's judgment — and it sequences behind the
composition card, which is what will say whether a Codex hand is worth
assigning at all. If Starts do begin dying for want of a rung, it is about the
board not stopping, and it goes first. The two readings imply different cards;
choosing between them without the count would be guessing in a confident
voice.
