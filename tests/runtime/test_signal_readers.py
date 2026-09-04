"""Reading a signal through the machine door, and a death's reason from the
journal (plan 03, items 5 and 7), on the floor."""

from datetime import UTC, datetime

from board.signals import parse_watch
from domain.session import Session, SessionKind, SessionState
from runtime import reasons, signals
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


def session(recorded: str, detail: str = "") -> Session:
    return Session(
        slot="alpha",
        config_dir="/x",
        short_id="aaaa0001",
        session_id="aaaa0001-0000-4000-8000-000000000000",
        kind=SessionKind.BACKGROUND,
        name="card-7-x",
        cwd="/srv/p",
        worktree=None,
        state=SessionState.ENDED,
        recorded=recorded,
        detail=detail,
        pid=None,
        scope=None,
        model=None,
        effort=None,
        stale=False,
        wall=None,
        intent="",
        created_at=NOW,
        updated_at=NOW,
    )


def test_a_deaths_reason_comes_from_the_journal_else_the_registry(machine_floor: Floor):
    machine_floor.update(
        journal={
            "needle-card-7-x.scope": [
                "Started needle-card-7-x.scope.",
                "claude[4242]: Killed process 4242 (claude) total-vm:9GB",
                "needle-card-7-x.scope: Consumed 2min CPU time.",
            ]
        }
    )
    assert (
        reasons.why_ended(session("stopped"), "needle-card-7-x.scope")
        == "the journal for needle-card-7-x.scope says: claude[4242]: Killed process 4242 "
        "(claude) total-vm:9GB"
    )
    assert reasons.why_ended(session("stopped"), "quiet.scope") == "the session was stopped"
    assert (
        reasons.why_ended(session("done"), None)
        == "the session finished its turn and was not resumed"
    )
    assert reasons.why_ended(session("blocked", "asking"), None) == "the registry says: asking"
    assert reasons.why_ended(session("working"), None) is None
