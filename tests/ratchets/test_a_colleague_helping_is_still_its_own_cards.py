"""Two boundaries, held: whose colleague a card has, and what asking one
for help is allowed to do to it.

**A card's colleague is chosen from the board's own record, never from the
directory alone.** Where a colleague sits is the weakest thing the board
knows about it, and for a long time it was the only thing the board asked.
On 2026-09-09 a Codex review pass run with `--cd` set to a lane's worktree
ended a minute after it started, and the card turned red with "session
died" while the lane's own session was building in the same directory the
whole time (card #108). On 2026-09-12 card #123's close had landed, its
plan was archived, its work was on `origin/main` and its session had been
stopped — and card #80's lane called that session back to be its
independent reader, whereupon the board dragged the finished card into
Executing with nobody working on it, and the owner, looking at his board,
asked whether the card was finished at all (card #135). The same thing
happened again to card #82 on 2026-09-13, while this was being built.
Both readings are the same mistake, and this refuses it: while a record
names a colleague — the card it was started on, or an open call it is
answering — the directory does not get to say.

**Asking a colleague for help never resumes or stops it.** The note exists
because the two colleagues that most need reaching are the two that must
never be interrupted: one in a terminal the owner is typing into, and one
in the middle of its turn. A note that resumed either would be the
disturbance the whole card is named after (card #137, 2026-09-13). So the
note path launches nothing and stops nothing, and this fails the moment it
does.

Ratcheted at the altitude of the intent: neither test names the field, the
function or the order in which today's readers work. A better method may
ship; a card claimed by whoever happens to be sitting in its worktree, or
a note that interrupts, may not.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from board.lane import LaneFacts, lane_for, should_enter_executing
from domain.call import Call
from domain.card import Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.document import DocumentKind
from domain.gate import Gate
from domain.lane import LaneRecord, LaneState
from domain.launch import LaunchVerdict, WindowlessStart
from domain.session import Session, SessionKind, SessionState
from runtime import launch
from runtime.service import Runtime
from tests.floor import Floor

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
PROJECT = "/srv/harbour"
NAME = "card-7-the-thing"
LANE = f"{PROJECT}/.claude/worktrees/{NAME}"
VISITOR = "8d7fb4a3-0000-4000-8000-000000000000"


def a_card() -> Card:
    return Card(
        number=7,
        project="proj",
        place=Place(column=Column.EXECUTED, group=None, position=0),
        title="The thing",
        gate=Gate.HIGH,
        tags=[],
        deep="",
        citations=["docs/plans/p.md"],
        link=DocumentLink(kind=DocumentKind.PLAN, stem="p", title="The thing", archived=True),
        origin=CardOrigin.IMPORTED,
        born_at=NOW - timedelta(days=3),
        rows=[],
    )


def a_session(session_id: str = VISITOR) -> Session:
    return Session(
        slot="alpha",
        config_dir="/x",
        short_id=session_id.split("-")[0],
        session_id=session_id,
        kind=SessionKind.BACKGROUND,
        name=NAME,
        cwd=LANE,
        worktree=LANE,
        state=SessionState.WORKING,
        recorded="working",
        detail="",
        pid=4242,
        scope=None,
        model="opus",
        effort=Gate.HIGH,
        stale=False,
        wall=None,
        intent="",
        created_at=NOW - timedelta(minutes=20),
        updated_at=NOW,
        resumed_from=None,
        doing=None,
    )


def a_record() -> LaneRecord:
    return LaneRecord(
        project="proj",
        card_number=7,
        name=NAME,
        path=LANE,
        branch=NAME,
        birth="aaa",
        tip="bbb",
        first_seen=NOW - timedelta(days=2),
        last_seen=NOW,
        gone_at=None,
        folded_at=NOW - timedelta(hours=6),
        trunk_synced_at=None,
        main_synced_at=None,
    )


def facts(**changes) -> LaneFacts:
    base = dict(
        project_path=PROJECT,
        sessions=[a_session()],
        events=[],
        discussions=[],
        records=[a_record()],
        windows=[],
        rescues={},
        deaths={},
        worktrees={LANE: NAME},
        now=NOW,
    )
    base.update(changes)
    return LaneFacts(**base)


def an_open_call(session_id: str = VISITOR) -> Call:
    return Call(
        id=1,
        session_id=session_id,
        slot="alpha",
        name=NAME,
        note="/home/dennis/.cache/needle/notes/n.md",
        answer="/home/dennis/.cache/needle/notes/from-x-re-n.md",
        brief="A colleague calls you with a question.",
        caller=f"{PROJECT}/.claude/worktrees/card-9-elsewhere",
        called_at=NOW - timedelta(minutes=20),
        moved=None,
        ended_at=None,
        words=None,
    )


@pytest.mark.parametrize(
    ("what", "records"),
    [
        (
            "a colleague answering another card's call, sitting in this card's worktree",
            {"calls": [an_open_call()]},
        ),
        (
            "a colleague the record says was started on another card",
            {"started_on": {VISITOR: "card-9-elsewhere"}},
        ),
    ],
)
def test_a_card_is_never_claimed_by_whoever_is_sitting_in_its_copy_of_the_code(
    what: str, records: dict
):
    told_by_the_record = lane_for(a_card(), facts(**records))
    told_by_the_directory = lane_for(a_card(), facts())

    assert told_by_the_directory.state == LaneState.WORKING, (
        "the fallback still stands: a session no record names is the lane's, by its directory"
    )
    assert told_by_the_directory.session is not None

    assert told_by_the_record.session is None, (
        f"{what} is not this card's colleague, and the board has a record that says so"
    )
    assert told_by_the_record.state != LaneState.WORKING
    assert should_enter_executing(a_card(), told_by_the_record, []) is None, (
        "and it never opens the card (cards #135 and #82, 2026-09-12 and 13)"
    )
    assert told_by_the_record.died is None, (
        "nor is it this card's death when it ends (card #108, 2026-09-09)"
    )


def test_handing_a_colleague_a_note_starts_nothing_and_stops_nothing(
    machine_floor: Floor, store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(launch, "OBSERVATION_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)
    monkeypatch.setattr(launch, "VERIFY_SECONDS", 4.0)
    runtime = Runtime(store)
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    machine_floor.script_launches({"then": "work"})
    started = runtime.start_windowless(
        WindowlessStart(repo=str(repo), card="colleague-x", brief="be there", effort=Gate.HIGH)
    )
    assert started.verdict == LaunchVerdict.ALIVE and started.session is not None

    terminal_id = "eeee0001-0000-4000-8000-000000000000"
    machine_floor.write_process("beta", terminal_id, os.getpid(), kind="cli", cwd=str(repo))
    before = len(machine_floor.state()["launch_log"])

    for ref in (started.session.short_id, "eeee0001"):
        who = runtime.colleague(ref)
        assert isinstance(who, Session)
        handed = runtime.call(
            who, brief="Read the note", name=who.name, answer=str(tmp_path / "a.md")
        )
        assert handed.verdict == LaunchVerdict.HANDED, (
            f"{ref} cannot be resumed, so the note is handed to it: {handed.reason}"
        )

    assert len(machine_floor.state()["launch_log"]) == before, (
        "the note path launched a process; it must launch none (card #137, 2026-09-13)"
    )
    assert machine_floor.state()["stops"] == [], (
        "the note path stopped a colleague; it must stop none — a note waits for the "
        "colleague's next word, it never takes its turn away"
    )
