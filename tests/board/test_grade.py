"""How bad a defect is, and the order that makes (card #100, items 2 and 3),
pure over domain values.

The grade is three parts in the owner's words, each with the reading's
words for what selected it; a grade with a part missing does not hold. The
band is computed from the parts and never landed — harm outside first, then
false before lost, then what costs, then what only looks wrong — and inside
a band who it reaches, then how often, then age. An unread defect sorts
after every graded one, because a grade is what the order is made of. A
grade binds to the document it judged: a changed document has no grade
until it is read again.
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from board.triage import band_of, current_grade, grade_why, grade_words, order_key
from domain.triage import Band, Breaks, Grade, Often, Reach
from tests.board.test_dial import suggestion, verified

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)


def grade(
    breaks: Breaks, reach: Reach | None = Reach.SESSION, often: Often | None = Often.SOMETIMES
):
    return Grade(
        breaks=breaks,
        breaks_words="the document says what breaks",
        reach=reach,
        reach_words="the document says who" if reach else None,
        often=often,
        often_words="the document says how often" if often else None,
    )


def test_a_grade_names_all_three_parts_with_their_words_or_nothing_alone():
    whole = grade(Breaks.LIES, Reach.CLIENT, Often.EVERY_TIME)
    assert whole.breaks == Breaks.LIES and whole.reach == Reach.CLIENT
    with pytest.raises(ValidationError, match="missing"):
        Grade(
            breaks=Breaks.LIES,
            breaks_words="x",
            reach=None,
            reach_words=None,
            often=Often.SOMETIMES,
            often_words="y",
        )
    with pytest.raises(ValidationError, match="missing"):
        Grade(
            breaks=Breaks.COSTS,
            breaks_words="x",
            reach=Reach.YOU,
            reach_words="  ",
            often=Often.SOMETIMES,
            often_words="y",
        )
    with pytest.raises(ValidationError, match="selected what breaks"):
        Grade(
            breaks=Breaks.LOOKS,
            breaks_words=" ",
            reach=Reach.YOU,
            reach_words="x",
            often=Often.SOMETIMES,
            often_words="y",
        )
    # Nothing: the document describes no failure, so no reach and no how-often.
    nothing = Grade(
        breaks=Breaks.NOTHING,
        breaks_words="it asks for a page, and says nothing is wrong",
        reach=None,
        reach_words=None,
        often=None,
        often_words=None,
    )
    assert band_of(nothing) == Band.NOTHING
    with pytest.raises(ValidationError, match="names no reach"):
        grade(Breaks.NOTHING, Reach.YOU, None)


def test_the_band_is_the_doctrines_two_cuts_in_order():
    # Harm outside first: something false or lost that reaches a client,
    # the public or money.
    assert band_of(grade(Breaks.LIES, Reach.CLIENT)) == Band.HARM_OUTSIDE
    assert band_of(grade(Breaks.LOSES, Reach.MONEY)) == Band.HARM_OUTSIDE
    # A cost or a blemish outside is not harm outside: the cut is false or lost.
    assert band_of(grade(Breaks.COSTS, Reach.CLIENT)) == Band.COSTS
    assert band_of(grade(Breaks.LOOKS, Reach.CLIENT)) == Band.LOOKS
    # Then false before lost, inside the owner's own door.
    assert band_of(grade(Breaks.LIES, Reach.SESSION)) == Band.LIES
    assert band_of(grade(Breaks.LOSES, Reach.YOU)) == Band.LOSES


def test_the_order_is_band_then_reach_then_how_often_then_age_and_unread_last():
    old = NOW - timedelta(days=30)
    cards = {
        "looks-client": (grade(Breaks.LOOKS, Reach.CLIENT, Often.EVERY_TIME), old),
        "lies-session-every": (grade(Breaks.LIES, Reach.SESSION, Often.EVERY_TIME), NOW),
        "loses-money-once": (grade(Breaks.LOSES, Reach.MONEY, Often.ONCE_SEEN), NOW),
        "costs-you": (grade(Breaks.COSTS, Reach.YOU, Often.SOMETIMES), old),
        "lies-you-sometimes": (grade(Breaks.LIES, Reach.YOU, Often.SOMETIMES), old),
        "lies-you-every-old": (grade(Breaks.LIES, Reach.YOU, Often.EVERY_TIME), old),
        "lies-you-every-new": (grade(Breaks.LIES, Reach.YOU, Often.EVERY_TIME), NOW),
        "unread-old": (None, old),
        "nothing": (grade(Breaks.NOTHING, None, None), old),
    }
    ordered = sorted(cards, key=lambda name: order_key(cards[name][0], cards[name][1], 0))
    # Pinned exactly: inside the lies band, who it reaches — you before a
    # session — then how often, then oldest first.
    assert ordered == [
        "loses-money-once",
        "lies-you-every-old",
        "lies-you-every-new",
        "lies-you-sometimes",
        "lies-session-every",
        "costs-you",
        "looks-client",
        "nothing",
        "unread-old",
    ]


def test_a_grade_stands_only_for_the_document_it_judged():
    document = suggestion("d", "**Kind:** defect\n**Fix:** now — the plan `docs/a.md` says so")
    triage = verified(document).model_copy(update={"grade": grade(Breaks.LIES)})
    assert current_grade(document, triage) is not None
    edited = suggestion(
        "d", "**Kind:** defect\n**Fix:** now — the plan `docs/a.md` says so", title="Reworded"
    )
    assert current_grade(edited, triage) is None, "a changed document has no grade until read again"
    assert current_grade(document, verified(document)) is None, "a reading from before the scale"
    assert current_grade(None, triage) is None


def test_the_faces_words_are_the_parts_and_the_readings_reasons():
    g = Grade(
        breaks=Breaks.LIES,
        breaks_words="the skipper believes a number that is not true",
        reach=Reach.CLIENT,
        reach_words="a skipper pays what the slip says",
        often=Often.SOMETIMES,
        often_words="every tariff change produces a week of wrong slips.",
    )
    assert (
        grade_words(g)
        == "shows something false as true, reaching a client or the public, sometimes"
    )
    assert grade_why(g) == (
        "the skipper believes a number that is not true; a skipper pays what the slip says; "
        "every tariff change produces a week of wrong slips"
    )
    assert grade_words(grade(Breaks.NOTHING, None, None)) == "describes no failure"
