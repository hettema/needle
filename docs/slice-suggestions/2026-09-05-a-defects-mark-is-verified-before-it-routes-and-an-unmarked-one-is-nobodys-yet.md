# A defect's mark is verified before it routes, and an unmarked one is nobody's yet

**Kind:** defect
**Fix:** now — the owner ruled the boundary on 2026-09-05 (recorded below, in his words and the colleagues'), so what remains is execution: replace the silent default, type the third state, hold the three marks with a ratchet, and give a genuine `his` card a door. The rule this installs is the same rule that makes it a `now`.
**Found by:** Dennis, 2026-09-05, reading twelve hours of auto-fix on Hello Revenue and asking "how many of these decision points could you guys take instead of me? The difficult thing is where to draw the line." Settled the same evening by Claude (Opus, session f4d2a309) and Sol (Codex gpt-5.6, rollout 01a071ee) in the first Claude-to-Codex call this machine has made; Sol held the primary judgment on the line, Claude held the measurements. Dennis read the result and ruled it true.

## Observation

Auto-fix converges on defects and diverges on decisions. Over twelve hours the
Hello Revenue rail went 26 → 20 while closing 20, so roughly fourteen new
defects arrived — thirteen of the newest fourteen filed by the fix lanes' own
reviews. Per fold that is about 0.4 new auto-fixable defects and 0.2 new
decisions marked `Fix: his`. The first branch converges. The second drains
only through the owner, and it was draining at zero:

- Eight live `Fix: his` defects, aged 41, 28, 21 and 9 days, plus four born
  that day.
- **The board holds zero `answered` rows. Ever.** 194 owner audit rows, all
  ranking, starting and looking.

Two causes, and neither is the owner being slow.

**The mark is the default for ambiguity and nothing ever re-reads it.** Hello
Revenue's doctrine says an unmarked defect reads as his — the safe default.
The mark is written once, by the session that filed the defect, at its moment
of least context, and never revisited. Of the eight, five turned out never to
have been his: three merely reapply an outcome their own document, a sibling
room, or a prior ruling already selects (one of them a half-state against
slice 8b's ruling that a June refactor dropped without reversing), and two are
technical judgments with measurable effects.

**There is no door.** `api/doors.py::answer` calls `_lane_session()` and
resumes a live lane's session with the owner's text. A parked suggestion has
no lane and no session, so the door is never offered. Cards reach him only
when a planning session happens to stop mid-turn. The count is exactly zero
because there is nothing to answer, not because nobody tried.

## The rule the owner ruled

> A decision is Dennis's only when the written record does not select among
> materially different outcomes he owns, or when acting would create external
> exposure beyond a bound he has already authorised. Applying an existing
> intent, ruling, precedent or authorised bound is execution, not a new
> decision. Effect-level reversibility is evidence about how safely to act
> under uncertainty; it is never the test of who owns the call.

## What to build

1. **Retire "unmarked reads as his."** An unmarked defect is `needs triage` —
   a typed state that routes to nobody. Ambiguity becomes work for the
   colleagues before it becomes work for him.
2. **Every mark carries its evidence.** `Fix: now` cites the intent, ruling,
   precedent or authorised bound that selects the outcome. `Fix: his` names
   the unresolved owner outcome or the unbounded exposure — never "product
   call", "prompt change" or "new surface" alone. `Fix: when <signal>` covers
   an outcome already selected whose authorising condition has not arrived.
3. **Triage is a second pass, never the finder judging its own downgrade.**
   The finding session proposes a stance with its citation; an independent
   session verifies it before the card routes. A different make while card #58
   measures whether make difference earns its cost — a hypothesis, not
   doctrine: if independence of context is what matters, different make is
   ceremony.
4. **A ratchet holds all three forms**, so a mark cannot be tidied away.
5. **Split mixed documents**, so a settled technical floor never waits behind
   an unsettled owner-facing surface. Two of the eight were hostages this way;
   one waited 41 days.
6. **A genuine `his` card gets an Answer door that needs no live lane.**

## The loop, fixed before the data exists

The owner audits the first five and the first ten colleague-taken decisions
cold, before seeing their outcomes. The classifier fails if any decision
exceeded an authorised exposure bound; chose between materially different
owner outcomes with no written source selecting one; was defended as
reversible at the code level while its real-world effect was not; if he would
have decided differently on more than one of the first ten; **or if the set
shows a shared direction that no individual citation disclosed.**

On failure the response is not "revert" — once a customer has seen something
or money has moved there is nothing to revert. It is: stop further downgrades
in that class, reclassify the open pile, show him the accumulated direction
and effects, tighten the rule on the observed mismatch, and resume only after
a revised classifier passes a fresh predeclared sample.

## Rejected

- **Reversibility as the rule** (Claude's proposal; Sol refused it and Claude
  conceded). A reversible change still chooses between outcomes nobody ranked:
  a chat surface removable tomorrow expresses product policy today. And the
  converse — spending inside an authorised budget is execution although money
  is irreversible. Kept as evidence about safe action, demoted from the test.
- **Category lists** ("customer-visible", "commits money", "creates risk") as
  absolute exclusions. Too broad in both directions: most defects restore a
  surface already decided, and an authorised budget exists precisely so that
  spending inside it is not a fresh decision. They are reliable warning
  markers, not the line.
- **Triage at filing time by the finder.** Cheap, and it is the exact session
  that produced this pile: adjacent to the defect, tired, and pulled both
  toward avoiding scope and toward moving on.
- **Folding this into card #58.** Composition cannot be measured honestly
  while the inputs are classified by an undefined rule; it would confound "did
  we find the right owner boundary" with "did this pairing judge better". This
  card defines the boundary; #58 then measures who classifies best inside it.

## Sequencing

Before #58. The eight are already re-triaged in Hello Revenue's corpus
(`59661dcd9`), so the rule has its first sample the moment this lands.
