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
something.
"""

from datetime import datetime

from domain.hook import HeardMark, Word
from domain.lane import HANDS_ON, Lane
from domain.watercooler import WatercoolerLine

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
    """The word for a lane and the mark to write when it says something;
    the mark is None when there is nothing new. `lines` is the project's
    watercooler, oldest first, at least every line past the mark; `mark`
    where the lane's hearing stands, or
    None when it has never been told anything — then the lines its brief
    already carried, said before `since` (the lane's first sighting, which
    outlives a resume of its session), are heard. A lane without hands on
    its worktree is told nothing: there is no session to hear it."""
    empty = Word(project=slug, card_number=lane.card_number, sentences=[], read_at=read_at)
    if lane.state not in HANDS_ON or lane.path is None:
        return empty, None
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
        # The lane's own lines advance the mark silently when the next word
        # is written; nothing to say means nothing to write.
        return empty, None
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
