# The team learns which mix of colleagues earns its place

**Found by:** Dennis, asking how teamwork can operate across cards and learn where its return is reliable without making him judge machine mechanics. His enduring judgment is whether the result works, looks and interacts like his intent; the colleagues should own the measurable loops beneath that.
**Status:** SHIPPED
**Composition:** different-make challenge — accountable hand Claude Opus 5 (the lane on the rented machine, 2026-09-11); Codex wrote the plan on 2026-09-05 and Claude Opus corrected it before build; a Codex colleague reads the change cold. Declared by the lane at its own start, since the card began before the board could assign a team, so the reader counts this card as an observation the way it counts #59's.
**Challenged:** 2026-09-05, by Claude Opus, of Codex's draft: one material correction before build — the first measures (the Written line above: corrections before build and defects escaping after close carry more signal than speed or token cost at small, confounded sample sizes), which is what the reader now ranks first.
**Written:** 2026-09-05, by Codex after challenge and reconciliation with Claude Opus. Both agreed this is separate from making Codex callable, that quality is invariant, and that the evidence already exists. Claude corrected the proposed first measures: corrections before build and defects escaping after close carry more signal at small, confounded sample sizes than speed or token cost. Dennis then ruled that every card should automatically assemble its best currently supported team: routing is a two-way door, selective human scheduling would make him the weakest link, and running the loop is how the evidence arrives fastest.
**Effort gate:** high — the reader is small, but choosing and automatically applying compositions without rewarding easy work or turning collaboration into a committee is a judgment problem.
**Sequencing:** after #63 (a composition can only name a hand the runtime can execute; #63 makes a Codex hand executable and its ladder a tier per rung, and calls itself this card's prerequisite — this line is the other half of that awareness, added from the Idea door on 2026-09-05, conversation 6b683c8b), after #59 (the boundary this card measures compositions inside; its `TRIAGED` rows are the comparable work shape), and after #57, because automatic different-make composition needs reciprocal addressability. #54 is the first different-make observation. No hold for three observations: incomplete evidence selects exploration honestly rather than leaving Dennis to schedule it.
**Formerly:** The team learns which composition earns its place (retitled 2026-09-07 to the bar docs/plans/README.md sets, card #74 on Needle)

## Intent

Every card automatically assembles the best team the organisation's current evidence supports, with quality invariant and speed and cost won inside it. The organisation, not Dennis's memory, chooses and measures which composition works for which kind of work, applies what it learns, explores while evidence is incomplete, and re-tests it when a model changes. Dennis judges perceptual and intent-bearing outcomes; the colleagues own composition, coordination and every machine-readable outcome, quality, rework, escape, time and cost loop, bringing him only intent divergence they cannot resolve.

This is not a new measurement platform. The system is already the authority: review rings, corrections, defect lineage, send-backs, commits and burn records are the evidence. This card adds the missing declared composition, one reader that joins those existing facts, and the reversible routing decision that applies the reading before each Start.

## Items

### 1. Every Start assigns a composition before the work

Before a card starts, the board assigns exactly one composition: accountable hand alone, same-make challenge, or different-make challenge, with the models named and one accountable hand. The assignment comes from the current evidence for that work shape; incomplete evidence invokes the exploration rule rather than asking Dennis. It appears on the card, enters every participant's brief, and is immutable after Start so an outcome cannot rewrite its experiment. Done means: every newly started card has one visible assignment; Start refuses an unexecutable composition; no session or owner memory is required to initiate the collaboration; and a single-hand assignment is as real a team decision as a multi-colleague one.

**Met:** `api/doors.py::Doors.start` asks `api/team.py::Team.route` for the team before the brief is built and refuses a plan that pins a team the runtime cannot execute (`board/team.py::Unexecutable`); the brief carries `board/brief.py::team_brief` — who challenges before build, who reads the change, and the one `**Challenged:**` line the reader counts; the row is written once the lane is alive, with the rung it landed on, and `Store.record_composition` refuses a second, so a restart keeps the first Start's team and no outcome rewrites it; the card's history says `team: …` with the machine as the actor, the open card shows a Team line, and a card with one hand is as much an assignment as one with a challenger (`tests/api/test_team.py`, four cases; `tests/board/test_team.py`). The team's hand is the rule's placement, so nothing here chooses a model or a make: a composition is who challenges the hand the one rule chose. Under `alone`, §13's independent review still happens, by a cold reader of the hand's own make — the doctrine of 2026-09-11 postdates this plan and governs it.

### 2. One reader joins evidence that already exists

For comparable design work, read and attribute: material corrections made before build; review findings by inside, adjacent and outside ring; defects later filed against the card; send-backs and stops; commits within a week that fix or revert the fold; tokens and wall-clock from the existing burn and lane timestamps. Do not copy these facts into a new event stream. Done means: one generated reading can be reproduced from corpus, board and git facts; deleting or changing a source fact changes the reading; there is no hand-maintained scorecard.

**Met:** `board/team.py::observation_of` joins, per closed card: the team declared (the store's row, else the plan's or the record's `Composition:` line — #59's and #54's, the founding observations), corrections before build from the plan's `Challenged:` line (None, and a named confound, when a challenged card left no line — never a zero), the review record's findings by ring from each disposition's class (`feature` inside, `seam` adjacent, `boundary` outside; records older than the class token count without rings), escapes as live defects naming the card within fourteen days of its close (`board/dial.py::filed_against`, the same reading `needle fixes` makes), stops from the card's history, a reverting commit on the trunk (`runtime.reverted`), hours from the first Start to the close on the card's history, and tokens from the lane's transcripts counted once by request (`runtime/transcripts.py::tokens`, `machine burn`'s definition, read on the machine that holds the lane through a `needle tokens` verb). Every observation lists the files and facts it read. `needle team needle` on a copy of the store on 2026-09-11 read #54 and #59 from those facts alone; `tests/board/test_team.py::test_changing_or_deleting_a_source_fact_changes_the_observation` holds the second clause; the store keeps no count. Send-backs are the owner's moves of the card out of Executed or Done after its close, from the history; the fold's rework is a reverting commit and the trunk's commits naming the card within a week of the lane's tip (`runtime/git.py::fixes_after`). Escapes count defects only — never ideas — live or archived since, born after the close by the board's own birth of the defect's card, to the day of its stem when it has no card. What is unread and says so: tokens for a lane whose machine is silent or whose make keeps no transcript the reader knows (Codex rollouts), and a round's corrections when the plan carries no Challenged line.

### 3. Quality decides first; efficiency breaks a quality tie

Compare each work shape across accountable hand alone, same-make challenge, and different-make challenge. The triage seat #59 exposes as a typed runtime request is one such work shape, and the first with a founding observation (#59's own plan: twelve corrections before build under a declared different-make challenge): #59 names no make, and this router decides who fills the seat and whether the difference survives (Sol's challenge of #59, 2026-09-05, moved that choice here so routing doctrine never encodes an experimental arm). Corrections before build and escaped defects after close decide first. Time and tokens are always shown but choose only between compositions that do not differ on quality. Findings are presented with the work shape and sample count so harder assignments cannot silently make a composition look worse. Done means: complete evidence names the leading composition; incomplete evidence says “exploring” and chooses the next under-sampled composition without claiming it is optimal; every choice preserves its underlying facts.

**Met, with the triage seat deviated:** `board/team.py::read_shape` compares the three compositions per shape — judgment (gated high or xhigh) and bounded (low or medium), the shape read from the gate every started card has. Escaped defects and corrections before build order first; mean hours, then tokens, break only a quality tie, and the reading says which decided (`tests/board/test_team.py::test_time_breaks_only_a_quality_tie`, `…test_one_escaped_defect_denies_the_lead…`). Complete evidence names the leader as `earned` or `best-quality`; incomplete evidence says `exploring` and names the sample and the next under-sampled composition; every tally is recomputed from its observations. **Deviated:** the triage seat is a shape the router cannot yet choose for, and says so rather than pretending: `runtime/launch.py::windowless` gives a windowless seat to Claude only, and #59 rules the seat one verifier and never a committee, so its one executable composition is the hand alone and the route reads `unavailable` (`tests/board/test_team.py::test_a_reading_seat_has_one_composition_and_says_so`). Whether the different-make difference survives on that seat is unmeasured until a card gives the other make a windowless session; #59's twelve corrections are counted as a judgment-shape observation, which is what they were — a plan challenged before its lane.

### 4. The router applies the evidence and keeps it falsifiable

A composition earns the default for that work shape only if the comparison's predeclared threshold is met, and the router applies it automatically at Start. One card in four explores a non-default composition, and any participating model change makes the old evidence stale and returns that work shape to exploration. A card-specific safety or intent constraint overrides composition and says why; convenience does not. The routing policy is versioned, reversible in one change, and never edits doctrine merely because a winner changes. Done means: fixtures cover earned, tied, incomplete, unavailable and stale conclusions; every route links to its observations; changing the source evidence changes the next assignment; rollback restores the previous policy without altering a card already in flight; Dennis is asked only when colleagues surface unresolved intent divergence.

**Met:** the threshold is the Loop's, as constants with their reasons (`domain/team.py`: three trials to judge, two of the first three correcting, no escape within fourteen days); `board/team.py::route_for` applies an earned leader, sends one card in four (by its number, so the board can read which) past the leader to the least-sampled composition, explores from the shape's bootstrap while evidence is incomplete, honours a plan's own `Composition:` line as a pin with its reason, and answers `stale` when an observation's hand model is not the model the rule names now — with the honest limit that the rule names no model for a top rung today (card #63's close), so the stale test bites once the machine's card makes the answer name it. Fixtures cover earned, tied, incomplete, unavailable, stale and pinned (`tests/board/test_team.py`, thirteen router and reading cases). Every route lists its observations as `#N`; changing the source evidence changes the next assignment and never a card already in flight, because the assignment is a row written once; the policy is one version string (`POLICY`) on every assignment, so a rollback is one edit of the constants and the date, visible on every card started after it. Nothing here edits doctrine, and Dennis is asked nothing: a card asks him only as any lane does.

## Acceptance criteria

1. Every card started after this slice receives and executes one predeclared composition without Dennis choosing or relaying between colleagues; #54 is retained as the first different-make observation.
2. The output orders corrections and escapes ahead of time and tokens, names confounds and sample size, and never calls debt or missing evidence a win.
3. Every source fact has one authoritative home; the new code stores only the predeclared composition and derives the rest.
4. The router automatically applies an earned leader and automatically explores when evidence is incomplete; a model change and the one-in-four exploration rule can both dethrone a default through fresh evidence.
5. One accountable hand exists on every composition; collaboration ends in execution or an intent-bearing question, never an unbounded committee.
6. The routing decision is reversible, visible and linked to evidence; no permanent “Claude implements, Codex reviews” role exists and no routing update requires Dennis.

## Loop

We think automatic evidence-directed composition will outperform human-scheduled collaboration because every eligible card contributes evidence and Dennis cannot become the coordination bottleneck. Bootstrap: high-judgment design explores from #54's different-make observation; bounded mechanical work begins with one accountable hand; an unknown shape chooses its least-sampled executable composition. Different-make becomes the earned leader for a work shape only if it produces a material correction missed by the accountable hand's own review in at least two of its first three eligible trials and no trial has a defect filed against it within fourteen days. Time and tokens are recorded from the first trial and decide only a quality tie. If the threshold is not met, the best quality result leads; if evidence is incomplete or shapes are not comparable, the router explores and says so; when a named model changes, that shape's comparison is stale and runs again. If automatic composition raises escaped defects, unresolved loops or owner interruptions, revert the routing policy in one change while retaining the evidence.

## Deliberately not

- A second telemetry stream, manually maintained scorecard or universal scalar productivity score.
- Equating “team” with two AIs on every card; a measured single accountable hand may be the optimal composition.
- Automatic doctrine edits or permanent provider roles.
- Asking Dennis to schedule collaboration or judge test mechanics, defect attribution, token counts or elapsed time.

## Terrain

- `api/dial.py::FixReport`, card history and defect lineage
- review records and HOW-WE-WORK's inside/adjacent/outside rings
- `machine burn`, git history and lane timestamps
- #51's corrections table, #54's amended close-out, and model-role history

## Close-out

Written by the lane: the three observations and why their work shape is comparable; composition declared before each; corrections and escapes with source links; review-ring findings, send-backs, rework, time and tokens; the conclusion or “insufficient evidence”; any `Fix: his` suggestion; next exploration and model-change trigger.

### What the close wrote

- **The three observations, and why their shape is comparable:** all three are
  judgment work — a plan gated high, challenged before its lane by a colleague
  of the other make — which is the shape the bootstrap explores from. Read by
  `needle team needle` on 2026-09-11 from a copy of the store and the checkout,
  nothing hand-kept:
  - **#54** (a new project follows the way we work on any machine): declared in
    `docs/reviews/2026-09-05-54-a-new-project-follows-the-way-we-work-on-any-machine.md`,
    its Composition line — one Claude lane, one Codex thread called four times.
    Corrections before build: unread, because the record predates the
    `Challenged:` grammar (its own words: nine findings changed the table, three
    rows reached the owner contested — read by hand, not counted). **One
    escape**: `docs/slice-suggestions/done/2026-09-07-a-finished-cards-lane-is-gone-from-the-disk-once-its-work-is-folded.md`,
    filed by the owner's session two days after the close and naming the card
    among twelve whose worktrees were left behind (since fixed, still an
    escape); the defect the lane itself filed in the walk is by the card, not
    against it, and is not counted. Stops: 0; no send-back; fold stands; three
    commits naming the card landed on the trunk within a week of its tip;
    2.2 h from the first Start to the close on the card's history; tokens
    unread (the lane ran on the laptop and the reading ran on the rented
    machine).
  - **#59** (a defect's mark is verified before it routes): declared in its plan's
    Composition line, before the challenge ran. Twelve material corrections
    before build (its Challenged line). Fourteen review findings, no rings (the
    record predates the class token). **One escape**: the same worktrees defect,
    naming this card too; the three defects the lane filed from its own review
    and close (`…a-short-job-the-board-opened-for-itself…`, `…one-word-never-names-two-different-things…`,
    `done/…a-loop-cannot-close-itself…`) are by the card and not counted. One
    stop; no send-back; fold stands; no fixing commit within a week; 2.6 h;
    tokens unread.
  - **#58** (this card): declared in this plan's head at the lane's own start.
    One material correction before build (the Challenged line). Its findings,
    escapes and hours become readable when this close lands and the fourteen
    days pass; the reading counts it then, by the same reader.
- **Send-backs and rework:** none on #54 or #59 (one stop on #59); no revert;
  three fixing commits within a week on #54, none on #59 — read again after
  the review's repairs by the same reader on the same copy, escapes now by
  the board's own birth of each defect's card and never a defect the card's
  own lane filed.
- **The conclusion:** insufficient evidence — `judgment: exploring`, two trials
  under different-make and none under the other two compositions, with two
  named confounds (an unread round, a sample of two). No composition is called
  a winner. The one escape each on #54 and #59 is already what the threshold
  reads: a different-make challenge that escapes a defect within fourteen days
  does not earn the lead however many corrections it made — and both escapes
  are one defect about the close ritual leaving worktrees behind, which the
  reader cannot tell from a defect in the work; that is a confound the
  owner reads off the sources, not one the number hides.
- **`Fix: his` suggestions:** none. The one decision this card met that was
  his — whether an `alone` composition may skip the independent review — was
  answered by his ruling of 2026-09-11 (§13) before the lane began, and the
  code follows it.
- **Next exploration:** the judgment shape keeps exploring different-make until
  it has three trials (the bootstrap), then the least-sampled composition —
  alone, then same-make; the bounded shape begins alone. The first card started
  after this fold is assigned by the board, not by anyone's memory.
- **The model-change trigger:** an observation whose hand model differs from the
  rule's current answer, or whose challenger's model differs from what a fresh
  call would run now, is set aside and the shape reads `stale` until a fresh
  cohort of three trials per composition judges again; the record keeps the
  old trials. Today the rule names no model for a top rung and Codex's
  configuration names no model, so the trigger arms when the machine's card
  makes `claude-acct best` name the rung (#63's close-out, the machine-side
  card) or `~/.codex/config.toml` names one.
