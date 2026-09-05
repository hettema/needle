"""`needle`'s verbs for sessions and the owner's terminal: the card as a
brief, the rows a session writes back, the close, the fold, a start that
goes through the running board, the hook's registration, and the loops run
by hand.

needle card SLUG N                       # the brief a lane opens with
needle row SLUG N KIND "text"            # one row on the card
needle close SLUG N --delivered … --watch … [--review PATH] [--column COL]
needle reading SLUG N delivered|not-delivered|cannot-tell "…" [--watch "…"]
needle fold [--main] [--worktree PATH]   # fast-forward push to origin/develop, trunk synced
needle start-card SLUG N                # Start, through the running board
needle hook install REPO                 # the session hook in REPO/.claude/settings.json, and REPO/hooks as git's
needle sync [SLUG]                       # level each main checkout with origin/develop now
needle signals [SLUG]                    # read every due signal now
needle lanes SLUG                        # every card's lane, as the board reads it
needle verdicts SLUG [--write]           # the verdicts the board's own facts settle (plan 05)
needle kinds SLUG                        # every live suggestion's kind and Fix: mark, as read
needle watercooler SLUG [N "text"]       # read the watercooler, or say one line as #N's lane
needle dial [on|off] [--lanes N]         # the owner's standing ruling on defects (plan 11)
needle fixes SLUG|all                    # every fix lane the dial ran, and the rail against dial-on

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

from api.dial import Dial
from api.doors import REPO_ROOT, DoorFailed, DoorRefused, Doors
from api.loops import Loops, project_of_cwd
from board.brief import watercooler_text
from board.dial import Filer
from board.lane import has_row
from board.verdicts import CLOSED, VerdictUnreadable, machine_verdict, parse_verdict, render_verdict
from domain.audit import AuditKind
from domain.card import Actor
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.lane import HANDS_ON, LaneState
from domain.row import Row, RowKind
from domain.signal import Finding
from domain.triage import Direction, TriageResult
from domain.verdict import EvidenceClass
from infrastructure import clock
from infrastructure.live import Live
from infrastructure.paths import db_path
from infrastructure.store import Store, StoreRefusal
from runtime.git import GitFailed, arm_hooks_path
from runtime.service import Runtime

DEFAULT_URL = "http://127.0.0.1:8480"
HOOK_EVENTS = ("SessionStart", "Stop", "SessionEnd", "StopFailure", "PostToolUse")
HOOK_SCRIPT = REPO_ROOT / "hooks" / "needle_hook.py"
WORD_HOOK_TIMEOUT_SECONDS = 5
"""Claude Code's own ceiling on the PostToolUse hook, in the settings entry:
the script's half second is the real one, this is the belt for an
interpreter that cannot start, where Claude Code's default is 600 s."""


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
    print(doors.brief_for_lane(detail, args.slug) if args.lane else _brief(live, args))
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
        f"#{args.number} said it; every running lane on {args.slug} hears it inside its own "
        "session within a minute, and every lane reads it at start and before its fold"
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


