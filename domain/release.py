"""What a board says cannot be undone, and a release that waits on it.

Card #139: the auto-fix switch is the owner's standing ruling about what
enters *execution* without him. On a project that deploys from its stable
branch it was also deciding, silently, what reaches *customers* without
him — a session the board started closed like any other, a close promoted
the stable branch, and the deploy ran the schema changes against live rows
on boot. The two rulings are separated here.

The declaration rides with the ruling it bounds: turning a board's auto-fix
on says what cannot be taken back there, and where that project's standing
hold on releasing is written. A board that names nothing has nothing, and
everything there releases exactly as it did before.

The test is on the *range* — everything the promotion would carry, whoever
put it there — and never on the folding session's own change. Reading only
its own change leaks: the archive gate that pushes a session toward the
release is itself range-based, so the very next ordinary fix would promote
a held schema change to get past a refusal it did not cause. That leak is
what made this a defect rather than a preference, and
`tests/ratchets/test_a_release_is_decided_on_the_range.py` holds it.
"""

from datetime import datetime

from pydantic import BaseModel


class Undoable(BaseModel):
    """What cannot be taken back on one board, as the owner declared it when
    he turned that board's auto-fix on.

    An empty `paths` is a declaration that nothing there is irreversible —
    every release ships — which is a different fact from a board that has
    never declared (no `Undoable` at all), and the head says which."""

    paths: list[str]
    """Repository paths, each a file or a folder: a release carrying
    anything under one of them is the owner's. Hello Revenue's is its
    migrations folder, because the container runs `alembic upgrade head`
    on every boot and better than one migration in five rewrites or
    deletes live rows."""
    hold: str | None
    """Where this project's standing hold on releasing is written, relative
    to its root, when it has such a lever; None when it has none. The file
    is what keeps the closes behind a held release from meeting their own
    archive refusal — without it one waiting card becomes every card behind
    it half-closed."""
    declared_at: datetime
    """When the owner last said it, at a turn of this board's switch."""


class Release(BaseModel):
    """What promoting a project's stable branch would carry right now: the
    range between that branch and the shared one, read in the project's own
    checkout on whichever machine holds it.

    `read` False is never an empty range: a machine that could not be
    reached, a checkout with no stable branch and a git that refused all
    answer with the reason in `note`, so a reader never mistakes "nothing
    to carry" for "nothing could be seen"."""

    files: list[str]
    commits: int
    read: bool
    note: str | None
    read_at: datetime | None = None


class Held(BaseModel):
    """One board's release, waiting on the owner: the work is on the shared
    branch, the stable branch stands where it was, and promoting it is his
    act. What the head counts, what holds the next card of the same shape,
    and the one sentence the card shows."""

    project: str
    carries: list[str]
    """The declared paths the range carries, as the owner declared them."""
    files: list[str]
    """The files in the range under those paths, first mention first."""
    commits: int
    hold: str | None
    """This project's standing hold file, as declared; None when it names none."""
    hold_stands: bool
    """That file is in the project's checkout right now. False with a `hold`
    named is the state a dead session leaves behind — the release waits and
    nothing holds the closes queued behind it."""
    cards: list[int]
    """The cards answerable for this release, newest first."""
    claimed: bool
    """A fold actually recorded that it left the release for him. False is a
    session that died between its fold and its hold: the cards above are
    then the board's own reading of which work the release carries, and the
    card reads as unheld and unclaimed rather than as done (item 5)."""
    sentence: str
    """The work, the waiting, whose move — one sentence, written once
    (`board/release.py::sentence`) and shown everywhere: the fold's own
    refusal, the card's WAITS row, and the head."""
    read_at: datetime
