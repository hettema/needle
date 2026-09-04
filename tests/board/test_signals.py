"""The WATCH row's grammar: a signal the board can read, or a written decline
(plan 03, item 5)."""

from datetime import UTC, date, datetime

import pytest

from board.signals import (
    GRAMMAR,
    SignalUnreadable,
    is_due,
    parse_watch,
    read_or_decline,
    where_after,
)
from domain.column import Column
from domain.signal import SignalKind

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def test_a_url_signal_with_an_expectation_a_due_date_and_a_cadence():
    signal = parse_watch(
        'prod answers the health check — url https://api.example.test/health expect "ok" '
        "by 2026-09-12 every 6h"
    )
    assert signal.what == "prod answers the health check"
    assert signal.kind == SignalKind.URL and signal.target == "https://api.example.test/health"
    assert signal.expect == "ok" and signal.due == date(2026, 9, 12) and signal.every_hours == 6


def test_a_file_signal_defaults_to_a_daily_cadence():
    signal = parse_watch(
        "the plan is archived — file docs/plans/done/2026-09-04-x.md by 2026-09-30"
    )
    assert signal.kind == SignalKind.FILE
    assert signal.target == "docs/plans/done/2026-09-04-x.md"
    assert signal.every_hours == 24


def test_a_command_signal_with_a_count():
    signal = parse_watch(
        "three clients billed — command uv run python scripts/count.py expect >= 3 by 2026-09-30 "
        "every 2d"
    )
    assert signal.kind == SignalKind.COMMAND
    assert signal.target == "uv run python scripts/count.py"
    assert signal.expect == ">= 3" and signal.every_hours == 48


def test_an_owner_signal_is_the_question_itself():
    signal = parse_watch("the invoice reached his inbox — owner by 2026-09-08")
    assert signal.kind == SignalKind.OWNER and signal.target == "the invoice reached his inbox"


def test_what_is_missing_is_named_with_the_grammar():
    with pytest.raises(SignalUnreadable, match="names no reader") as no_reader:
        parse_watch("what reality still has to confirm")
    assert GRAMMAR in str(no_reader.value)
    with pytest.raises(SignalUnreadable, match="no due date"):
        parse_watch("prod is up — url https://x.test")
    with pytest.raises(SignalUnreadable, match="no target"):
        parse_watch("prod is up — url by 2026-09-12")
    signal, why = read_or_decline(None)
    assert signal is None and why == "no WATCH row names a signal"


def test_the_cadence_and_the_verdict_after_a_reading():
    signal = parse_watch("x — url https://x.test by 2026-09-09 every 12h")
    assert is_due(signal, last_read=None, now=NOW)
    assert not is_due(signal, last_read=NOW.replace(hour=1), now=NOW)
    assert is_due(signal, last_read=NOW.replace(day=9, hour=23), now=NOW)
    assert where_after(signal, True, NOW) == (Column.DONE, "the signal says delivered: x")
    column, reason = where_after(signal, False, NOW)
    assert column == Column.DECISION_MOMENT and "due date 2026-09-09 has passed" in reason
    column, reason = where_after(signal, None, NOW)
    assert column == Column.DECISION_MOMENT and "could not be read" in reason
    not_yet = parse_watch("x — url https://x.test by 2026-09-11")
    assert where_after(not_yet, False, NOW) == (None, "not delivered yet, and not yet due")
