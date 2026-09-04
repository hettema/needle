"""`needle`'s verbs for sessions and the owner's terminal: the card as a
brief, the rows a session writes back, the close, the fold, a start that
goes through the running board, the hook's registration, and the loops run
by hand.

needle card SLUG N                       # the brief a lane opens with
needle row SLUG N KIND "text"            # one row on the card
needle close SLUG N --delivered … --watch … [--review PATH] [--column COL]
needle fold [--main] [--worktree PATH]   # fast-forward push to origin/develop, trunk synced
needle start-card SLUG N [--anyway]      # Start, through the running board
needle hook install REPO                 # register the session hook in REPO/.claude/settings.json
needle sync [SLUG]                       # level each main checkout with origin/develop now
needle signals [SLUG]                    # read every due signal now
needle lanes SLUG                        # every card's lane, as the board reads it
needle verdicts SLUG [--write]           # the verdicts the board's own facts settle (plan 05)
needle kinds SLUG                        # every live suggestion's kind as the board reads it (plan 06)
needle watercooler SLUG [N "text"]       # read the watercooler, or say one line as #N's lane

Rows are written to the store directly — the one writer — and the running
board hears the store change; a start goes through the server so the board
watches the launch exactly as the button's.
"""

import argparse
import contextlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from api.doors import REPO_ROOT, DoorFailed, DoorRefused, Doors
from api.loops import Loops, project_of_cwd
from board.brief import watercooler_text
from board.lane import has_row
from board.verdicts import CLOSED, VerdictUnreadable, machine_verdict, parse_verdict, render_verdict
from domain.audit import AuditKind
from domain.card import Actor
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.lane import HANDS_ON, LaneState
from domain.row import Row, RowKind
from domain.verdict import EvidenceClass
from infrastructure import clock
from infrastructure.live import Live
from infrastructure.paths import db_path
from infrastructure.store import Store, StoreRefusal
from runtime.service import Runtime

DEFAULT_URL = "http://127.0.0.1:8480"
HOOK_EVENTS = ("SessionStart", "Stop", "SessionEnd", "StopFailure")
HOOK_SCRIPT = REPO_ROOT / "hooks" / "needle_hook.py"


def _board() -> tuple[Store, Live, Runtime, Loops, Doors]:
    store = Store(db_path())
    live = Live(store)
    live.load()
    runtime = Runtime(store)
    loops = Loops(live, runtime)
    return store, live, runtime, loops, Doors(live, runtime, loops)


def _with_board(verb: Callable[..., int]) -> Callable[[argparse.Namespace], int]:
    def run(args: argparse.Namespace) -> int:
        store, live, runtime, loops, doors = _board()
        try:
            return verb(args, live, runtime, loops, doors)
        except (StoreRefusal, DoorRefused, DoorFailed) as error:
            print(str(error), file=sys.stderr)
            return 1
        finally:
            store.close()

    return run


def hook_command() -> str:
    return f"python3 {HOOK_SCRIPT}"


# ── the verbs ──────────────────────────────────────────────────────────


