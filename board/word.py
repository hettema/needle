"""What the board tells a running lane, and when it has said it (plan 10).

A lane hears its neighbours in its brief at Start and in `needle fold` at
the end, and until this slice nothing in between: a collision that began
after Start was seen by the owner on the pill and by no one in the lane.
The word is what the board has learned about a lane since the lane last
listened — its drift into another lane's file, and what other lanes said on
the watercooler — one sentence per fact, said once. "Once" is a mark in the
store, never memory in the hook (plan ruling 3), and the drift is the loop's
last read, never git (ruling 4). Pure: the caller reads the snapshot and
the store and hands them in, and writes the mark back when the word says
something. A note landing on the machine's watercooler is one more
sentence in the same word (plan 17, item 2), never a second delivery.
"""

from datetime import datetime

from domain.hook import HeardMark, Word
from domain.lane import HANDS_ON, Lane
from domain.watercooler import Note, WatercoolerLine

SAY_SO = "Say in the watercooler what you are doing there."
CLEARED = "The collision has cleared: no other live lane is editing a file this lane is editing."


def _line_sentence(line: WatercoolerLine) -> str:
    who = "The board" if line.card_number is None else f"#{line.card_number}"
    return f"{who} said on the watercooler: {line.text}"


def compose(
    slug: str,
    lane: Lane,
    lines: list[WatercoolerLine],
    mark: HeardMark | None,
    *,
    since: datetime | None,
    now: datetime,
    read_at: datetime,
) -> tuple[Word, HeardMark | None]:
    """The word for a lane and the mark to write, or None when the mark
    already says where the lane's hearing stands.

    The mark moves whenever hearing moved, which is not only when the word
    says something: a lane that is told nothing still records the baseline
    it started from, and a lane whose own lines went by records passing
    them. Otherwise a quiet lane would keep no mark, and every tool call it
    makes — thousands over a lane-day — would read the project's whole
    watercooler again to work out that it had nothing to hear. Only a word
    that said something stamps `at` and `text`, which is what the card
    shows.

    `mark` is where the lane's hearing stands, and it decides how much of
    the watercooler `lines` must carry — the caller reads exactly that
    much, because this runs on every tool call:

    - a mark, and `lines` need only be the lines past `mark.watercooler_id`;
    - no mark (the lane has never been told anything), and `lines` must be
      the project's whole watercooler, because the baseline is read from
      it: everything said before `since` was already in the lane's brief
      and counts as heard.

    `since` is the lane record's first sighting, not the session's start,
    so a resume — which forks the session id — keeps what the lane heard.
    A lane without hands on its worktree is told nothing: there is no
    session to hear it."""
    empty = Word(project=slug, card_number=lane.card_number, sentences=[], read_at=read_at)
    if lane.state not in HANDS_ON or lane.path is None:
        return empty, None
    known = mark
    if mark is None:
        heard_upto = max(
            (ln.id for ln in lines if since is None or ln.at <= since),
            default=0,
        )
        mark = HeardMark(
            project=slug,
            card_number=lane.card_number,
            watercooler_id=heard_upto,
            collision=None,
            at=None,
            text=None,
        )
    sentences: list[str] = []
    colliding = lane.colliding.sentence if lane.colliding is not None else None
    if colliding != mark.collision:
        sentences.append(f"{colliding} {SAY_SO}" if colliding is not None else CLEARED)
    unheard = [
        ln for ln in lines if ln.id > mark.watercooler_id and ln.card_number != lane.card_number
    ]
    sentences.extend(_line_sentence(ln) for ln in unheard)
    newest = max(
        (ln.id for ln in lines if ln.id > mark.watercooler_id), default=mark.watercooler_id
    )
    if not sentences:
        # Nothing to say means the drift already reads as the mark records
        # it, so only the watercooler can have moved: the baseline of a lane
        # never told anything, or the lane's own lines going by.
        quiet = mark.model_copy(update={"watercooler_id": newest})
        return empty, None if quiet == known else quiet
    word = Word(project=slug, card_number=lane.card_number, sentences=sentences, read_at=read_at)
    moved = mark.model_copy(
        update={
            "watercooler_id": newest,
            "collision": colliding,
            "at": now,
            "text": " ".join(sentences),
        }
    )
    return word, moved


def notes_word(
    notes: list[Note],
    stamps: dict[str, datetime],
    *,
    party_to: set[str],
) -> tuple[list[str], dict[str, datetime]]:
    """The sentences for the notes on the machine's watercooler that a lane
    is party to and has not heard (plan 17, item 2), and the stamps to
    write so each is said once. `party_to` names the notes the lane's card
    or its calls name; a note the lane wrote itself was stamped at the
    write (the hook says so) and is never heard back, while a later change
    to it by another party moves the file past the stamp and is heard.
    Pure, like `compose`."""
    sentences: list[str] = []
    moved: dict[str, datetime] = {}
    for note in notes:
        if note.path not in party_to:
            continue
        heard = stamps.get(note.path)
        if heard is not None and note.at <= heard:
            continue
        what = "changed" if heard is not None else "landed"
        head = f" — {note.first_line}" if note.first_line else ""
        sentences.append(f"A note {what} on the machine's watercooler: {note.path}{head}")
        moved[note.path] = note.at
    return sentences, moved
