"""Writes `frontend/tests/fixture.json`: the Harbourmaster board exactly as the
API serves it, with every card's detail, at a fixed clock.

The frontend tests need a board in the page's own types. Writing one by hand
drifts from what the backend actually serves and, before this tool, it carried
a real project's card titles into a public repository. So the fixture is
generated: the synthetic project under `tests/fixtures/harbourmaster/` goes
through the real registration, import and sweep, and the result is dumped from
the Pydantic models. A ratchet regenerates and compares, so the snapshot can
never lag the domain.

One arrival is staged: the storm-warning plan is held back from the
founding sweep and swept in afterwards, so the snapshot carries one card born
while the board was watching — the NEW mark and the "arrived today" count the
page has to render.

    uv run python tools/board_fixture.py
"""

import json
import shutil
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from board.assemble import (  # noqa: E402
    document_of,
    routing_for,
    summarize,  # noqa: E402
)
from board.import_01 import read_01  # noqa: E402
from board.lane import (  # noqa: E402
    LaneFacts,  # noqa: E402
    doors_for,
    lane_for,
)
from board.progress import progress_of  # noqa: E402
from board.triage import Sources  # noqa: E402
from domain.audit import AuditEntry, AuditKind  # noqa: E402
from domain.board import MachineState  # noqa: E402
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place  # noqa: E402
from domain.column import Column  # noqa: E402
from domain.corpus import CorpusIndex  # noqa: E402
from domain.document import Document, DocumentKind, Fix, FixMark, SuggestionKind  # noqa: E402
from domain.evidence import Evidence  # noqa: E402
from domain.gate import Gate  # noqa: E402
from domain.hook import HookEvent, HookKind  # noqa: E402
from domain.lane import Collision, CollisionVerdict, Progress, Wait  # noqa: E402
from domain.project import Project  # noqa: E402
from domain.row import Row, RowKind  # noqa: E402
from domain.session import Session, SessionKind, SessionState  # noqa: E402
from domain.signal import Reading, SessionWork, WindowlessSession  # noqa: E402
from domain.slot import Model, Placement  # noqa: E402
from domain.triage import Triage, TriageResult  # noqa: E402
from infrastructure.corpus import scan  # noqa: E402
from infrastructure.live import Live, sweep  # noqa: E402
from infrastructure.store import Store  # noqa: E402

HARBOURMASTER = REPO / "tests" / "fixtures" / "harbourmaster"
FIXTURE = REPO / "frontend" / "tests" / "fixture.json"
ARRIVAL = "docs/plans/2026-09-04-a-storm-warning-reaches-every-skipper.md"
NOW = datetime(2026, 9, 4, 8, 30, tzinfo=UTC)
SHOWN_PATH = "/srv/harbourmaster"
"""The path the snapshot shows for the project: the real one is a temporary
directory and would differ on every run."""

LANE_PATH = f"{SHOWN_PATH}/.claude/worktrees/card-900-a-card-in-every-state"
PLACEMENT = Placement(
    slot="alpha", model=Model.FABLE, config_dir="/x/alpha", why="Fable headroom on alpha"
)


def _card(
    number: int,
    *,
    column: Column,
    archived: bool = False,
    gate: Gate | None = Gate.HIGH,
    watch: str | None = None,
    kind: DocumentKind = DocumentKind.PLAN,
) -> Card:
    rows = [Row(kind=RowKind.SERVES, text="Every berth is billed by the metre.")]
    if watch:
        rows.append(Row(kind=RowKind.WATCH, text=watch))
    return Card(
        number=number,
        project="harbourmaster",
        place=Place(column=column, group=None, position=0),
        title="A card in every state",
        gate=gate,
        tags=[],
        deep="",
        citations=[],
        link=DocumentLink(kind=kind, stem="p", title="A card in every state", archived=archived),
        origin=CardOrigin.IMPORTED,
        born_at=NOW,
        rows=rows,
    )


