"""What the board knows about a lane's deaths, parks and recoveries lives in
the store (plan 68, item 2): a sighting is one row per life refreshed in
place, a death is rewritten while unsettled, a park stands once per card
and a recovery is open once per card — so the note lands once across every
process that reads the board, and one interruption has one replacement."""

from datetime import UTC, datetime, timedelta

import pytest

from domain.ending import Cause, Death, Sighting
from infrastructure.store import StoreRefusal

AT = datetime(2026, 9, 9, 10, 0, tzinfo=UTC)


def _sighting(**changes) -> Sighting:
    base = dict(
        session_id="s1",
        project="proj",
        card_number=7,
        pid=4242,
        scope="needle-card-7-x.scope",
        boot_id="boot-0",
        first_seen=AT,
        last_seen=AT,
    )
    base.update(changes)
    return Sighting(**base)


def test_a_sighting_keeps_its_first_time_and_moves_its_last(store):
    store.record_sighting(_sighting())
    later = AT + timedelta(minutes=5)
    store.record_sighting(
        _sighting(first_seen=later, last_seen=later, scope="claude-daemon-alpha.scope")
    )
    seen = store.sighting("s1")
    assert seen is not None
    assert seen.first_seen == AT and seen.last_seen == later
    assert seen.scope == "claude-daemon-alpha.scope"
    assert seen.released_at is None and seen.scoped_at is None
    store.record_sighting(_sighting(last_seen=later, scoped_at=later))
    assert store.sighting("s1").scoped_at == later, "an act once per life is kept"
    store.record_sighting(_sighting(last_seen=later))
    assert store.sighting("s1").scoped_at == later, "a refresh without the act keeps it"
    # A different process under the same id is a new life: its first
    # sighting and its once-per-life acts start again.
    reborn = later + timedelta(hours=1)
    store.record_sighting(_sighting(pid=5151, first_seen=reborn, last_seen=reborn))
    seen = store.sighting("s1")
    assert seen.pid == 5151 and seen.first_seen == reborn and seen.scoped_at is None
    assert set(store.sightings("proj")) == {"s1"} and store.sightings("other") == {}


def test_a_death_is_rewritten_while_unsettled(store):
    first = Death(
        session_id="s1",
        project="proj",
        card_number=7,
        cause=Cause.UNKNOWN,
        words="the process disappeared; the cause is not established",
        evidence="",
        last_alive_at=AT,
        named_at=AT,
        settled=False,
    )
    store.record_death(first)
    assert store.deaths("proj")["s1"].cause == Cause.UNKNOWN
    named = first.model_copy(
        update={
            "cause": Cause.LANE_KILLED,
            "words": "the machine took back its memory at 10:01",
            "evidence": "systemd-oomd killed 12 process(es) in this unit.",
            "named_at": AT + timedelta(minutes=1),
            "settled": True,
        }
    )
    store.record_death(named)
    death = store.deaths("proj")["s1"]
    assert death.cause == Cause.LANE_KILLED and death.settled
    assert death.evidence.startswith("systemd-oomd killed")
    assert len(store.deaths("proj")) == 1, "one row per session, rewritten"
    store.forget_death("s1")
    assert store.deaths("proj") == {}


def test_one_park_stands_per_card_and_lifts_once(store):
    park = store.open_park(
        "proj",
        7,
        session_id="s1",
        cause=Cause.WALL,
        words="waits on the allowance",
        waits_on="clock",
        until=AT + timedelta(hours=2),
        held_since=None,
        at=AT,
    )
    with pytest.raises(StoreRefusal, match="already stands"):
        store.open_park(
            "proj",
            7,
            session_id="s1",
            cause=Cause.WALL,
            words="again",
            waits_on="clock",
            until=None,
            held_since=None,
            at=AT,
        )
    assert [p.id for p in store.parks("proj", standing_only=True)] == [park.id]
    held = store.hold_park(park.id, AT + timedelta(seconds=30))
    assert held.held_since == AT + timedelta(seconds=30)
    lifted = store.lift_park(park.id, AT + timedelta(hours=2), "the allowance is back")
    assert lifted.lifted_at is not None and lifted.lifted_words == "the allowance is back"
    assert store.parks("proj", standing_only=True) == []
    again = store.open_park(
        "proj",
        7,
        session_id="s2",
        cause=Cause.LANE_KILLED,
        words="waits on the machine's memory",
        waits_on="clock",
        until=None,
        held_since=None,
        at=AT + timedelta(hours=3),
    )
    assert again.id != park.id and len(store.parks("proj")) == 2


def test_one_recovery_is_open_per_card_and_a_closed_one_keeps_its_verdict(store):
    opened = store.open_recovery(
        "proj", 7, session_id="s1", cause=Cause.LANE_KILLED, words="oom at 10:00", at=AT
    )
    with pytest.raises(StoreRefusal, match="already open"):
        store.open_recovery(
            "proj", 7, session_id="s1", cause=Cause.LANE_KILLED, words="again", at=AT
        )
    other = store.open_recovery(
        "proj", 8, session_id="s9", cause=Cause.BOOT, words="the laptop went down", at=AT
    )
    assert other.id != opened.id, "another card's recovery is not held by this one"
    closed = store.close_recovery(
        opened.id, verdict="alive", replacement="s2", at=AT + timedelta(seconds=9), note=None
    )
    assert closed.verdict == "alive" and closed.replacement == "s2"
    with pytest.raises(StoreRefusal, match="inside the horizon"):
        store.open_recovery(
            "proj",
            7,
            session_id="s2",
            cause=Cause.LANE_KILLED,
            words="oom at 10:20",
            at=AT + timedelta(minutes=20),
            horizon_seconds=3600,
        )
    second = store.open_recovery(
        "proj",
        7,
        session_id="s2",
        cause=Cause.LANE_KILLED,
        words="oom at 11:20",
        at=AT + timedelta(minutes=80),
        horizon_seconds=3600,
    )
    assert [r.id for r in store.recoveries("proj", 7)] == [opened.id, second.id]
    assert [r.card_number for r in store.recoveries("proj")] == [7, 8, 7]
