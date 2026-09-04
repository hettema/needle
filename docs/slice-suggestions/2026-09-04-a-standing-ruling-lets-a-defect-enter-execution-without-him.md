# A standing ruling lets a defect enter execution without him

**Kind:** idea
**Found by:** the owner, from the board's Idea door on 2026-09-04 (conversation
56f7b05f), after two defects were filed in one sitting: "Many of the defects
are unambiguous? They're straight fix it tasks with no real input needed from
me? Can we somehow start the fixes automatically and only ping me if there is
ambiguity?"

## Where this stands against the fixed point

`docs/INTENT.md`: **"One move is his; every other move is teamwork. He decides
what enters execution."** Read as a rule, this idea breaks it. Read as an
intent, it is the same decision made once instead of forty times: he decides
*what enters execution*, and pressing Start on each card is today's method for
recording that decision, not the decision itself. He manages priorities, not
tasks — and which defect gets fixed is a task.

So what this proposes is a **standing ruling of his**, applied by the board,
and never the board deciding for itself which work is safe to start. Any
version where eligibility rests on a session's own judgment of its own fix
fails the intent and should not ship: I am both the change and its judge there,
and the judgment would agree with me.

Execution itself is not the new part. A started lane already runs to its fold
with no hand on it — the first board was retired by a card Needle ran from
Start to Done on its own. What is missing is only the entry.

## What stands between a defect and execution today

Three of his moves per defect:

1. A suggestion carries no effort gate, so Start is closed on it
   (`board/lane.py:674`).
2. The Plan door opens a **conversation with him** to write the plan
   (`api/doors.py:477`, `WindowKind.PLAN`) — right for an idea, mostly
   ceremony for a defect whose document already names its own fix in its
   "What would hold it" section.
3. Start is a door he presses (`board/lane.py:655`).

## The shape