def card(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    if args.lane:
        # The riders name the other live lanes, which only a read of the machine knows.
        loops.reconcile_now()
    detail = live.detail(args.slug, args.number)
    print(
        doors.brief_for_lane(detail, args.slug, overrode=None) if args.lane else _brief(live, args)
    )
    return 0


def watercooler(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """Read the project's watercooler, or say one line on it as a card's lane."""
    if args.number is None:
        print(watercooler_text(live.store.watercooler(args.slug)))
        return 0
    if args.text is None or not args.text.strip():
        print('a watercooler line says something: needle watercooler SLUG N "…"', file=sys.stderr)
        return 1
    live.say(args.slug, args.number, Actor.SESSION, args.text)
    print(
        f"#{args.number} said it; every lane on {args.slug} reads it at start and before its fold"
    )
    return 0


def _brief(live: Live, args: argparse.Namespace) -> str:
    from board.brief import render

    return render(live.detail(args.slug, args.number), live.projects[args.slug].project)


def row(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    kind = RowKind(args.kind.upper())
    text = args.text.strip()
    if not text:
        print("an empty row says nothing", file=sys.stderr)
        return 1
    if kind == RowKind.VERDICT:
        try:
            parse_verdict(text)
        except VerdictUnreadable as why:
            print(f"not written: {why}", file=sys.stderr)
            return 1
    live.add_row(args.slug, args.number, Row(kind=kind, text=text), Actor.SESSION)
    print(f"#{args.number}: {kind.value} written")
    return 0


def close(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    result = doors.close(
        args.slug,
        args.number,
        delivered=args.delivered,
        watch=args.watch,
        review=args.review,
        column=Column(args.column) if args.column else None,
        actor=Actor.SESSION,
    )
    print(result.said)
    return 0


def fold(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    worktree = str(Path(args.worktree or ".").resolve())
    project = project_of_cwd(worktree, live.projects)
    if project is None:
        print(f"{worktree} is in no project on the board", file=sys.stderr)
        return 1
    from board.lane import card_of_cwd

    number = card_of_cwd(worktree, project.project.path)
    slug = project.project.slug
    # A lane re-reads the watercooler before it folds, and is told which live
    # lane's edits its fold lands over (plan 07, item 2): the machine is read
    # first so the other lanes' footprints are today's.
    loops.reconcile_now()
    print("The watercooler, before the fold:")
    print(watercooler_text(live.store.watercooler(slug)))
    over = _folds_over(live, slug, number, runtime.edits(worktree)) if number is not None else []
    for other, files in over:
        print(f"this fold lands over #{other}'s edits in {', '.join(files)}")
    folded = runtime.fold(worktree, promote_main=args.main)
    if not folded.pushed:
        print(f"not folded: {folded.words}", file=sys.stderr)
        return 1
    print(f"folded: {folded.words}")
    now = clock.now()
    if number is not None and folded.tip:
        record = live.store.lane(slug, number)
        if record is not None:
            live.store.record_lane(
                record.model_copy(update={"tip": folded.tip, "folded_at": record.folded_at or now})
            )
        live.note(slug, number, AuditKind.FOLDED, Actor.SESSION, f"Folded: {folded.words}")
        for other, files in over:
            shown = ", ".join(files)
            live.note(
                slug,
                number,
                AuditKind.FOLDED,
                Actor.MACHINE,
                f"Folded over #{other}'s edits in {shown}",
            )
            live.note(
                slug,
                other,
                AuditKind.FOLDED,
                Actor.MACHINE,
                f"#{number} folded over this lane's edits in {shown}; re-verify them at the fold",
            )
            live.say(
                slug, None, Actor.MACHINE, f"#{number} folded over #{other}'s edits in {shown}"
            )
    else:
        print("(this worktree is not a card's lane, so no card carries the fold)")
    state = loops.level_project(project)
    if state.level:
        print(f"trunk synced: {project.project.path} is level with origin/develop")
    else:
        print(f"trunk not synced: {state.note}", file=sys.stderr)
    if args.main:
        if folded.main_pushed:
            print("main promoted: origin/main is the same commit")
            if number is not None:
                record = live.store.lane(slug, number)
                if record is not None and record.main_synced_at is None:
                    live.store.record_lane(record.model_copy(update={"main_synced_at": now}))
                live.note(
                    slug,
                    number,
                    AuditKind.SYNCED,
                    Actor.SESSION,
                    "Main synced: promoted at the fold",
                )
        else:
            print("main not promoted: see above", file=sys.stderr)
            return 1
    return 0


def _folds_over(live: Live, slug: str, number: int, mine: set[str]) -> list[tuple[int, list[str]]]:
    """The other live lanes whose edits this fold lands over, with the files."""
    project = live.projects.get(slug)
    if project is None or project.snapshot is None:
        return []
    found: list[tuple[int, list[str]]] = []
    for other, lane in sorted(project.snapshot.lanes.items()):
        if other == number or lane.state not in HANDS_ON:
            continue
        overlap = sorted(mine & set(lane.edits))
        if overlap:
            found.append((other, overlap))
    return found


def start_card(args: argparse.Namespace) -> int:
    """Start through the running board, so the launch is watched like the button's."""
    url = f"{args.url.rstrip('/')}/api/projects/{args.slug}/cards/{args.number}/start"
    body = json.dumps({"anyway": bool(args.anyway)}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            answer = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        with contextlib.suppress(json.JSONDecodeError, AttributeError):
            detail = json.loads(detail).get("detail", detail)
        print(f"not started ({error.code}): {detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as error:
        print(f"the board at {args.url} could not be reached: {error}", file=sys.stderr)
        return 1
    print(answer.get("said", answer))
    return 0


def hook_install(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    settings = repo / ".claude" / "settings.json"
    blob: dict = {}
    if settings.is_file():
        try:
            blob = json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"{settings} is not JSON: {error}", file=sys.stderr)
            return 1
    hooks = blob.setdefault("hooks", {})
    command = hook_command()
    added = []
    for event in HOOK_EVENTS:
        entries = hooks.setdefault(event, [])
        present = any(
            h.get("command") == command
            for entry in entries
            for h in entry.get("hooks", [])
            if isinstance(h, dict)
        )
        if present:
            continue
        entries.append({"matcher": "", "hooks": [{"type": "command", "command": command}]})
        added.append(event)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    if added:
        print(f"registered Needle's hook in {settings} for {', '.join(added)}")
    else:
        print(f"Needle's hook is already registered in {settings}")
    return 0


def sync(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    code = 0
    for project in live.projects.values():
        if args.slug and project.project.slug != args.slug:
            continue
        state = loops.level_project(project)
        if state.level:
            print(f"{project.project.slug}: level with origin/develop")
        else:
            code = 1
            print(
                f"{project.project.slug}: {state.note or f'{state.behind} behind'}", file=sys.stderr
            )
    return code


def signals(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    loops.read_signals_now()
    for project in live.projects.values():
        if args.slug and project.project.slug != args.slug:
            continue
        for number, reading in sorted(live.store.last_readings(project.project.slug).items()):
            said = {True: "delivered", False: "not delivered", None: "unreadable"}[
                reading.delivered
            ]
            print(f"#{number}: {said} — {reading.words} ({reading.at.isoformat()})")
    return 0


def lanes(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    loops.reconcile_now()
    project = live.projects.get(args.slug)
    if project is None or project.snapshot is None:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    for number, lane in sorted(project.snapshot.lanes.items()):
        if lane.state.value == "none":
            continue
        print(f"#{number}  {lane.state.value:<8} {lane.name}  {lane.sentence}")
    return 0


def verdicts(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """The verdicts the board's own facts settle, for every open card that
    carries none yet; `--write` puts them on the cards as the machine's
    rows. The classes the corpus decides are left to a session."""
    loops.reconcile_now()
    project = live.projects.get(args.slug)
    if project is None:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    slug = project.project.slug
    with_lane = {r.card_number for r in live.store.lanes(slug)}
    counts: dict[EvidenceClass, int] = {}
    undecided = 0
    for card in sorted(live.store.cards(slug), key=lambda c: c.number):
        if (
            card.place.column in CLOSED
            or card.folded_into is not None
            or has_row(card, RowKind.VERDICT)
        ):
            continue
        detail = live.detail(slug, card.number)
        ever = (
            card.number in with_lane
            or (detail.lane is not None and detail.lane.state != LaneState.NONE)
            or any(h.kind == AuditKind.STARTED for h in detail.history)
        )
        verdict = machine_verdict(
            card,
            detail.summary.standing,
            detail.document,
            detail.signal,
            detail.readings[0] if detail.readings else None,
            ever_had_a_lane=ever,
            now=clock.now(),
        )
        if verdict is None:
            undecided += 1
            print(f"#{card.number:<4} {card.place.column.value:<16} (the corpus decides)")
            continue
        counts[verdict.evidence_class] = counts.get(verdict.evidence_class, 0) + 1
        text = render_verdict(verdict)
        print(f"#{card.number:<4} {card.place.column.value:<16} {text}")
        if args.write:
            live.add_row(slug, card.number, Row(kind=RowKind.VERDICT, text=text), Actor.MACHINE)
    said = ", ".join(f"{k.value}: {n}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    verb = "written" if args.write else "proposed"
    print(f"{sum(counts.values())} {verb} ({said or 'none'}); {undecided} for the corpus to decide")
    return 0


def kinds(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    """Every live suggestion's kind as the board reads it (plan 06, item 2):
    from its `Kind:` line, or guessed from its text where there is none —
    the table of guesses the owner checks, printed rather than tracked,
    since a project's titles stay in that project's repository."""
    project = live.projects.get(args.slug)
    if project is None:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    rows = [d for d in project.index.live() if d.kind == DocumentKind.SUGGESTION]
    lined = sum(1 for d in rows if any(f.key.lower() == "kind" for f in d.head_fields))
    guessed = [d for d in rows if not any(f.key.lower() == "kind" for f in d.head_fields)]
    defects = sum(1 for d in guessed if d.suggestion_kind == SuggestionKind.DEFECT)
    print(
        f"{len(rows)} live suggestions; {lined} with a Kind line; {len(guessed)} read from "
        f"their text, {defects} of them as defects"
    )
    for document in rows:
        line = next((f.value for f in document.head_fields if f.key.lower() == "kind"), None)
        kind = document.suggestion_kind.value if document.suggestion_kind else "-"
        why = f"Kind: {line}" if line else ("its title or Found-by" if kind == "defect" else "no sign of a defect")
        print(f"{kind:<7} {document.path}  {document.title}  ({why})")
    return 0


def register(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p_card = sub.add_parser("card", help="the card as text: the brief a lane opens with")
    p_card.add_argument("slug")
    p_card.add_argument("number", type=int)
    p_card.add_argument("--lane", action="store_true", help="with the riders a launched lane gets")
    p_card.set_defaults(run=_with_board(card))

    p_row = sub.add_parser("row", help="write one row on a card")
    p_row.add_argument("slug")
    p_row.add_argument("number", type=int)
    p_row.add_argument("kind", choices=[k.value for k in RowKind])
    p_row.add_argument("text")
    p_row.set_defaults(run=_with_board(row))

    p_close = sub.add_parser(
        "close", help="a session's close: DELIVERED, WATCH, REVIEW and the move"
    )
    p_close.add_argument("slug")
    p_close.add_argument("number", type=int)
    p_close.add_argument("--delivered", required=True, help="what the owner now has")
    p_close.add_argument(
        "--watch", required=True, help="the signal: <what> — kind target by YYYY-MM-DD"
    )
    p_close.add_argument("--review", help="the review record's path under docs/reviews/")
    p_close.add_argument("--column", choices=[c.value for c in Column], help="Executed unless said")
    p_close.set_defaults(run=_with_board(close))

    p_fold = sub.add_parser(
        "fold", help="fast-forward push this lane to origin/develop; level the trunk"
    )
    p_fold.add_argument("--main", action="store_true", help="promote main from the same commit")
    p_fold.add_argument("--worktree", help="the lane's worktree; the current directory if omitted")
    p_fold.set_defaults(run=_with_board(fold))

    p_start = sub.add_parser("start-card", help="Start a card through the running board")
    p_start.add_argument("slug")
    p_start.add_argument("number", type=int)
    p_start.add_argument("--anyway", action="store_true", help="override a named lane collision")
    p_start.add_argument("--url", default=DEFAULT_URL)
    p_start.set_defaults(run=start_card)

    p_hook = sub.add_parser("hook", help="the session hook")
    hook_sub = p_hook.add_subparsers(dest="hook_command", required=True)
    p_install = hook_sub.add_parser(
        "install", help="register the hook in a project's .claude/settings.json"
    )
    p_install.add_argument("repo")
    p_install.set_defaults(run=hook_install)

    p_sync = sub.add_parser("sync", help="level each project's main checkout with origin/develop")
    p_sync.add_argument("slug", nargs="?")
    p_sync.set_defaults(run=_with_board(sync))

    p_signals = sub.add_parser("signals", help="read every due signal now")
    p_signals.add_argument("slug", nargs="?")
    p_signals.set_defaults(run=_with_board(signals))

    p_lanes = sub.add_parser("lanes", help="every card's lane, as the board reads it")
    p_lanes.add_argument("slug")
    p_lanes.set_defaults(run=_with_board(lanes))

    p_verdicts = sub.add_parser(
        "verdicts", help="the verdicts the board's own facts settle, for cards carrying none"
    )
    p_verdicts.add_argument("slug")
    p_verdicts.add_argument("--write", action="store_true", help="write them as VERDICT rows")
    p_verdicts.set_defaults(run=_with_board(verdicts))

    p_kinds = sub.add_parser(
        "kinds", help="every live suggestion's kind as the board reads it, and why"
    )
    p_kinds.add_argument("slug")
    p_kinds.set_defaults(run=_with_board(kinds))

    p_water = sub.add_parser(
        "watercooler", help="the project's watercooler: read it, or say one line as a card's lane"
    )
    p_water.add_argument("slug")
    p_water.add_argument("number", type=int, nargs="?", help="the card whose lane is speaking")
    p_water.add_argument("text", nargs="?", help="the line")
    p_water.set_defaults(run=_with_board(watercooler))