def _document(*, archived: bool = False, kind: DocumentKind = DocumentKind.PLAN) -> Document:
    folder = "docs/plans" if kind == DocumentKind.PLAN else "docs/slice-suggestions"
    suggestion = kind == DocumentKind.SUGGESTION
    return Document(
        kind=kind,
        stem="p",
        path=f"{folder}{'/done' if archived else ''}/2026-09-04-a-card-in-every-state.md",
        archived=archived,
        title="A card in every state",
        date=date(2026, 9, 4),
        status=None,
        status_word=None,
        gate=None,
        gate_why=None,
        sequencing=None,
        found_by=None,
        card_ref=None,
        suggestion_kind=SuggestionKind.DEFECT if suggestion else None,
        fix=Fix(mark=FixMark.NOW, why=None, trigger=None) if suggestion else None,
        fix_note=None,
        cites=[],
        handouts=[],
        items=[],
        head_fields=[],
        fingerprint="f1x7ur3f1n6erpr",
        intent_heading=None,
        intent="",
        essence="Every berth is billed by the metre.",
        read_at=NOW,
    )


def _session(
    *,
    pid: int | None = 4242,
    state: SessionState = SessionState.WORKING,
    recorded: str = "working",
    detail: str = "",
) -> Session:
    return Session(
        slot="alpha",
        config_dir="/x/alpha",
        short_id="aaaa0001",
        session_id="aaaa0001-0000-4000-8000-000000000000",
        kind=SessionKind.BACKGROUND,
        name="card-900-a-card-in-every-state",
        cwd=LANE_PATH,
        worktree=LANE_PATH,
        state=state,
        recorded=recorded,
        detail=detail,
        pid=pid,
        scope="needle-card-900.scope",
        model=Model.FABLE,
        effort=Gate.HIGH,
        stale=False,
        wall=None,
        intent="",
        created_at=NOW - timedelta(minutes=12),
        updated_at=NOW - timedelta(minutes=1),
        resumed_from=None,
        doing=None,
    )


def _facts(**changes) -> LaneFacts:
    base = dict(
        project_path=SHOWN_PATH,
        sessions=[],
        events=[],
        discussions=[],
        records=[],
        windows=[],
        rescues={},
        deaths={},
        worktrees={LANE_PATH: "card-900-a-card-in-every-state"},
        now=NOW,
    )
    base.update(changes)
    return LaneFacts(**base)


def _summary(
    card: Card,
    *,
    lane=None,
    placed_by_machine: bool = False,
    last=None,
    reading=None,
    planning=None,
    triaging=None,
    triage=None,
    suggestion_live: bool = False,
    collision: Collision | None = None,
    placement: Placement | None = PLACEMENT,
    waits: list[Wait] | None = None,
):
    """One card as the page receives it, through the real derivation."""
    the_lane = lane if lane is not None else lane_for(card, _facts(worktrees={}))
    assert card.link is not None
    index = CorpusIndex(
        documents=[_document(archived=card.link.archived, kind=card.link.kind)], read_at=NOW
    )
    sources = Sources(Path(SHOWN_PATH), lambda number: None)
    routed = routing_for(card, document_of(card, index), triage, sources)
    doors = doors_for(
        card,
        the_lane,
        gate_named=card.gate is not None,
        placement=placement,
        placement_note="every subscription is spent" if placement is None else "",
        collision=collision,
        signal=None,
        signal_due_for_owner=False,
        signal_evidence=None,
        suggestion_live=suggestion_live,
        waits=waits or [],
        routed=routed,
    )
    # A card the machine put in Executing on hands-on evidence, with no lane
    # on this read, is what the board doubts: the evidence is gone.
    placed = (
        AuditEntry(
            id=1,
            at=NOW,
            actor=Actor.MACHINE,
            kind=AuditKind.MOVED,
            card_number=card.number,
            from_place=None,
            to_place=card.place,
            detail="hands on it",
            evidence=Evidence.HANDS_ON,
        )
        if placed_by_machine
        else None
    )
    summary = summarize(
        card,
        index,
        NOW,
        lane,
        doors=doors,
        placement=placed,
        last=last,
        read=True,
        reading=reading,
        planning=planning,
        triaging=triaging,
        triage=triage,
        sources=sources,
        project_path=SHOWN_PATH,
    )
    return summary


