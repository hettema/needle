# A handoff to opus survives an account whose Fable is spent

**Kind:** defect
**Fix:** now — ruling 1 of 2026-09-04 already selects the outcome ("the
runtime asks `claude-acct best` and never re-implements the rule", written
into `domain/slot.py`), so which allowance bounds which rung is not the
owner's call; the fix is inside `api/loops.py::Loops._rung_open` and removes
the class — every handoff judged closed by an allowance its own rung does not
run on — rather than today's ten lanes.
**Found by:** the owner, 2026-09-15, when ten lanes on the rented machine
walled on hrme and none of them moved

## The intent it breaks

The wall detector chooses where a walled session goes, at the wall, with the
accounts read fresh. That choice is the best information on the machine. The
board is meant to discard it only when the rung it names has since run out —
and instead discards it whenever *any* allowance on that account is spent,
including one belonging to a model the rung is not running.

Fable is spent on four of the five accounts today, so nearly every handoff is
judged closed, and nearly every comeback falls through to the board's cached
fallback instead of the hook's fresh answer.

## The evidence

At 2026-09-15 12:56Z hrme hit its session limit on the rented machine and
took ten sessions with it. The hook chose correctly every time — here is a
handoff it wrote, read off the machine:

    {'account': 'armana', 'model': 'opus', 'from_slot': None, 'at': 1789469884.1880038}

armana's own reading at that moment, from `claude-acct`'s cache:

    "Session (5-hour)": 0.04,
    "Weekly (7-day)": 0.6,
    "Fable Weekly": 1.0

`api/loops.py::Loops._rung_open` takes the account's reading and closes the
rung on any share at 1.0 whose reset is still ahead:

    for label, share in reading.spent.items():
        if share < 1.0:
            continue
        when = reading.resets.get(label)
        ...
        if when > now:
            return False

`Fable Weekly` is 1.0 and returns on 20 Sep, so the rung was called closed —
though the handoff names **opus**, which the hook chose precisely *because*
Fable is gone everywhere. `Handoff.model` carries that word and this check
never reads it.

The consequence, in the board's own records (`recoveries`, four rows at
10:57–10:58Z, one per lane):

> rented could not move it: rented refused `needle resume` (exit 1): the rule
> would not place it on hrme: no Fable left anywhere; armana has the most
> weekly headroom (59% used), so opus

— the board fell through to its cached placement, which named hrme, the
account that had just walled. Every lane parked an hour on a refusal that
would repeat. Card #143 fixes that second link so the machine's own rule
chooses; this card is the first link, so the hook's answer is not thrown away
in the first place.

## What would hold it

Needle must not read allowance labels for meaning: `domain/slot.py` says so
in as many words, and a rung's model is "whatever word the rule answered,
kept as it was given and never guessed", so matching `Fable Weekly` against
`opus` in here would be exactly the guessing the design forbids. Two shapes
that do not:

1. **Ask the rule.** `claude-acct best --from <slot> --tried <rung,...>
   --json` is the one door, and the runtime already goes through it
   (`rule.where`). `_rung_open` becomes a question for the rule on the
   machine that holds the lane, not a sum over labels here. Cheapest, and it
   needs nothing new — but note the rule answers "where next", which is not
   quite "is this rung open": it may name a better account while the
   handoff's is still fine, which discards a good handoff again, harmlessly
   now that #143 sends the question to the rule anyway.
2. **Teach the rule the question.** A verb that answers whether one named
   rung has its allowance — `claude-acct open <slot> [--model <m>]` — put in
   `~/Work/omarchy-machine`, which is where the knowledge belongs. Truthful
   for both purposes, and one more thing to keep in step across two repos.

Recommended: (1) now, and (2) only if a measurement shows the extra rule call
or the discarded-but-fine handoff costing something. With #143 landed, being
wrong here costs one uncached rule lookup, not a broken comeback — which is
what makes (1) safe to take first.

## Live neighbours on this ground

Searched `docs/slice-suggestions/` (live and `done/`) for the rung, the
allowance and the handoff. Card #143
(`2026-09-13-work-that-runs-out-of-allowance-comes-back-on-the-first-try.md`)
is the same chain's second link — the board naming a rung the holding machine
refuses — and is being fixed in its own lane now; it does not touch which
handoffs are believed.
`2026-09-05-a-conversation-that-hits-an-accounts-limit-carries-on-elsewhere-with-no-popup.md`
is about an interactive conversation getting a popup instead of a move — the
hook's side, not the board's reading of what the hook wrote.
