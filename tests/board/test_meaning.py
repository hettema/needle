"""One shape for every sentence on a face, and the shape agrees with the
colour (card #75, item 1): the opening is bound to the meaning in code, so
a sentence that says "Your move" on a grey face cannot be built."""

import pytest
from pydantic import ValidationError

from board.lane import lane_for
from domain.board import CardState, FaceDoor, FaceDoorName
from domain.lane import Door, Lane
from domain.meaning import OPENING, Meaning, opening_of, say
from tests.board.test_lane import card, facts


def test_a_sentence_for_each_meaning_opens_with_its_words():
    for meaning in Meaning:
        sentence = say(meaning, "the one thing", why="the plain reason", then="what happens next")
        assert sentence == (
            f"{OPENING[meaning]}: the one thing. The plain reason. What happens next."
        )
        assert opening_of(sentence) == meaning


def test_the_parts_are_clauses_and_a_quoted_question_keeps_its_mark():
    assert say(Meaning.QUIET, "this starts by itself once #20 ships") == (
        "Nothing for you: this starts by itself once #20 ships."
    )
    assert say(Meaning.YOURS, "answer its question", why="it asked: “High or medium?”") == (
        "Your move: answer its question. It asked: “High or medium?”"
    )
    assert say(Meaning.LIVE, "a session is on it.", why="  ", then=None) == (
        "Happening now: a session is on it."
    )


def test_a_free_sentence_opens_with_nothing():
    assert opening_of("Start waits on the plan's own word: its Sequencing names #20") is None
    assert opening_of("your move: lowercase is not the opening") is None


def test_a_state_refuses_a_detail_that_opens_with_another_meanings_words():
    with pytest.raises(ValidationError, match="must open with 'Nothing for you'"):
        CardState(
            word="waits on #20",
            meaning=Meaning.QUIET,
            detail=say(Meaning.YOURS, "rule on this"),
            loop=None,
            door=None,
            hint=None,
        )
    with pytest.raises(ValidationError, match="must open with 'Your move'"):
        CardState(
            word="your move",
            meaning=Meaning.YOURS,
            detail="Decide: the open card has every door.",
            loop=None,
            door=None,
            hint=None,
        )


def test_a_face_that_claims_him_always_carries_a_sentence():
    for meaning in (Meaning.YOURS, Meaning.BROKEN):
        with pytest.raises(ValidationError, match="says what in a sentence"):
            CardState(word="doubted", meaning=meaning, detail=None, loop=None, door=None, hint=None)
    quiet = CardState(
        word="planned", meaning=Meaning.QUIET, detail=None, loop=None, door=None, hint=None
    )
    assert quiet.detail is None


def test_a_door_refuses_a_reason_with_no_opening():
    with pytest.raises(ValidationError, match="Door.why must open with one of"):
        Door(offered=False, label="Start", why="This card names no effort gate.")
    with pytest.raises(ValidationError, match="FaceDoor.why must open with one of"):
        FaceDoor(name=FaceDoorName.START, label="Start", why="Start · fable on alpha", primary=True)
    opened = Door(offered=True, label="Start", why=say(Meaning.YOURS, "press it"))
    assert opened.why == "Your move: press it."


def test_a_lane_refuses_a_sentence_with_no_opening_and_allows_none():
    lane = lane_for(card(), facts()).model_dump()
    with pytest.raises(ValidationError, match="Lane.sentence must open with one of"):
        Lane.model_validate({**lane, "sentence": "Working, fable on alpha."})
    assert Lane.model_validate({**lane, "sentence": ""}).sentence == ""