def language_cases() -> list[dict[str, object]]:
    """One card per state the rule can name (plan 27, item 6). The page test
    renders each and asserts its word, its meaning, its border and its door
    against this table — and the cards come from the real derivation, so a
    backend that changes a word fails the page's test, not only its own."""
    working = lane_for(
        _card(900, column=Column.EXECUTING),
        _facts(sessions=[_session(detail="Skimming the test suites for the pill's pattern.")]),
    )
    asking = lane_for(
        _card(900, column=Column.EXECUTING),
        _facts(
            sessions=[_session(state=SessionState.DONE, recorded="done")],
            events=[
                HookEvent(
                    id=1,
                    kind=HookKind.SESSION_START,
                    session_id=_session().session_id,
                    cwd=LANE_PATH,
                    at=NOW,
                    source=None,
                    message=None,
                    reason=None,
                    error=None,
                    transcript_path=None,
                    project="harbourmaster",
                    card_number=900,
                ),
                HookEvent(
                    id=2,
                    kind=HookKind.STOP,
                    session_id=_session().session_id,
                    cwd=LANE_PATH,
                    at=NOW,
                    source=None,
                    message="The parser is in.\n\nHigh or medium?",
                    reason=None,
                    error=None,
                    transcript_path=None,
                    project="harbourmaster",
                    card_number=900,
                ),
            ],
        ),
    )
    ended = lane_for(
        _card(900, column=Column.DECISION_MOMENT), _facts(sessions=[_session(pid=None)])
    )
    colliding = working.model_copy(
        update={
            "colliding": Collision(
                verdict=CollisionVerdict.COLLIDES,
                sentence="#241's lane is also editing engine/metering.py.",
                files=["engine/metering.py"],
                cards=[241],
            )
        }
    )
    owner_watch = (
        "the owner reads the board without it being explained — owner dennis by 2026-09-11"
    )
    session_watch = "no session re-grows the old doors — session harbourmaster by 2026-09-11"
    due_watch = "the office check email names a real event — owner dennis by 2026-09-04"
    late_watch = "the nightly check email names a real event — session harbourmaster by 2026-09-01"
    read_at = NOW - timedelta(hours=1)
    delivered = Reading(
        id=1,
        card_number=900,
        at=read_at,
        delivered=True,
        words="the doors stayed",
        actor=Actor.SESSION,
    )
    reading = WindowlessSession(
        id=1,
        project="harbourmaster",
        card_number=900,
        work=SessionWork.READING,
        session_id="bbbb0001-0000-4000-8000-000000000000",
        slot="beta",
        started_at=NOW - timedelta(minutes=2),
        ended_at=None,
    )
    gone = _card(900, column=Column.UP_NEXT)
    gone.link = DocumentLink(kind=DocumentKind.PLAN, stem="nowhere", title="", archived=False)
    # A defect the dial took (plan 11): its planning session writes the plan
    # in the project's checkout, never hands on the tree.
    planning = WindowlessSession(
        id=2,
        project="harbourmaster",
        card_number=900,
        work=SessionWork.PLANNING,
        session_id="cccc0001-0000-4000-8000-000000000000",
        slot="alpha",
        started_at=NOW - timedelta(minutes=3),
        ended_at=None,
    )
    # A defect whose mark an independent reading is verifying, and one that
    # reading put on the owner's pile (plan 59): the two faces the seat adds.
    triaging = WindowlessSession(
        id=3,
        project="harbourmaster",
        card_number=900,
        work=SessionWork.TRIAGE,
        session_id="dddd0001-0000-4000-8000-000000000000",
        slot="beta",
        started_at=NOW - timedelta(minutes=4),
        ended_at=None,
    )
    ruled_yours = Triage(
        id=1,
        project="harbourmaster",
        card_number=900,
        at=NOW - timedelta(minutes=6),
        actor=Actor.SESSION,
        result=TriageResult.HIS,
        words=(
            "the berth plan names neither of the two shapes this could take, and both are "
            "yours to choose between"
        ),
        decision="a1b2c3d4e5f60718",
        parent=None,
        direction=None,
        source_ref=None,
        source_path=None,
        source_fingerprint=None,
        document_fingerprint=_document(kind=DocumentKind.SUGGESTION).fingerprint,
        session_id="dddd0001-0000-4000-8000-000000000000",
    )
    cases: list[tuple[str, object]] = [
        ("free to start", _summary(_card(900, column=Column.UP_NEXT))),
        (
            "shares ground",
            _summary(
                _card(900, column=Column.UP_NEXT),
                collision=Collision(
                    verdict=CollisionVerdict.COLLIDES,
                    sentence="Shares ground: #241's lane is editing engine/metering.py right "
                    "now. The second to fold rebases.",
                    files=["engine/metering.py"],
                    cards=[241],
                ),
            ),
        ),
        (
            "waits",
            _summary(
                _card(900, column=Column.PLANNED),
                waits=[
                    Wait(
                        label="#139",
                        project="harbourmaster",
                        number=139,
                        column=Column.DECISION_MOMENT,
                        shipped=False,
                    )
                ],
            ),
        ),
        ("no gate", _summary(_card(900, column=Column.UP_NEXT, gate=None))),
        ("nowhere to run", _summary(_card(900, column=Column.UP_NEXT), placement=None)),
        ("working", _summary(_card(900, column=Column.EXECUTING), lane=working)),
        ("asking you", _summary(_card(900, column=Column.EXECUTING), lane=asking)),
        ("colliding", _summary(_card(900, column=Column.EXECUTING), lane=colliding)),
        ("lane ended", _summary(_card(900, column=Column.DECISION_MOMENT), lane=ended)),
        ("doubted", _summary(_card(900, column=Column.EXECUTING), placed_by_machine=True)),
        ("document nowhere", _summary(gone)),
        ("your move", _summary(_card(900, column=Column.DECISION_MOMENT))),
        (
            "loop open",
            _summary(_card(900, column=Column.EXECUTED, archived=True, watch=session_watch)),
        ),
        (
            "loop open, owner only",
            _summary(_card(900, column=Column.EXECUTED, archived=True, watch=owner_watch)),
        ),
        (
            "signal for you to read",
            _summary(_card(900, column=Column.EXECUTED, archived=True, watch=due_watch)),
        ),
        (
            "a session is reading it",
            _summary(
                _card(900, column=Column.EXECUTED, archived=True, watch=session_watch),
                reading=reading,
            ),
        ),
        (
            "signal past due",
            _summary(_card(900, column=Column.EXECUTED, archived=True, watch=late_watch)),
        ),
        (
            "loop closed",
            _summary(
                _card(900, column=Column.DONE, archived=True, watch=session_watch), last=delivered
            ),
        ),
        ("not now", _summary(_card(900, column=Column.NOT_NOW))),
        (
            "being planned",
            _summary(
                _card(900, column=Column.BACKLOG, gate=None, kind=DocumentKind.SUGGESTION),
                suggestion_live=True,
                planning=planning,
            ),
        ),
        (
            "mark being read",
            _summary(
                _card(900, column=Column.BACKLOG, gate=None, kind=DocumentKind.SUGGESTION),
                suggestion_live=True,
                triaging=triaging,
            ),
        ),
        (
            "your ruling",
            _summary(
                _card(900, column=Column.BACKLOG, gate=None, kind=DocumentKind.SUGGESTION),
                suggestion_live=True,
                triage=ruled_yours,
            ),
        ),
    ]
    return [{"case": case, "card": card.model_dump(mode="json")} for case, card in cases]