def reading(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """A reading session's finding on the card, and the move it implies
    (plan 09): the one verb a reading session ends its turn with."""
    result = doors.reading(
        args.slug,
        args.number,
        finding=Finding(args.finding),
        words=args.words,
        watch=args.watch,
    )
    print(result.said)
    return 0


def triage(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """A triage reading's result on the card, and the routing it implies
    (plan 59, item 3): the one verb a reading of a defect's mark ends its
    turn with."""
    result = doors.triage(
        args.slug,
        args.number,
        result=TriageResult(args.result),
        words=args.words,
        source=args.source,
        direction=Direction(args.direction) if args.direction else None,
    )
    print(result.said)
    return 0


def decisions(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """Every decision a colleague took on the rail, in order, with its
    source, its direction and its fate (plan 59, item 6): the sample the
    loop's cold audit reads, printed rather than tracked."""
    slug = None if args.slug == "all" else args.slug
    if slug is not None and slug not in live.projects:
        print(f'no project "{slug}" is on the board', file=sys.stderr)
        return 1
    loops.reconcile_now()
    rows = Dial(live, runtime, loops, doors).decisions(slug)
    if args.first:
        rows = rows[: args.first]
    if not rows:
        print("no decision has been taken on the rail yet")
        return 0
    for line in rows:
        came = f" (out of {line.parent})" if line.parent else ""
        print(
            f"{line.at.date().isoformat()}  {line.project} #{line.card_number:<4} "
            f"{line.result.value:<12} {line.decision}{came}"
        )
        print(f"      {line.title}")
        print(f"      says: {line.words}")
        print(f"      source: {line.source}")
        print(f"      direction: {line.direction.value if line.direction else 'none recorded'}")
        print(f"      routes as: {line.routing.value}; fate: {line.fate.words}")
    taken = [line for line in rows if line.result == TriageResult.NOW]
    counts: dict[str, int] = {}
    for line in taken:
        if line.direction is not None:
            counts[line.direction.value] = counts.get(line.direction.value, 0) + 1
    print(
        f"{len(rows)} decisions, {len(taken)} taken off your rail as `now`"
        + (
            "; directions: " + ", ".join(f"{n} {d}" for d, n in sorted(counts.items()))
            if counts
            else "; no direction recorded"
        )
    )
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
    body = json.dumps({}).encode("utf-8")
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
        hook: dict = {"type": "command", "command": command}
        if event == "PostToolUse":
            hook["timeout"] = WORD_HOOK_TIMEOUT_SECONDS
        entries.append({"matcher": "", "hooks": [hook]})
        added.append(event)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    if added:
        print(f"registered Needle's hook in {settings} for {', '.join(added)}")
    else:
        print(f"Needle's hook is already registered in {settings}")
    return _arm_git_hooks(repo)


def _arm_git_hooks(repo: Path) -> int:
    """Point git at the repository's own `hooks/` when it keeps git hooks there.

    By ABSOLUTE path, and this is the whole reason the arming is a command
    rather than a line in a README: the setting lives in the shared config, and
    a relative value resolves against each worktree's own root — so every lane
    under `.claude/worktrees/` would silently run no hook, which is exactly
    where the commits are made.

    Silent for a repository with no `hooks/commit-msg`: only the project that
    owns the one text has a doctrine to guard, and pointing git at a directory
    with no hooks in it would disable the default hooks directory for
    nothing."""
    hooks = repo / "hooks"
    if not (hooks / "commit-msg").is_file():
        return 0
    try:
        was = arm_hooks_path(repo, hooks)
    except GitFailed as error:
        print(f"the commit hook was not armed: {error}", file=sys.stderr)
        return 1
    if was == str(hooks):
        print(f"git already runs {repo.name}'s hooks from {hooks}")
    else:
        print(f"armed {repo.name}'s git hooks: core.hooksPath = {hooks}" + (f" (was {was})" if was else ""))
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
            print(
                f"#{number}: {said}, by the {reading.actor.value} — {reading.words} "
                f"({reading.at.isoformat()})"
            )
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


def kinds(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """Every live suggestion's kind as the board reads it (plan 06, item 2):
    from its `Kind:` line, or guessed from its text where there is none —
    the table of guesses the owner checks, printed rather than tracked,
    since a project's titles stay in that project's repository. And its
    `Fix:` mark (plan 11, item 2), with why it is unmarked when it is."""
    project = live.projects.get(args.slug)
    if project is None:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    rows = [d for d in project.index.live() if d.kind == DocumentKind.SUGGESTION]
    lined = sum(1 for d in rows if any(f.key.lower() == "kind" for f in d.head_fields))
    guessed = [d for d in rows if not any(f.key.lower() == "kind" for f in d.head_fields)]
    defects = sum(1 for d in guessed if d.suggestion_kind == SuggestionKind.DEFECT)
    marked = sum(1 for d in rows if d.fix is not None)
    print(
        f"{len(rows)} live suggestions; {lined} with a Kind line; {len(guessed)} read from "
        f"their text, {defects} of them as defects; {marked} with a Fix: mark, "
        f"{len(rows) - marked} unmarked"
    )
    for document in rows:
        line = next((f.value for f in document.head_fields if f.key.lower() == "kind"), None)
        kind = document.suggestion_kind.value if document.suggestion_kind else "-"
        why = (
            f"Kind: {line}"
            if line
            else ("its title or Found-by" if kind == "defect" else "no sign of a defect")
        )
        if document.fix is not None:
            mark = document.fix.mark.value + (
                f" {document.fix.trigger}" if document.fix.trigger else ""
            )
        else:
            mark = f"unmarked ({document.fix_note})"
        print(f"{kind:<7} {document.path}  {document.title}  ({why}; Fix: {mark})")
    return 0


def dial(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    """The owner's dial from his terminal (plan 11, item 3): read it, or
    turn it. The running board hears the store change within a second."""
    control = Dial(live, runtime, loops, doors)
    loops.reconcile_now()
    if args.setting is None and args.lanes is None:
        state = control.state()
    else:
        current = live.store.dial()
        on = current.on if args.setting is None else args.setting == "on"
        lanes = current.lanes if args.lanes is None else args.lanes
        state = control.turn(on=on, lanes=lanes)
    setting = state.dial
    print(
        f"auto-fix {'on' if setting.on else 'off'}, {setting.lanes} fix lane"
        f"{'' if setting.lanes == 1 else 's'} at most; {state.running} live now"
        + (f", {state.held} held" if state.held else "")
        + "; the machine is "
        f"{'quiet' if state.quiet else 'not quiet (a lane has hands on a project)'}"
        + (f"; {state.full}" if state.full else "")
        + (f"; changed {setting.changed_at.isoformat()}" if setting.changed_at else "")
        + (f"; first turned on {setting.first_on_at.isoformat()}" if setting.first_on_at else "")
    )
    return 0


def fixes(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """The loop counted (plan 11, item 6), for one project or all."""
    slug = None if args.slug == "all" else args.slug
    if slug is not None and slug not in live.projects:
        print(f'no project "{slug}" is on the board', file=sys.stderr)
        return 1
    loops.reconcile_now()
    report = Dial(live, runtime, loops, doors).fixes(slug)
    setting = report.dial
    print(
        f"dial: {'on' if setting.on else 'off'}, {setting.lanes} at most"
        + (f", first on {setting.first_on_at.isoformat()}" if setting.first_on_at else ", never on")
    )
    if not report.lanes:
        print("no fix lane yet")
    for lane in report.lanes:
        facts = [
            lane.stage.value,
            "folded" if lane.folded else "not folded",
            "review record" if lane.reviewed else "no review record",
            "stopped to ask" if lane.stopped_to_ask else "did not ask",
            "defect filed against it"
            if lane.defect_filed_against
            else "no defect filed against it",
            "fold reverted" if lane.fold_reverted else "fold stands",
            f"class: {lane.class_closer}" if lane.class_closer else "no Class: line",
        ]
        print(f"{lane.project} #{lane.card_number:<4} {lane.title}")
        print("      " + "; ".join(facts))
    closed = [lane for lane in report.lanes if lane.stage.value in ("folded", "ended", "asked")]
    green = sum(1 for done in closed if done.folded and done.reviewed)
    asked = sum(1 for done in closed if done.stopped_to_ask)
    undone = sum(1 for done in closed if done.defect_filed_against or done.fold_reverted)
    closers = sum(1 for done in closed if done.class_closer)
    print(
        f"{len(report.lanes)} fix lanes, {len(closed)} closed: {green} folded with a review "
        f"record, {asked} stopped to ask, {undone} undone (a defect filed against it, or the "
        f"fold reverted), {closers} carried a class-closer"
    )
    taken = [d for d in report.decisions if d.result == TriageResult.NOW]
    print(
        f"{len(report.decisions)} readings of a mark, {len(taken)} of them taking the decision "
        "off your rail; `needle decisions` follows each to its fate"
    )
    for waiting in report.waiting:
        print(f"rail  {waiting.project} #{waiting.card_number:<4} {waiting.title} — {waiting.why}")
    at_on = {r.project: r for r in report.rail_at_first_on}
    for rail in report.rail_now:
        before = at_on.get(rail.project)
        split = ", ".join(
            f"{filer.value} {rail.counts.get(filer, 0)}"
            + (f" (was {before.counts.get(filer, 0)})" if before else "")
            for filer in Filer
            if rail.counts.get(filer, 0) or (before and before.counts.get(filer, 0))
        )
        print(
            f"rail {rail.project}: {rail.total}"
            + (f" (was {before.total} at dial-on)" if before else " (the dial has never been on)")
            + (f" — {split}" if split else "")
        )
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

    p_reading = sub.add_parser(
        "reading", help="a reading session's finding on its card, with the evidence"
    )
    p_reading.add_argument("slug")
    p_reading.add_argument("number", type=int)
    p_reading.add_argument("finding", choices=[f.value for f in Finding])
    p_reading.add_argument("words", help="what was read, where, and what it said")
    p_reading.add_argument(
        "--watch", help="a replacement WATCH row when the measure could not be read"
    )
    p_reading.set_defaults(run=_with_board(reading))

    p_triage = sub.add_parser(
        "triage", help="a triage reading's result on a defect's mark, with the source it read"
    )
    p_triage.add_argument("slug")
    p_triage.add_argument("number", type=int)
    p_triage.add_argument("result", choices=[r.value for r in TriageResult])
    p_triage.add_argument("words", help="what the source said, in the words the result needs")
    p_triage.add_argument("--source", help="the path or #N the result rests on")
    p_triage.add_argument(
        "--direction",
        choices=[d.value for d in Direction],
        help="which way it moves the product; required with now",
    )
    p_triage.set_defaults(run=_with_board(triage))

    p_decisions = sub.add_parser(
        "decisions", help="every decision a colleague took on the rail, with source and fate"
    )
    p_decisions.add_argument("slug", help="a project's slug, or all")
    p_decisions.add_argument("--first", type=int, help="only the first N, for the cold audit")
    p_decisions.set_defaults(run=_with_board(decisions))

    p_fold = sub.add_parser(
        "fold", help="fast-forward push this lane to origin/develop; level the trunk"
    )
    p_fold.add_argument("--main", action="store_true", help="promote main from the same commit")
    p_fold.add_argument("--worktree", help="the lane's worktree; the current directory if omitted")
    p_fold.set_defaults(run=_with_board(fold))

    p_start = sub.add_parser("start-card", help="Start a card through the running board")
    p_start.add_argument("slug")
    p_start.add_argument("number", type=int)
    p_start.add_argument("--url", default=DEFAULT_URL)
    p_start.set_defaults(run=start_card)

    p_hook = sub.add_parser("hook", help="the session hook")
    hook_sub = p_hook.add_subparsers(dest="hook_command", required=True)
    p_install = hook_sub.add_parser(
        "install",
        help="register the session hook in a project's .claude/settings.json for every event "
        "it serves, and point git at the project's own hooks/ when it keeps git hooks there; "
        "idempotent, so run it again when an event is added",
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

    p_dial = sub.add_parser(
        "dial", help="the dial: read it, or turn auto-fix on or off and set the number of fix lanes"
    )
    p_dial.add_argument("setting", nargs="?", choices=["on", "off"])
    p_dial.add_argument("--lanes", type=int, help="how many fix lanes may run at once")
    p_dial.set_defaults(run=_with_board(dial))

    p_fixes = sub.add_parser(
        "fixes", help="every fix lane the dial ran, and the rail now against dial-on"
    )
    p_fixes.add_argument("slug", help="a project's slug, or all")
    p_fixes.set_defaults(run=_with_board(fixes))
