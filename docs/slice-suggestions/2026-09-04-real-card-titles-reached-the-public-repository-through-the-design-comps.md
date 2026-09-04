# Real card titles reached the public repository through the design comps

**Kind:** defect
**Found by:** the lane on card #26 (plan 10), running the suite after rebasing
onto `origin/develop` and finding the synthetic-fixture ratchet red on develop
itself, from commit `16a8023` (2026-09-04).

## Observation

`tests/ratchets/test_the_fixture_project_is_synthetic.py::test_no_real_card_title_is_in_the_tracked_tree`
fails on `origin/develop`: eight of Hello Revenue's real card titles are in
`docs/design/2026-09-04-the-colour-language/Card.dc.html`, `Main.dc.html` and
`Triage.dc.html`, used as the comps' sample content — "a paid invoice reaches
the ledger", "tell production which ad accounts are ours", "the pen writes on
pictures", "the homepage walk through tells one campaign in three ad formats",
"google keyword pools open the whole market", "brief written in the market's
language", "the coordinator stops growing into the next campaign service", "a
failed check repairs the line not the answer".

This is the leak that ratchet was written to stop: `tools/board_fixture.py`
exists because a hand-written page fixture "carried a real project's card
titles into a public repository", and the ratchet is the guard that followed.
The guard held for the fixture and the comps went round it, because a design
comp is a new kind of file that needs sample cards and nothing told its author
where synthetic ones live.

Two costs, not one. The leak itself: a customer project's roadmap titles are in
a public repository's history, and a `git rm` does not take them out of it. And
a red trunk: every lane's fold rule is "when the suite is green", so every lane
that rebases onto develop now inherits a failure it did not cause and has to
reason about whether to fold anyway. Card #26's lane hit exactly that.

## What would hold it

The synthetic project under `tests/fixtures/harbourmaster/` is the one source
of sample card titles, and a design comp draws from it like the fixture does —
so the ratchet's list is the only place real titles could enter, and it already
refuses them. The gap is that nobody writing a comp knows that: name it where a
comp is written (the design skill's own instructions, or a line in
`docs/design/README.md` pointing at the harbourmaster titles), so the synthetic
source is the obvious one rather than the one you find by failing a ratchet.

The trunk half is separate and larger: a lane whose fold lands a commit that
turns the suite red on develop leaves every other lane holding a failure it did
not cause. A pre-fold gate — `needle fold` running the ratchets, or refusing a
fold whose commit fails them — would have caught this one before it landed, and
is the mechanism that makes "the fold is when the suite is green" a fact rather
than a convention.

**Ring:** outside card #26's change (`CLAUDE.md`'s rings rule), inside card
#27's, whose lane wrote these files and was live when this was filed. Said on
the watercooler to #27 at the same time, so the lane that can fix it heard it
while it ran — which is the mechanism card #26 was building.
