"""A window into any session, proved by the compositor, closable without ending it.

Plan 02, item 4.
"""

import os
from pathlib import Path

import pytest

from domain.gate import Gate
from domain.launch import Start
from domain.window import WindowKind
from runtime import launch, windows
from runtime.service import Runtime
from tests.floor import Floor


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    monkeypatch.setattr(windows, "WINDOW_VERIFY_SECONDS", 1.5)


@pytest.fixture
def runtime(store) -> Runtime:
    return Runtime(store)


@pytest.fixture
def live(runtime: Runtime, tmp_path: Path, machine_floor: Floor) -> str:
    """A session started on the floor; its short id."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    result = runtime.start(
        Start(repo=str(repo), card="card-9-a-lane", brief="go", effort=Gate.HIGH, from_slot=None)
    )
    assert result.session is not None, result.reason
    return result.session.short_id


def test_a_window_into_a_live_session_is_an_attach_proved_by_one_more_client(
    machine_floor: Floor, runtime: Runtime, live: str, store
):
    opened = runtime.window(live, None)

    assert not opened.fresh and opened.window.kind == WindowKind.LANE
    assert opened.window.app_id == "org.omarchy.lane-card-9-a-lane"
    assert opened.window.address == "0xfake0001"
    spawned = machine_floor.state()["spawned"][0]
    assert spawned["app_id"] == "org.omarchy.lane-card-9-a-lane"
    command = spawned["command"][-1]
    assert (
        f"exec claude attach {live}" in command
        and f"CLAUDE_CONFIG_DIR={machine_floor.config_dir('alpha')}" in command
    )
    assert [w.address for w in store.windows(open_only=True)] == ["0xfake0001"]


def test_a_second_window_for_a_session_that_has_one_is_refused_by_name(
    runtime: Runtime, live: str, machine_floor: Floor
):
    runtime.window(live, None)

    with pytest.raises(
        windows.WindowRefused, match="already has a window: org.omarchy.lane-card-9-a-lane"
    ):
        runtime.window(live, None)
    assert len(machine_floor.state()["spawned"]) == 1


def test_a_window_the_owner_closed_is_recorded_and_the_runtime_never_reopens_it(
    machine_floor: Floor, runtime: Runtime, live: str, store
):
    opened = runtime.window(live, None)
    machine_floor.update(clients=[])  # the owner closed it

    runtime.sessions()

    closed = store.windows(opened.window.session_id)
    assert len(closed) == 1 and closed[0].closed_at is not None
    assert len(machine_floor.state()["spawned"]) == 1, "a read opens nothing"
    again = runtime.window(live, None)
    assert again.window.id != opened.window.id, "an explicit call after the close opens a new one"
    assert len(machine_floor.state()["spawned"]) == 2
    assert [w.id for w in store.windows(open_only=True)] == [again.window.id]


def test_no_window_within_the_deadline_fails_by_name(
    machine_floor: Floor, runtime: Runtime, live: str, store
):
    machine_floor.update(windows_open=False)

    with pytest.raises(
        windows.WindowRefused, match="no window appeared under org.omarchy.lane-card-9-a-lane"
    ):
        runtime.window(live, None)
    assert store.windows(open_only=True) == []


def test_a_session_live_nowhere_gets_a_fresh_session_from_its_transcript(
    machine_floor: Floor, runtime: Runtime, store
):
    session_id = machine_floor.write_job(
        "alpha",
        "dead0001",
        state="done",
        worktree="/repo/.claude/worktrees/card-3",
        effort="high",
        name="card-3-x",
    )
    machine_floor.answer_best("beta", None, "Fable headroom on beta")

    opened = runtime.window("dead0001", None)

    assert opened.fresh and opened.window.kind == WindowKind.LOOK
    assert opened.window.app_id == "org.omarchy.board-look-card-3-x"
    assert opened.banner is not None and opened.banner.startswith(
        "Fresh session from the transcript of dead0001"
    )
    assert "fable on the beta subscription" in opened.banner
    command = machine_floor.state()["spawned"][0]["command"][-1]
    assert command.startswith("cd /repo/.claude/worktrees/card-3 && printf")
    assert f"--resume {session_id} --fork-session" in command and "--effort high" in command
    assert f"CLAUDE_CONFIG_DIR={machine_floor.config_dir('beta')}" in command


def test_a_transcript_above_the_limit_is_named_not_loaded(
    machine_floor: Floor, runtime: Runtime, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(launch, "RESUME_SIZE_LIMIT", 1024)
    session_id = machine_floor.write_job(
        "alpha", "dead0002", state="done", cwd="/repo", intent="the brief"
    )
    machine_floor.write_transcript("/repo", session_id, 4096)

    opened = runtime.window("dead0002", None)

    assert opened.banner is not None and "named, not loaded" in opened.banner
    command = machine_floor.state()["spawned"][0]["command"][-1]
    assert "--resume" not in command and "tail -c 200000" in command and "the brief" in command


def test_a_stale_copy_and_an_interactive_session_get_no_window(
    machine_floor: Floor, runtime: Runtime
):
    session_id = machine_floor.write_job("alpha", "cafe0001", state="done")
    machine_floor.write_job("beta", "cafe0001", state="working", session_id=session_id)
    machine_floor.write_process("beta", session_id, os.getpid())
    machine_floor.write_process(
        "alpha", "cafe0002-0000-4000-8000-000000000000", os.getpid(), kind="interactive"
    )

    live_copy = runtime.window("cafe0001", None)
    assert live_copy.window.app_id.startswith("org.omarchy.lane-")
    with pytest.raises(windows.WindowRefused, match="terminal of its own"):
        runtime.window("cafe0002", None)


def test_the_app_id_follows_the_owners_contract():
    assert (
        windows.app_id_for(WindowKind.WATCH, "card 12: a title")
        == "org.omarchy.board-watch-card-12-a-title"
    )
    assert windows.app_id_for(WindowKind.LANE, "") == "org.omarchy.lane-unnamed"
