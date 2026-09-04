"""The lane's dispatches and the machine's roles, read from the floor (plan 12)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from runtime import machine, roles, transcripts
from tests.floor import Floor

LANE = "/srv/p/.claude/worktrees/card-9-the-seams"


def _record(kind: str, blocks: list[dict], *, sidechain: bool = False, stamp: str = "") -> str:
    return json.dumps(
        {
            "type": kind,
            "sessionId": "abc",
            "isSidechain": sidechain,
            "timestamp": stamp or "2026-09-05T10:00:00.000Z",
            "message": {"role": kind, "content": blocks},
        }
    )


def _agent(role: str | None) -> dict:
    given = {"prompt": "find it", "description": "a search"}
    if role is not None:
        given["subagent_type"] = role
    return {"type": "tool_use", "id": "t1", "name": "Agent", "input": given}


def write_transcript(cwd: str, name: str, lines: list[str]) -> Path:
    path = machine.transcript_dir(cwd) / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_every_agent_tool_use_on_a_main_thread_is_a_dispatch_and_nothing_else_is(
    machine_floor: Floor,
):
    assert transcripts.dispatches(LANE) is None
    write_transcript(
        LANE,
        "first",
        [
            _record("user", [{"type": "text", "text": "go"}]),
            _record("assistant", [_agent("search")], stamp="2026-09-05T10:00:01.000Z"),
            _record("assistant", [{"type": "tool_use", "id": "t2", "name": "Read", "input": {}}]),
            _record("assistant", [_agent("execution")], sidechain=True),
            "not json at all",
        ],
    )
    write_transcript(
        LANE,
        "resumed",
        [_record("assistant", [_agent(None), _agent("Search")], stamp="2026-09-05T11:00:00Z")],
    )
    # A subagent's own transcript sits in a subdirectory and is never a main thread.
    inner = machine.transcript_dir(LANE) / "first" / "subagents"
    inner.mkdir(parents=True)
    (inner / "agent-1.jsonl").write_text(_record("assistant", [_agent("search")]) + "\n")
    found = transcripts.dispatches(LANE)
    assert found is not None
    assert [(d.role, d.session_id) for d in found] == [
        ("search", "abc"),
        ("claude", "abc"),
        ("search", "abc"),
    ]
    assert found[0].at == datetime(2026, 9, 5, 10, 0, 1, tzinfo=UTC)


def test_a_transcript_the_board_cannot_read_hides_nothing_else(machine_floor: Floor):
    write_transcript(LANE, "readable", [_record("assistant", [_agent("search")])])
    locked = write_transcript(LANE, "locked", [_record("assistant", [_agent("execution")])])
    locked.chmod(0)
    try:
        found = transcripts.dispatches(LANE)
    finally:
        locked.chmod(0o600)
    assert found is not None and [d.role for d in found] == ["search"]


def test_the_roles_are_the_roles_files_keys_without_its_notes(machine_floor: Floor):
    assert roles.roles() == ["top", "downgrade", "execution", "search"]
    machine.roles_path().write_text("not json", encoding="utf-8")
    assert roles.roles() is None
    machine.roles_path().unlink()
    assert roles.roles() is None