1. **The filing session writes the fix into the document**, in the head, where
   the board and he both read it before anything runs: whether the fix is
   determined and bounded, the effort gate it wants, and its "done means"
   items — the material a plan needs. A defect that cannot say this says so,
   and waits for him. This is written when the finding is fresh, by the session
   that has the evidence, and it is visible on the card.

   The proposed bar, three parts, all required (from the owner's question the
   same evening — "find a bug, fix it, because you can; but is it that black
   and white?" — and the answer that it is not, in exactly three places):
   - **Against a written intent.** The intent existed and the code did not
     hold it. A "defect" that turns out to be an unwritten intent is a
     question, not a fix, and is his.
   - **Inside its ring.** The fix stays within the change it corrects, in the
     rings rule's sense; a fix that has to move a boundary is a redesign
     wearing a defect's clothes.
   - **Removes a class, not an instance.** At a seam with something that
     moves — the registry, the wall detector, launch timing — "ignore
     `starting…`" patches one case and rots into a special case; "a session
     never seen alive has not died" removes the class. Only the second is a
     fix, and only the second is eligible.
2. **His ruling, written once**, names which class may enter execution without
   him — and is a document, not a setting, so the reason it says what it says
   survives the session that asked for it.
3. **On a card meeting both, the board writes the plan from the document with
   no window and starts the lane.** From there the card walks the ordinary
   path: same ratchets, same review loop, same fold.
4. **Ambiguity has one destination and it already exists.** A lane that finds
   the document's fix wrong, or finds the fix implies a decision that is his,
   stops and asks; the question lands on the card and on Your move, as every
   lane's question does. It never improvises a different fix — that is the
   scope creep the effort gate exists to refuse.
5. **He can see and undo it**: the rail says which cards the board started on
   its own, and any class can be ruled back to hand-start in one edit.

## The cycle, as the owner drew it, and what the machine adds

The owner's drawing (same evening): a lane reviews its own work in rings —
inside and adjacent fixed in the lane until a pass finds nothing, the outer
ring filed to the board; the board's findings then get the same loop; anything
marked as his is excluded; everything else goes on an automatic fix path; the
limit is tokens and this laptop.

That drawing is right, and it is a recursion: **the outer ring of one lane is
the inner ring of the next.** Same loop, one ring out, until the rail is empty.
What the machine can see that the drawing does not:

- **The intent, sharpened so it can be measured.** "Bug-free" cannot be
  counted. Two things can: *no defect fails silently*, and *no known defect
  waits on a human*. Every one of the nineteen that cost something was silent —
  a currency mislabelled, a repair reporting success, a theme paid three times,
  five rows nobody opened. Rock-solid is software whose failures are loud.
- **A fix that does not close its class churns the rail.** Each fix lane runs
  a review that files its own outer ring, so the rail is fed by the path that
  drains it. It drains only if fixes remove more than they file — which means
  every fix ships the thing that makes its class loud (a validator, a ratchet,
  an alarm), not just the patch. The "removes a class" bar is what keeps this
  from running until the death of the universe.
- **The dial is his, on the board.** The owner's own shape, and better than
  an idle-fill rule: a toggle on the head — *auto-fix defects* — and a number
  beside it, how many fix lanes may run at once. He turns it to one while he
  is building features and up when he goes to sleep; the head's Live count
  already tells him what else is running. The board fills up to the number
  from the rail and no further. The binding limit is not tokens but the
  subscription slots his ranked work needs and the one trunk every fold lands
  on, and the dial is exactly the control for that. Collisions are the
  existing machinery — a worktree per lane, Start refused when two lanes
  would edit the same files, the second fold rebasing onto the first — with
  one condition the plan must hold: a plan the board writes for a defect
  declares its terrain honestly, or the collision check has nothing to read.
  Needle's own defects run only when no lane is live anywhere, because a fold
  on the board restarts the service under every running lane.
- **The filer's mark has three values, not two.** The nineteen already say
  all three in prose: *fix now*, *fix when this trigger fires* (#377 says wait
  for one production row; #341 says wait for a shipped duplicate), and *his*.
  A trigger that has not fired is not started — and "how do we know it
  fired?" (the owner's question) has an answer already built: a shipped card
  waits in Executed with a WATCH signal a session reads on a cadence
  (`SignalKind.SESSION`, plan 09). A defect with a trigger carries the same
  row, the same reader reads it, and when it fires the card's mark becomes
  *fix now*. One mechanism, not a second one; today the trigger is prose
  nobody reads, which is the open loop that rule exists to close.
- **Two preconditions are on the rail already.** The close still accepts a
  code lane with no review record
  (`2026-09-04-a-close-without-a-review-record-is-accepted.md`) — an
  unattended lane's "clean" has to be a refused close, not a remembered rule.
  And a green suite is not the truth for the served board (two of this
  slice's own defects only the live board could show), so a fix that touches
  the page carries a live check in its "done means".
- **The measure, named now, in lanes rather than days.** The cadence belongs
  to the intent, not the calendar: the signal arrives once per fix lane, so
  the look happens after the first ten fix lanes close, and again after
  thirty. Per lane: folded green with a clean final pass / stopped to ask /
  undone (reverted, or a defect filed against it) before the next look; and
  whether it shipped a class-closer. Across the rail: its size on both boards,
  split by who filed each card (a fix lane, a feature lane, a production
  reading, the owner). Prediction at ten: no more than one undone, fewer than
  half stopped to ask, most shipped a class-closer. Prediction at thirty:
  arrivals from feature lanes flat (the natural discovery rate), arrivals from
  fix lanes falling, the rail smaller than when the dial was first turned. If
  the rail grows, fixes are patching instances — the dial goes to zero and
  the last ten fixes get read before it moves again. Time enters only as the
  guard: ten lanes not reached within a fortnight of the dial being on is
  itself the finding that the path is not running.

## The decisions in this that are his, not mine

- **Does an unattended fix fold to `develop` on green, or stop before the fold
  and wait for him?** My recommendation is that it folds: the ratchets and the
  review loop are the mechanism that makes a fold safe, and a queue of unfolded
  lanes collides with itself and with everything else. But the blast radius is
  the trunk, so the call is his.
- **How many may run at once**, given the collision detector refuses lanes that
  share files but does not rank them.
- **Whether a defect he filed himself is eligible**, or only ones a session
  found with evidence.

## The bar, tried on the nineteen defects Hello Revenue holds today

The owner's test, the same evening: "if there is no ambiguity in the 19, I
think we might have our answer." All nineteen documents on Hello Revenue's
defects rail read in full (cards #128, #129, #341, #355, #361, #377, #379,
#383, #384, #385, #386, #391, #392, #393, #394, #395, #397, #399, #402).

| Verdict | Cards | What they have in common |
|---|---|---|
| **A straight fix. Needs nobody.** | #361, #377, #383, #384, #385, #386, #391, #392, #393, #394, #397, #399 — twelve | The intent is written (a CLAUDE.md rule, a shipped plan's intent, a validator that already states the bar). The document names the fix, usually with the test that proves it. Where a judgment remains it is technical and the document already ranks the candidates. |
| **Mine, but a plan's worth, not a fix.** | #379, #395, #402 — three | No question for the owner. The fix touches a contract many call sites share, or adds a seat, or has an unproven cause the document says to confirm first. A session writes the plan; the plan only reaches him if it finds a call that is his. |
| **Carries a decision that is his.** | #128, #129, #341, #355 — four | Each is a missing sentence of intent, not a bug: should a wrong-looking ad account get a confirm moment (a product surface); should a broken checker stop the build (risk); should a duplicate-copy floor bite harder (quality against cost); should chat grow a clickable budget door (a new surface). Two of the four are half straight fix (#128's server-side check, #355's second item once its upstream lands). |

Two findings that matter more than the count:

- **The filing sessions already mark it.** The four that are his say so in
  their own words — "owner call", "intent question for the owner", "a
  calibration decision the owner takes on evidence", "comp-first surface
  change". The twelve say "one-way-to-do-each-thing tidy", "one route test",
  "the fix is two one-line edits". Nobody had to judge them afterwards; the
  evidence was written at filing time by the session holding it. The head
  field in item 1 is that sentence, made machine-readable.
- **Several straight fixes were deferred for a ritual, not a doubt.** #391 and
  #392 "ride the next real edit" because a prompt change drags a walk record
  and a battery replay. That is human labour economics reasoning in a session
  whose labour is free; under a standing ruling the ritual is simply paid.

And the owner's framing holds: every "ambiguous" defect here is a place where
intent is unwritten. Four one-line rulings from him turn the four into
straight fixes, and the class they belong to stays autonomous afterwards.

## A precondition worth naming

Eligibility would be read off the document's head, so the head has to be there.
Two of the eight live suggestions carry no `**Kind:**` line at all and reach the
defects rail by a title heuristic (`board/parse.py:31`). A ratchet that refuses
a suggestion without its head fields is the cheap precondition, and is worth
doing whether or not this ships.

## The loop

We think a standing ruling on unambiguous defects will cut the owner's moves
per defect from three to zero without costing him a fix he would have made
differently, because what makes a defect unambiguous is written down by the
session that found it, before the fix wants to run, and read by him on the card.

Over the first ten unattended fixes: how many folded green with a clean review
and no defect filed against them within the week; how many stopped to ask him;
how many he undid. **If he undoes even one, the eligibility field is written at
the wrong altitude** — and the fix is to that field, not to the board. If more
than half stop to ask, the idea is right but the bar is set where it saves
nothing, and the field should say less.