RECORD = """# Review — a storm warning reaches every skipper

**Plan:** docs/plans/done/2026-09-04-a-storm-warning-reaches-every-skipper.md
**Reviewer:** the build session
**Diff range:** 3c91e2a..HEAD
**Findings:** 9 — 8 fixed before this record, 1 filed.

## The passes

1. **The feature against the plan's "done means".** A boat booked twice was
   warned twice; the log line said reached before the message left; two more.
2. **The seams.** Two offices warning at once; the send retried on a timeout
   and reached a skipper twice; two more.
3. **The boundaries.** The warning reaches the office's mailer directly — the fix is landing.

## Dispositions

1. **A boat booked twice was warned twice.** FIXED in 4d1e2f.
2. **The log line said reached before the message left.** FIXED in 4d1e2f.
3. **A skipper with no phone was skipped in silence.** FIXED in 5e2f3a.
4. **The list read yesterday's bookings after midnight.** FIXED in 5e2f3a.
5. **Two offices warned at once.** FIXED in 6f3a4b.
6. **The send retried on a timeout and reached a skipper twice.** FIXED in 6f3a4b.
7. **The rehearsal's five unreached were the wrong five.** FIXED in 7a4b5c.
8. **The Warn button was reachable from the tide table.** FIXED in 7a4b5c.
9. **A berth is let twice when two offices book in the same second.** Outside
   this change — filed as docs/slice-suggestions/2026-09-05-a-berth-is-let-twice.md.
"""
"""A review record as the lane on the storm-warning plan would write it,
pass by pass, in Harbourmaster's words: the fixture for the review counter
(plan 13, item 5). The passes and findings are staged, as the comp says."""

