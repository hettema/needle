"""The runtime's own records in the store: where a session runs, its rescues,
its windows. Three tables with no foreign key to the board's, so clearing a
session's rescue history never clears its slot (plan 02, item 3)."""

from datetime import UTC, datetime

from domain.session import SessionSlot
from domain.slot import Model, Rung
from domain.window import WindowKind

AT = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)


def _slot(session_id: str, slot: str, card: str, scope: str) -> SessionSlot:
    return SessionSlot(session_id=session_id, slot=slot, card=card, scope=scope, recorded_at=AT)


def test_a_session_slot_is_written_once_and_updated_in_place(store):
    store.record_session_slot(_slot("s1", "alpha", "card-1", "needle-card-1.scope"))
    store.record_session_slot(_slot("s1", "beta", "card-1", "needle-card-1.scope"))

    record = store.session_slot("s1")
    assert record is not None and record.slot == "beta"
    assert [r.session_id for r in store.session_slots()] == ["s1"], "the same session is one row"
    assert store.session_slot("unknown") is None


def test_clearing_rescues_leaves_the_slot_record_standing(store):
    store.record_session_slot(_slot("s2", "beta", "card-2", "needle-card-2.scope"))
    store.record_rescue(
        "s2",
        Rung(slot="alpha", model=Model.FABLE),
        Rung(slot="beta", model=Model.FABLE),
        "Fable limit",
        AT,
    )
    store.record_rescue(
        "s2",
        Rung(slot="beta", model=Model.FABLE),
        Rung(slot="beta", model=Model.OPUS),
        "Fable limit again",
        AT,
    )

    assert [(r.from_rung.slot, r.to_rung.model) for r in store.rescues("s2")] == [
        ("alpha", Model.FABLE),
        ("beta", Model.OPUS),
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
