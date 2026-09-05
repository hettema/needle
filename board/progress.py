"""How far a running lane has come, read from the lane's own copies (plan 13).

The board never judges an item. It reads the plan as the lane's worktree
carries it — the trunk's copy is the plan as it stood at Start — counts the
stances the session wrote, and once every item is met reads the review
record the same worktree holds and counts its passes and findings. Pure over
text: the caller reads the files, and hands the review texts in as a
callable so they are read only when the item count says the lane is in its
review loop.

Proof of search: `board/collision.py::footprint` reads a plan's text with an
`exists` callable from the loop in the same way; `board/handouts.py` judges
a plan's handouts against the machine. Neither carries an item's stance or a
lane's count.
"""

from collections.abc import Callable
from datetime import datetime

from board.parse import items_of, plan_stem_of, review_of
from domain.document import Review, Stance
from domain.lane import Progress


def progress_of(
    plan_text: str,
    *,
    plan_stem: str,
    read_reviews: Callable[[], list[tuple[str, str]]],
    now: datetime,
) -> Progress | None:
    """The lane's progress from its copy of the plan: None when the plan has
    no items, so a plan written as one promise shows the signed card and
    nothing new. `read_reviews` yields (path, text) for every record under
    the lane's `docs/reviews/`; the one whose `Plan:` line names this plan
    is the lane's, and it is read only once every item is met."""
    items = items_of(plan_text)
    if not items:
        return None
    met = sum(1 for item in items if item.stance == Stance.MET)
    deviated = sum(1 for item in items if item.stance == Stance.DEVIATED)
    marked = [item for item in items if item.stance is not None]
    review: Review | None = None
    if met + deviated == len(items):
        for path, text in read_reviews():
            if plan_stem_of(text) == plan_stem:
                review = review_of(text, path)
                break
    last = marked[-1].title if marked else None
    return Progress(
        items=items,
        met=met,
        deviated=deviated,
        total=len(items),
        last=last,
        read_at=now,
        review=review,
        line=progress_line(met, deviated, len(items), last, review),
    )


def progress_line(
    met: int, deviated: int, total: int, last: str | None, review: Review | None
) -> str:
    """The one line under the strip, in the lane's words: the item count
    while items are open, the review counter once every item is met and a
    record exists. Composed here so the page invents nothing (plan 27)."""
    if review is not None:
        counts = f"{review.found} found, {review.fixed} fixed"
        if review.no_change:
            counts += f", {review.no_change} no change"
        counts += f", {review.filed} filed"
        passes = len(review.passes)
        if review.clean:
            return f"review clean · {passes} pass{'es' if passes != 1 else ''} · {counts}"
        return f"review · pass {passes} · {counts}"
    line = f"{met} of {total} met"
    if deviated:
        line += f", {deviated} deviated"
    if last:
        line += f" · last: {last}"
    return line
