# Cross-repo knowledge sharing: one board asks another for a signal

**Found by:** the owner, 2026-09-04, reasoning about two repos that hold
something similar: "One repo being able to query another repo to see if it
already has directional signal or data feels like it could be valuable. As
long as the enquiring party remains sceptical and verifies rather than
believes." And: "I guess it's a feature that needs some way to turn repos
on/off to be included in cross repo knowledge sharing."
**Kind:** idea

## Observation

Every project on the board keeps its signals, verdicts and rulings in one
grammar, in one store, but each project's board reads only its own. A
session in Hello Revenue that is about to test a Meta policy assumption has
no way to ask whether Needle, or the machine, or another project already
carries a signal that was read — or a ruling that settled it. Today that
knowledge crosses repos only through the owner's memory or a session that
happens to read the other tree, which is the failure mode the board exists
to remove.

The doctrine test that separates sharing from duplication (machine repo,
2026-09-04): if a change in one repo would have to be made in the other for
both to stay correct, it is one mechanism and gets one owner; if not, the two
realities may read each other freely — and the reader cites and verifies,
never believes.

## Done means

- A project on the board can be marked as **sharing** or not; the default is
  not. Only sharing projects answer queries from other projects, and only a
  sharing project's cards can be cited across the boundary.
- `needle signals --across <query>` (and the same from the board) returns,
  from every sharing project, the signals and verdicts whose subject matches:
  the card, the project, the signal's grammar row, when it was last read and
  what it read. A session opening a lane can ask it in one command; the
  brief a lane opens with can carry the matches for its card's subject.
- Every match is a **citation, not a fact**: the row says which project and
  card it came from and when it was read, and a card that leans on another
  project's signal writes a WATCH row of its own that re-reads the cited
  signal on its own cadence. Nothing is copied into the asking project's
  corpus; a copy would be the duplication the doctrine test refuses.
- The owner sees, on a card, which of its rows cite another project, and on
  the project's page which projects may ask it.
