# Work that runs out of allowance comes back on the first try, not an hour later

**Kind:** defect
**Fix:** now — the intent it breaks is written (plan 68 / card #107: work the
laptop interrupted comes back by itself, and a session that ran out of
allowance is brought back on the rung the rule names); the fix stays inside
the runtime's own `where`/`resume` pair and removes the class — every move to
another machine decided on a cached account reading and re-decided on a fresh
one — rather than tonight's three lanes.
**Found by:** the owner, 2026-09-13, when every lane on the rented machine
stopped and none of them came back

## The intent it breaks

A lane that runs out of allowance moves to a slot with room and carries on
without the owner. Tonight three did not: they parked for an hour on the
first attempt and would have parked another hour had he not been watching.
The board's own words on the card said "then it comes back by itself", which
was not true of the attempt it had just made.

## The evidence

At 18:10Z and 18:12Z armana's session window ran out on the rented machine
("You've hit your session limit · resets 9:20pm (Europe/Berlin)"). The wall
hook did its half correctly: it filed a background handoff to hrme on opus
for each session (`~/.cache/omarchy/claude-acct/handoff/bg/`, and the same
three lines in `handoff.log`).

The board's automatic comeback then failed on all three, recorded verbatim in
`recoveries` rows 29 and 30:

> rented could not move it: rented refused `needle resume` (exit 1): the rule
> would not place it on armana: no Fable left anywhere; hrme has the most
> weekly headroom (58% used), so opus

Both halves of that sentence are the same machine's rule, asked twice, seconds
apart, with different freshness:

- `api/loops.py::Loops._placement` asks `runtime.where(..., cached=True)`.
  With a repo named, `runtime/service.py::Runtime.where` picks the machine and
  asks *that* machine's rule — so this is the rented machine's rule, read from
  its cache. The cache still had armana as the slot with Fable left (armana is
  the only account with any Fable: 34% used), because nothing had yet written
  back the session wall that had just happened.
- The comeback then calls `Runtime.resume` with that placement, which for a
  remote machine sends `needle resume --to armana` over the wire
  (`runtime/remote.py::Remote.resume`).
- On the rented machine, `api/runtime_cli.py::resume` re-asks the same rule
  with `cached=False`, gets hrme, sees it does not match `--to`, and refuses
  with exit 1.

Nothing bridges the two readings. The refusal is deterministic, so the hour's
park bought nothing: the second attempt would have failed the same way unless
the laptop's cache happened to age out first. The three lanes were moved by
hand with `needle move <short>` (no `--to`, which lets the holding machine's
own fresh reading choose) and all three were working on hrme/opus within
seconds — which is the proof that the room was there the whole time.

Cards left standing for over half an hour: Hello Revenue #534, Needle #139,
Needle #137.

## What would hold it

Two candidates, both inside the runtime:

1. The machine that holds the lane chooses. Send the comeback without a slot
   (what `needle move` already does) and let `resume` on the holding machine
   ask its own rule fresh — the board stops deciding on a reading it is one
   hop away from.
2. If the board must name a rung, the receiving verb treats a mismatch as
   *the rule moved under us* and places the session where the fresh rule says,
   recording both answers, rather than refusing and costing an hour.

The first is smaller and removes the class; the second is what to write if a
caller ever legitimately needs to pin a slot.

A third thing to check while in there: a refusal that is deterministic should
not buy the same hour's park as a genuine "no room anywhere" — the park's
words should say which it was.
