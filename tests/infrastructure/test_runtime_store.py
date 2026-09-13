"""The runtime's own records in the store: where a session runs, its rescues,
its windows. Three tables with no foreign key to the board's, so clearing a
session's rescue history never clears its slot (plan 02, item 3)."""

from datetime import UTC, datetime

from domain.session import SessionSlot
from domain.slot import Rung
from domain.window import WindowKind

AT = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)


def _slot(
    session_id: str, slot: str, card: str, scope: str, started_on: str | None = None
) -> SessionSlot:
    return SessionSlot(
        session_id=session_id,
        slot=slot,
        card=card,
        started_on=started_on,
        scope=scope,
        recorded_at=AT,
    )


def test_a_session_slot_is_written_once_and_updated_in_place(store):
    store.record_session_slot(_slot("s1", "alpha", "card-1", "needle-card-1.scope"))
    store.record_session_slot(_slot("s1", "beta", "card-1", "needle-card-1.scope"))

    record = store.session_slot("s1")
    assert record is not None and record.slot == "beta"
    assert [r.session_id for r in store.session_slots()] == ["s1"], "the same session is one row"
    assert store.session_slot("unknown") is None


def test_the_card_a_session_was_started_on_is_written_once_and_never_over(store):
    """Card #115: a warm call rewrote the one row that said which card a
    session was started on with the call's own name, so an hour later the
    board could not tell a lane's author from a reader in its directory."""
    store.record_session_slot(_slot("s9", "alpha", "card-1", "u", started_on="card-1"))
    store.record_session_slot(_slot("s9", "alpha", "call-abc", "call-abc.scope", "call-abc"))

    record = store.session_slot("s9")
    assert record is not None
    assert record.card == "call-abc", "what it runs as now moves"
    assert record.started_on == "card-1", "what started it does not"
    assert store.started_on(["s9"]) == {"s9": "card-1"}


def test_a_record_written_before_the_field_existed_names_no_card_and_is_never_guessed_at(store):
    store.record_session_slot(_slot("s10", "alpha", "card-2", "u"))
    assert store.session_slot("s10").started_on is None
    assert store.started_on(["s10"]) == {}, "absent, so the reader falls back to the directory"
    assert store.started_on([]) == {}

    # A later write that does bring one fills the empty field: a session
    # rescoped or moved after this landed says what started it from then on.
    store.record_session_slot(_slot("s10", "alpha", "card-2", "u", started_on="card-2"))
    assert store.started_on(["s10"]) == {"s10": "card-2"}


def test_clearing_rescues_leaves_the_slot_record_standing(store):
    store.record_session_slot(_slot("s2", "beta", "card-2", "needle-card-2.scope"))
    store.record_rescue(
        "s2",
        Rung(slot="alpha", model="fable"),
        Rung(slot="beta", model="fable"),
        "Fable limit",
        AT,
    )
    store.record_rescue(
        "s2",
        Rung(slot="beta", model="fable"),
        Rung(slot="beta", model="opus"),
        "Fable limit again",
        AT,
    )

    assert [(r.from_rung.slot, r.to_rung.model) for r in store.rescues("s2")] == [
        ("alpha", "fable"),
        ("beta", "opus"),
    ]
    assert store.clear_rescues("s2") == 2
    assert store.rescues("s2") == []
    assert store.session_slot("s2").slot == "beta", "the slot outlives the rescue history"


def test_a_rescue_from_the_top_rung_records_no_from(store):
    rescue = store.record_rescue("s3", None, Rung(slot="alpha", model=None), "started fresh", AT)
    assert rescue.from_rung is None and rescue.to_rung.model is None


def test_a_window_is_recorded_open_then_closed(store):
    opened = store.record_window("s4", WindowKind.LANE, "org.omarchy.lane-card-4", "0xabc", AT)
    assert opened.closed_at is None
    assert [w.address for w in store.windows(open_only=True)] == ["0xabc"]

    store.window_closed(opened.id, AT)
    assert store.windows(open_only=True) == []
    assert store.windows("s4")[0].closed_at is not None
    store.window_closed(opened.id, AT)  # idempotent: a second close changes nothing
    assert store.windows("s4")[0].closed_at == AT
