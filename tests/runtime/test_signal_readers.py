"""Reading a signal through the machine door, and a death's reason from the
journal (plan 03, items 5 and 7), on the floor."""

from datetime import UTC, datetime

from board.signals import parse_watch
from runtime import signals
from tests.floor import Floor

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def test_a_url_signal_is_read_through_curl(machine_floor: Floor):
    machine_floor.update(
        urls={
            "https://api.test/health": {"code": 200, "body": '{"status":"ok"}'},
            "https://api.test/down": {"code": 503, "body": "later"},
        }
    )
    ok = parse_watch('prod is up — url https://api.test/health expect "ok" by 2026-09-30')
    assert signals.read(ok, "/srv/p") == (
        True,
        'https://api.test/health answered 200, expecting \'ok\': {"status":"ok"}',
    )
    down = parse_watch("prod is up — url https://api.test/down by 2026-09-30")
    delivered, words = signals.read(down, "/srv/p")
    assert delivered is False and words.startswith("https://api.test/down answered 503")
    unreachable = parse_watch("prod is up — url https://nowhere.test by 2026-09-30")
    delivered, words = signals.read(unreachable, "/srv/p")
    assert delivered is None and "could not be fetched" in words


def test_a_file_and_a_command_signal_are_read_in_the_project(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "done.md").write_text("x")
    there = parse_watch("archived — file docs/done.md by 2026-09-30")
    assert signals.read(there, str(tmp_path))[0] is True
    missing = parse_watch("archived — file docs/nope.md by 2026-09-30")
    assert signals.read(missing, str(tmp_path))[0] is False
    count = parse_watch("three billed — command printf '2 clients' expect >= 3 by 2026-09-30")
    delivered, words = signals.read(count, str(tmp_path))
    assert (
        delivered is False and words == "`printf '2 clients'` exited 0, expecting >= 3: 2 clients"
    )
    enough = parse_watch("three billed — command printf '4 clients' expect >= 3 by 2026-09-30")
    assert signals.read(enough, str(tmp_path))[0] is True
    failing = parse_watch("green — command exit 3 by 2026-09-30")
    delivered, words = signals.read(failing, str(tmp_path))
    assert delivered is False and words.startswith("`exit 3` exited 3")