CLEAN_PASS = "4. **The fixed work again.** Re-read the three fix commits. Nothing new. Clean.\n"


def progress_cases() -> dict[str, object]:
    """How far a running card has come, from the real derivation over the
    storm-warning plan (plan 13): the lane's copy with two items met, with
    one deviated, with every item met and the review loop open, and with
    the loop closed by a clean pass. The page test renders each on an
    Executing card and on the open card's items section."""
    plan = (HARBOURMASTER / ARRIVAL).read_text(encoding="utf-8")
    stem = "2026-09-04-a-storm-warning-reaches-every-skipper"
    met = {
        1: "**Met:** the list at office/tonight.py; eleven boats on the fixture, each with "
        "its skipper's phone.",
        2: "**Met:** Warn sends through office/messages.py; test_warn_reaches_every_boat passes.",
        3: "**Met:** a line per skipper in office/log.py, reached or not.",
        4: "**Met:** test_gale_rehearsed finds five unreached.",
    }
    deviated = "**Deviated:** sent from the tide clock, not a Warn button; see the review's pass 1."

    def marked(stances: dict[int, str]) -> str:
        lines = plan.split("\n")
        out: list[str] = []
        for line in lines:
            out.append(line)
            for number, stance in stances.items():
                if line.startswith(f"{number}. **"):
                    out.append(stance)
        return "\n".join(out)

    def progress(stances: dict[int, str], record: str | None) -> Progress:
        found = progress_of(
            marked(stances),
            plan_stem=stem,
            read_reviews=lambda: [(f"docs/reviews/{stem}.md", record)] if record else [],
            now=NOW,
        )
        assert found is not None
        return found

    return {
        "nothing": progress({}, None).model_dump(mode="json"),
        "two_met": progress({1: met[1], 2: met[2]}, None).model_dump(mode="json"),
        "deviated": progress({1: met[1], 2: deviated, 3: met[3]}, None).model_dump(mode="json"),
        "review_open": progress(met, RECORD).model_dump(mode="json"),
        "review_clean": progress(
            met, RECORD.replace("## Dispositions", CLEAN_PASS + "\n## Dispositions")
        ).model_dump(mode="json"),
    }


def snapshot() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "harbourmaster"
        shutil.copytree(HARBOURMASTER, root)
        arrival = root / ARRIVAL
        held_back = arrival.read_text(encoding="utf-8")
        arrival.unlink()

        store = Store(Path(tmp) / "needle.db")
        project = Project(
            slug="harbourmaster", name="Harbourmaster", path=str(root), registered_at=NOW
        )
        store.add_project(project)
        card_file = json.loads((root / "docs/board/needle-board.json").read_text(encoding="utf-8"))
        store.import_01(project.slug, read_01(card_file, scan(root, NOW)), NOW)
        sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)

        arrival.write_text(held_back, encoding="utf-8")
        live = Live(store, now=lambda: NOW)
        live.load()
        # The snapshot is the board as served: the watcher is on. Without a
        # running loop there is no watcher task, so its two facts are set here.
        live.projects[project.slug].watching = True
        live.projects[project.slug].watch_note = None
        # The machine as the loop would have read it: every command found,
        # and the two roles the machine's roles file names today (plan 12).
        live.set_machine(
            MachineState(missing=[], roles=["top", "downgrade", "execution", "search"])
        )

        board = live.board(project.slug)
        board.project = board.project.model_copy(update={"path": SHOWN_PATH})
        numbers = [c.number for col in board.columns for g in col.groups for c in g.cards]
        details = {str(n): live.detail(project.slug, n).model_dump(mode="json") for n in numbers}
        store.close()
        return {
            "board": board.model_dump(mode="json"),
            "details": details,
            "language": language_cases(),
            "progress": progress_cases(),
        }


def render() -> str:
    return json.dumps(snapshot(), indent=2, ensure_ascii=False) + "\n"


def write() -> bool:
    """True when the file changed."""
    content = render()
    if FIXTURE.is_file() and FIXTURE.read_text(encoding="utf-8") == content:
        return False
    FIXTURE.write_text(content, encoding="utf-8")
    return True


if __name__ == "__main__":
    print(f"wrote {FIXTURE}" if write() else f"{FIXTURE} is current")
