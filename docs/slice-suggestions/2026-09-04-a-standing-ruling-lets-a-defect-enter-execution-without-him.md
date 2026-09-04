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
