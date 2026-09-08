"""What the board says about who will drive a card, and what it never
guesses (card #63, item 3).

The board said `fable` for any row that recorded no model, which was a guess
for a terminal of the owner's and a false claim for a session of another
make. Every face builds those words in one place now, so there is one thing
to hold: a rung with no model says the slot alone, and a rung of another
make says which make it is.
"""

from datetime import date

from domain.session import Session, SessionKind, SessionState
from domain.slot import Make, Placement, Tier, rung_words
from board.lane import driver, where_of, why_this_driver

from tests.board.test_lane import card, doors


def a_placement(**changes) -> Placement:
    base = dict(
        slot="alpha", make=Make.CLAUDE, model="fable", config_dir="/x", why="Fable headroom on alpha"
    )
    base.update(changes)
    return Placement(**base)


def a_session(**changes) -> Session:
    base = dict(
        slot="codex",
        config_dir="/codex",
        short_id="01a08000",
        session_id="01a08000-0000-7000-8000-0000000000aa",
        kind=SessionKind.BACKGROUND,
        name="codex-01a08000",
        cwd="/srv/harbour",
        worktree=None,
        state=SessionState.WORKING,
        recorded="exec",
        detail="",
        pid=4242,
        scope=None,
        model=None,
        effort=None,
        stale=False,
        wall=None,
        intent="",
        created_at=None,
        updated_at=None,
        resumed_from=None,
        doing=None,
    )
    base.update(changes)
    return Session(**base)


def test_a_rung_with_no_model_says_the_slot_alone_and_never_a_model_it_was_not_told():
    assert rung_words("fable", "eduard") == "fable on eduard"
    assert rung_words(None, "codex") == "codex"
    assert "fable" not in rung_words(None, "eduard")


def test_a_row_with_no_model_recorded_reads_as_its_slot_and_not_as_fable():
    assert where_of(a_session()) == "codex"
    assert where_of(a_session(model="gpt-6-astra")) == "gpt-6-astra on codex"
    assert where_of(a_session(slot="eduard", model=None)) == "eduard"


def test_the_start_door_names_the_make_only_when_it_is_not_the_one_every_lane_was():
    """Naming the make on every rung would put "claude" on a board that has
    said `fable on eduard` since its first day; naming it when it is news is
    what the owner reads."""
    assert driver(a_placement()) == "fable on alpha"
    assert "claude" not in driver(a_placement())
    codex = a_placement(slot="codex", make=Make.CODEX, model="gpt-6-astra")
    assert driver(codex) == "gpt-6-astra on codex (codex)"


def test_the_start_doors_reason_carries_the_owners_dated_tier_ruling():
    ruled = Tier(rank=1, ruled_on=date(2026, 9, 5), why="the tier is quality, not allowance")
    said = why_this_driver(a_placement(tier=ruled))

    assert "Fable headroom on alpha" in said
    assert "2026-09-05" in said and "tier 1" in said
    assert "the tier is quality, not allowance" in said


def test_a_rung_the_rule_gave_no_tier_for_says_the_rules_reason_and_invents_none():
    said = why_this_driver(a_placement())

    assert said == "Fable headroom on alpha"
    assert "tier" not in said


def test_the_start_door_a_codex_rung_offers_names_the_make_and_the_ruling():
    ruled = Tier(rank=1, ruled_on=date(2026, 9, 5), why="the tier is quality")
    codex = a_placement(slot="codex", make=Make.CODEX, model="gpt-6-astra", tier=ruled)

    opened = doors(card(), _no_lane(), placement=codex)

    assert opened.start.offered
    assert "gpt-6-astra on codex (codex)" in opened.start.label
    assert "2026-09-05" in opened.start.why and "tier 1" in opened.start.why


def _no_lane():
    """A card nobody has touched: no session, and no copy of the code on
    disk, which is what leaves Start open."""
    from board.lane import lane_for

    from tests.board.test_lane import facts

    return lane_for(card(), facts(worktrees={}))
