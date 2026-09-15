"""Auto-fix stops at the line the owner drew (card #149), on the pure side.

What is held here:
- the one comparison: a band is at or above a line by the ladder's order,
  and the last rung takes every graded band;
- the line's words: one phrase per rung, the last rung "takes every
  defect", and the owner's words back to a rung, refusing anything else;
- `why_not_eligible` leaves a verified defect below the line with the
  line's own sentence and takes one at or above it;
- a planned card below the line is held and does not count, exactly as a
  card whose switch went off is (ruling 5);
- a board's line at a moment is read from the audit of turns, the last
  rung until a row names one, unmoved by a change of the number.
"""

from datetime import timedelta

from board.dial import below_line_words, held_lanes, line_at, running, why_not_eligible
from board.triage import (
    EVERY_DEFECT,
    LINE_WORDS,
    at_or_above,
    line_from_words,
    line_rungs,
    line_words,
)
from domain.card import Actor
from domain.dial import DialChange, FixStage
from domain.triage import Band, Breaks, Reach
from tests.board.test_dial import NOW, card, fix, routed_for, suggestion, verified
from tests.board.test_grade import grade


def test_a_band_is_at_or_above_a_line_by_the_ladders_order():
    assert at_or_above(Band.HARM_OUTSIDE, Band.HARM_OUTSIDE)
    assert not at_or_above(Band.LIES, Band.HARM_OUTSIDE)
    assert at_or_above(Band.LIES, Band.LIES) and at_or_above(Band.HARM_OUTSIDE, Band.LIES)
    assert not at_or_above(Band.LOSES, Band.LIES)
    # The last rung is above nothing: a line there takes every graded band.
    assert all(at_or_above(band, Band.NOTHING) for band in Band)


def test_the_line_is_said_as_where_auto_fix_stops_and_read_back_from_the_owners_words():
    """Ruling 4: one phrase per rung wherever it is said; the last rung is
    "takes every defect", never the ladder's own word for it."""
    assert line_words(Band.HARM_OUTSIDE) == "stops at harm outside"
    assert line_words(Band.NOTHING) == "takes every defect"
    assert set(LINE_WORDS) == set(Band)
    assert line_from_words("harm outside") is Band.HARM_OUTSIDE
    assert line_from_words("  Lies ") is Band.LIES
    assert line_from_words(EVERY_DEFECT) is Band.NOTHING
    assert line_from_words("every  defect") is Band.NOTHING
    # The ladder's last word is refused as a line: on a switch it would read
    # as "no line", and there is no such thing (ruling 3).
    assert line_from_words("nothing") is None
    assert line_from_words("elsewhere") is None
    assert line_rungs() == "harm outside, lies, loses, costs, looks, or every defect"


def test_a_verified_defect_below_the_line_is_left_with_the_lines_sentence():
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    common = dict(
        routed=routed_for(now, verified(now)),
        last=None,
        lane=None,
        planning_open=False,
        triage_open=False,
        ran_before=False,
    )
    costs = grade(Breaks.COSTS, Reach.YOU)
    harm = grade(Breaks.LOSES, Reach.MONEY)
    # No line, or the last rung: every verified defect is the dial's, as before.
    assert why_not_eligible(card(1, "a"), now, **common, grade=costs) is None
    assert why_not_eligible(card(1, "a"), now, **common, grade=costs, line=Band.NOTHING) is None
    # A line at harm outside: the costs card is filed, the harm card taken.
    filed = why_not_eligible(card(1, "a"), now, **common, grade=costs, line=Band.HARM_OUTSIDE)
    assert filed == "below this board's line at harm outside" == below_line_words(Band.HARM_OUTSIDE)
    assert why_not_eligible(card(1, "a"), now, **common, grade=harm, line=Band.HARM_OUTSIDE) is None
    # At the line is above it: a costs card with the line at costs is taken.
    assert why_not_eligible(card(1, "a"), now, **common, grade=costs, line=Band.COSTS) is None
    # A defect with no standing grade has no band to compare: the line says
    # nothing of it (the beat reads it again first, card #100).
    assert why_not_eligible(card(1, "a"), now, **common, grade=None, line=Band.HARM_OUTSIDE) is None


def test_a_planned_card_below_the_line_is_held_and_does_not_count():
    """Ruling 5: as #80's review finding 1 settled for the switch — a plan is
    not execution until Start, and the line at that moment applies."""
    lanes = [fix(FixStage.PLANNED, 2), fix(FixStage.PLANNED, 3), fix(FixStage.STARTED, 5)]
    below = {2: below_line_words(Band.HARM_OUTSIDE)}
    held = held_lanes(
        lanes,
        lambda project, number: True,
        lambda project: True,
        None,
        lambda project, number: below.get(number),
    )
    assert [f.card_number for f in held] == [2]
    assert running(lanes, held) == 2, "the planned card above the line, and the started one"
    # Without the reader every planned card with an open door runs, as before.
    assert held_lanes(lanes, lambda project, number: True, lambda project: True) == []


def test_a_boards_line_at_a_moment_is_read_from_the_audit_of_turns():
    """Item 2: the last row at or before the moment that names the board and
    carries a line says; a change of the number carries none and moves
    nothing; no row by then is the last rung, which is how every board is
    born and where auto-fix reached before the line existed."""

    def turned(n: int, at, project, on, line=None, lanes=1):
        return DialChange(
            id=n, at=at, actor=Actor.OWNER, project=project, on=on, lanes=lanes, line=line
        )

    t = NOW
    changes = [
        turned(1, t, "a", True),  # a switch turn from before the line: no line on the row
        turned(2, t + timedelta(hours=1), "a", None, line=Band.HARM_OUTSIDE),
        turned(3, t + timedelta(hours=2), None, None, lanes=4),  # the number alone
        turned(4, t + timedelta(hours=3), "b", None, line=Band.LIES),
        turned(5, t + timedelta(hours=4), "a", False, line=Band.HARM_OUTSIDE),  # off, line kept
        turned(6, t + timedelta(hours=5), "a", None, line=Band.NOTHING),
    ]
    assert line_at(changes, "a", t - timedelta(seconds=1)) is Band.NOTHING
    assert line_at(changes, "a", t) is Band.NOTHING
    assert line_at(changes, "a", t + timedelta(hours=1)) is Band.HARM_OUTSIDE
    assert line_at(changes, "a", t + timedelta(hours=2, minutes=30)) is Band.HARM_OUTSIDE
    assert line_at(changes, "b", t + timedelta(hours=2, minutes=30)) is Band.NOTHING
    assert line_at(changes, "b", t + timedelta(hours=3)) is Band.LIES
    assert line_at(changes, "a", t + timedelta(hours=4, minutes=30)) is Band.HARM_OUTSIDE
    assert line_at(changes, "a", t + timedelta(hours=9)) is Band.NOTHING
    # Read in the order of moments, never ids: a clock that stepped back
    # between two turns cannot end the read early.
    late_id = [turned(9, t + timedelta(hours=1), "a", None, line=Band.LOSES)] + changes[1:]
    assert line_at(late_id, "a", t + timedelta(hours=1)) is Band.LOSES
