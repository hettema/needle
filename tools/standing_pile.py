"""Read every lane of a project that sits ended with nothing landed, through
the loop's own reader, and print what the board will do with each (plan 68,
ruling 4): the cause of its ending from the evidence that held the process,
what the work stood at from the card's record, and the disposition that
follows — brought back, waiting on an end, or the owner's.

Read-only for real: the store is copied to a temporary directory and the
copy is opened (`Store` migrates whatever it opens, so opening the served
store from a lane would migrate it — card #51's incident); the registries
and journals are read as the loop reads them; no session is started. The
close of card #68 ran it against Hello Revenue before and after the fold, so the close-out names every lane by number, evidence,
disposition and time; the served board applies the same reading on its next
pass and acts on it.

    uv run python tools/standing_pile.py <project slug> [--all]

`--all` prints every lane with a session, not only the ended ones.
"""

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from board.lane import LaneFacts, disposition, entered_executing_at, lane_for  # noqa: E402
from domain.ending import MACHINE_ENDED, Cause, Disposition  # noqa: E402
from domain.lane import LaneState  # noqa: E402
from domain.session import SessionKind  # noqa: E402
from infrastructure import clock  # noqa: E402
from infrastructure.paths import db_path  # noqa: E402
from infrastructure.store import Store  # noqa: E402
from runtime import codex, launch, machine, reasons  # noqa: E402
from runtime.git import worktrees  # noqa: E402
from runtime.service import Runtime  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    slug, everything = argv[0], "--all" in argv
    scratch = Path(tempfile.mkdtemp(prefix="standing-pile-"))
    source = db_path()
    for suffix in ("", "-wal", "-shm"):
        if source.with_name(source.name + suffix).exists():
            shutil.copy2(source.with_name(source.name + suffix), scratch / (source.name + suffix))
    store = Store(scratch / source.name)
    project = next((p for p in store.projects() if p.slug == slug), None)
    if project is None:
        print(f"no project {slug!r} in {db_path()}", file=sys.stderr)
        return 1
    runtime = Runtime(store)
    now = clock.now()
    sessions = runtime.sessions()
    boots = reasons.boots()
    records = store.lanes(slug)
    facts = LaneFacts(
        project_path=project.path,
        sessions=sessions,
        events=store.hook_events(slug),
        discussions=store.discussions(slug),
        records=records,
        windows=store.windows(open_only=True),
        rescues={},
        deaths=store.deaths(slug),
        parks={p.card_number: p for p in store.parks(slug, standing_only=True)},
        worktrees=worktrees(project.path),
        now=now,
    )
    by_record = {r.card_number: r for r in records}
    rows: list[tuple] = []
    for card in store.cards(slug):
        lane = lane_for(card, facts)
        session = lane.session
        if session is None or lane.state == LaneState.NONE:
            continue
        if not everything and (lane.state != LaneState.ENDED or lane.folded):
            continue
        history = store.history(slug, card.number)
        record = by_record.get(card.number)
        since = (
            record.first_seen
            if record is not None
            else lane.hands_on_since or entered_executing_at(history)
        )
        stood, why = disposition(card, lane, history, since)
        if lane.state == LaneState.ENDED and session.pid is None:
            named = runtime.cause_of(
                session,
                units=[
                    launch.lane_unit(lane.name),
                    machine.unit_name(launch.DAEMON_UNIT_PREFIX, session.slot),
                ],
                sighting=store.sighting(session.session_id),
                boots_seen=boots,
                now=now,
            )
            cause, words = named.cause, named.words
        else:
            cause, words = None, lane.sentence
        if stood == Disposition.CLOSED:
            verdict = "finished; nothing to bring back"
        elif stood == Disposition.OWNERS:
            verdict = "the owner's; left where it fell"
        elif session.kind == SessionKind.INTERACTIVE or session.slot == codex.SLOT:
            verdict = "the owner's own terminal or a worker of the other make; not the board's"
        elif cause in MACHINE_ENDED:
            verdict = (
                "a candidate for the board to bring back; its next pass decides through the "
                "gate (room on an account, the floor) and the hour's count"
            )
        elif cause == Cause.UNKNOWN:
            verdict = "unresolved; goes to the owner in the batch"
        elif cause == Cause.STOPPED:
            verdict = "stopped through its account; the owner's"
        else:
            verdict = "left as it stands"
        rows.append(
            (
                card.number,
                card.place.column.value,
                session.short_id,
                session.slot,
                cause.value if cause else "-",
                stood.value,
                verdict,
                words,
                why,
            )
        )
    for number, column, short, slot, cause, stood, verdict, words, why in sorted(rows):
        print(f"#{number} [{column}] {short} on {slot}")
        print(f"    cause: {cause}")
        print(f"    evidence: {words}")
        print(f"    work stood: {stood} — {why}")
        print(f"    disposition: {verdict}")
    print(f"{len(rows)} lanes read at {now.strftime('%Y-%m-%d %H:%MZ')}")
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
