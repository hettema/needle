"""Whether a release may go without the owner, and the one sentence it says.

Card #139. The rule is one line: a session the board started does not
promote the stable branch when the range that promotion would carry holds
a path the board declared cannot be undone — whoever put it there.

Two things make the rule right rather than merely strict.

The read is on the **range**, never on the folding session's own change.
Hello Revenue's archive gate, which is what pushes a closing session toward
the release at all, is itself range-based: it refuses while production paths
on the shared branch have not reached the stable one. So a rule that asked
"did *this* session touch the migrations folder" would let the very next
ordinary fix promote a held schema change to get past a refusal it did not
cause — the leak that made this a defect. `tests/ratchets/
test_a_release_is_decided_on_the_range.py` fails if anyone narrows it back.

And the test is on a **path appearing**, never on a judgement about what
the change does. Asking an unattended session at three in the morning
whether its own migration is destructive is the defect, not the fix; a file
under a declared folder is the cheap, loud stand-in the owner chose on
2026-09-12 after the numbers said blocking every release to guard one class
in five buys too little.

Pure over domain values: the git range comes from `runtime/git.py::release`,
the declaration from the board's switch, and everything decided about them
is here.
"""

CARRIED_SHOWN = 3
"""How many of the waiting files the sentence names before it says "and N
more": the owner reads the sentence to know which release is waiting, not
to review it."""


def _normalise(path: str) -> str:
    return path.strip().strip("/")


def carried(files: list[str], declared: list[str]) -> list[str]:
    """Which declared paths this set of files carries, in the owner's own
    order: the one match used both for what a release would carry and for
    what a plan names, so the release that waits and the card the board
    holds behind it are decided by the same reading.

    A declared path matches a file that is it, or that sits under it: a
    folder is how a project names an irreversible surface (`alembic/
    versions`), and a single file is how it names one. Never a substring —
    `alembic/versions` must not match `alembic/versions_old/x.py`."""
    found: list[str] = []
    for path in declared:
        want = _normalise(path)
        if not want:
            continue
        if any(_normalise(f) == want or _normalise(f).startswith(f"{want}/") for f in files):
            found.append(path)
    return found


def under(files: list[str], declared: list[str]) -> list[str]:
    """The files of the range that sit under the declared paths, first
    mention first: what the sentence names and what the owner will read."""
    wanted = [_normalise(path) for path in declared]
    return [
        f
        for f in files
        if any(_normalise(f) == want or _normalise(f).startswith(f"{want}/") for want in wanted)
    ]


def _listed(files: list[str]) -> str:
    shown = ", ".join(files[:CARRIED_SHOWN])
    more = len(files) - CARRIED_SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


def sentence(
    project: str,
    *,
    files: list[str],
    hold: str | None,
    hold_stands: bool,
    unreadable: str | None = None,
) -> str:
    """The work, the waiting, whose move — written once and shown
    everywhere: the refusal on the folding session's screen, the WAITS row
    on the card, and the card's own face. One wording, so a cold reader who
    meets it twice never wonders whether they are two different facts
    (item 3's done means).

    It opens lowercase and names no mechanism the owner does not use — no
    branch flag, no verb, no code path — because the face wraps it after
    "Your move:" and the owner's steering says a house term carries nothing
    to him."""
    waiting = (
        f"what this release would carry could not be read ({unreadable}), and {project} names "
        "things there that cannot be undone"
        if unreadable
        else f"this release would carry {_listed(files)}, which {project} says cannot be undone"
    )
    if hold and hold_stands:
        behind = f"{hold} keeps the work finishing behind it from stalling until you do"
    elif hold:
        behind = f"{hold} is not there, so the work finishing behind it will stall"
    else:
        behind = (
            f"{project} names nothing that holds the work finishing behind it, so some of it "
            "may stall"
        )
    return (
        "the work is on the shared branch and the stable branch is where it was, because "
        f"{waiting}; promoting it is yours, and {behind}."
    )
