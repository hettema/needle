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
needle hook install REPO                 # the hook in REPO/.claude/settings.json, Codex's skills link, git's hooks
needle sync [SLUG]                       # level each main checkout with origin/develop now
needle signals [SLUG]                    # read every due signal now
needle lanes SLUG                        # every card's lane, as the board reads it
needle verdicts SLUG [--write]           # the verdicts the board's own facts settle (plan 05)
needle kinds SLUG                        # every live suggestion's kind and Fix: mark, as read
needle watercooler SLUG [N "text"]       # read the watercooler, or say one line as #N's lane
needle dial [on|off] [--lanes N]         # the owner's standing ruling on defects (plan 11)
needle fixes SLUG|all                    # every fix lane the dial ran, and the rail against dial-on
needle team SLUG [--json]                # which team earns its place, per kind of work (card #58)

Rows are written to the store directly — the one writer — and the running
board hears the store change; a start goes through the server so the board
watches the launch exactly as the button's. On a machine that is not the
board's (`needle board NAME`, card #83 item 3) every verb here runs on the
board's machine over ssh instead — `api/cli.py::main` hands it over before
the store is opened — so a lane there writes the one board and never a
copy; `hook install` and `start-card` stay here, one editing this
machine's file, the other already talking to the board by its address.
"""

import argparse
import contextlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from api.dial import Dial
from api.doors import REPO_ROOT, SKILLS, DoorFailed, DoorRefused, Doors
from api.loops import Loops, project_of_cwd
from board.brief import watercooler_text
from board.dial import Filer
from board.lane import has_row
from board.team import team_words
from board.verdicts import CLOSED, VerdictUnreadable, machine_verdict, parse_verdict, render_verdict
from domain.audit import AuditKind
from domain.call import HowKnown
from domain.card import Actor
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.focus import FocusState, FocusStrip, FocusVerdict, Leverage, Likelihood, RecheckOutcome
from domain.lane import HANDS_ON, LaneState
from domain.row import Row, RowKind
from domain.signal import Finding
from domain.team import Challenge, Tally
from domain.triage import Direction, TriageResult
from domain.verdict import EvidenceClass
from infrastructure import clock
from infrastructure.live import Live
from infrastructure.paths import db_path
from infrastructure.store import Store, StoreRefusal
from runtime.git import GitFailed, arm_hooks_path, corpus_renames
from runtime.service import Runtime

DEFAULT_URL = "http://127.0.0.1:8480"
HOOK_EVENTS = (
    "SessionStart",
    "Stop",
    "SessionEnd",
    "StopFailure",
    "PostToolUse",
    "UserPromptSubmit",
)
HOOK_SCRIPT = REPO_ROOT / "hooks" / "needle_hook.py"
READ_EVENTS = ("PostToolUse", "UserPromptSubmit")
"""The two events on which the hook reads something into the session rather
than posting an event to the board: the board's word on every tool call, the
doctrine's two sections on the word "backbrief" (card #60)."""
WORD_HOOK_TIMEOUT_SECONDS = 5
"""Claude Code's own ceiling on the read hooks, in the settings entry: the
script's half second (the word) and its one file read (the re-anchor) are
the real ones, this is the belt for an interpreter that cannot start, where
Claude Code's default is 600 s."""


def _board() -> tuple[Store, Live, Runtime, Loops, Doors]:
    store = Store(db_path())
    live = Live(store, renames_of=corpus_renames)
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
    turn with — and, since card #74, the cold reading of any card's title:
    the mark's result and the title's verdict in one command on a defect,
    the title's verdict alone on a plan or an idea."""
    failed = [w.strip() for w in (args.failed or "").split(",") if w.strip()]
    result = doors.triage(
        args.slug,
        args.number,
        result=TriageResult(args.result) if args.result else None,
        words=args.words,
        source=args.source,
        direction=Direction(args.direction) if args.direction else None,
        title=args.title,
        failed=failed,
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


LANES = ".claude/worktrees"
"""Where every lane's worktree lives, under a project's main checkout."""


def hook_install(args: argparse.Namespace) -> int:
    """Register the hook, lay the Codex skills link, arm the git hooks.
    Refused from a lane: the command it registers names this checkout's
    script by absolute path, and a lane's path is gone at the lane's
    close — on 2026-09-07 a lane wrote its own worktree path into three
    projects' settings before anyone read the line (card #73)."""
    if LANES in REPO_ROOT.as_posix():
        print(
            f"needle hook install runs from Needle's main checkout, never a lane: {REPO_ROOT} is "
            "a worktree, and the hook path it would register dies with the lane",
            file=sys.stderr,
        )
        return 1
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
        if event in READ_EVENTS:
            hook["timeout"] = WORD_HOOK_TIMEOUT_SECONDS
        entries.append({"matcher": "", "hooks": [hook]})
        added.append(event)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")
    if added:
        print(f"registered Needle's hook in {settings} for {', '.join(added)}")
    else:
        print(f"Needle's hook is already registered in {settings}")
    laid = lay_skills_link(repo)
    if laid:
        print(laid)
    return _arm_git_hooks(repo)


CODEX_SKILLS = Path(".agents") / "skills"
"""Where Codex looks for a project's skills (the open agent-skills standard;
read live on 2026-09-07, Codex 0.153.4: it scans this folder from the start
directory up to the repository root and follows symlinks). Claude Code does
not read it, so the link points from here at `.claude/skills`, never the
reverse, and the skills stay in one folder."""


def lay_skills_link(repo: Path) -> str:
    """Lay `<repo>/.agents/skills` as a relative link at `../.claude/skills`
    so a Codex session on the project sees what a Claude session sees
    (card #73, item 1), and say what was done in one line. Relative, so a
    clone at another path keeps it. A project without `.claude/skills` gets
    nothing and hears nothing about it (an empty line). A real directory already there is
    the project's own, on the standard already, and is left alone; a link
    pointing elsewhere is named and never replaced — replacing it silently
    would be the one thing this installer does that a project did not ask
    for. The link is a change in the project's tree that git sees, so the
    line says it is to be committed: an uncommitted link is the silent
    failure the plan names, gone at the next clean checkout."""
    skills = repo / SKILLS
    if not skills.is_dir():
        return ""
    link = repo / CODEX_SKILLS
    target = Path("..") / SKILLS
    if link.is_symlink():
        if link.resolve() == skills.resolve():
            return f"Codex already sees {repo.name}'s skills through {CODEX_SKILLS}"
        return (
            f"{CODEX_SKILLS} in {repo.name} links to {link.readlink()}, not {target}; "
            "left as it is — point it at the skills folder yourself if that is wrong"
        )
    if link.exists():
        return f"{repo.name} keeps its own {CODEX_SKILLS}; left as it is"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    return f"laid {CODEX_SKILLS} -> {target} in {repo.name} so Codex sees its skills; commit it"


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
        print(
            f"armed {repo.name}'s git hooks: core.hooksPath = {hooks}"
            + (f" (was {was})" if was else "")
        )
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
    if args.killed:
        return killed_lanes(args, live, runtime)
    if args.slug is None:
        print("name a project, or ask --killed", file=sys.stderr)
        return 1
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


def killed_lanes(args: argparse.Namespace, live: Live, runtime: Runtime) -> int:
    """The lanes the system's memory killer took on one machine over the
    window (card #83, item 5): the plan's daily loop, read from the deaths
    the board named and the machine each session ran on."""
    since = clock.now() - timedelta(hours=args.since_hours)
    here = runtime.here().name
    machine = args.machine or here
    if not any(m.name == machine for m in runtime.machines()):
        print(f"no machine named {machine!r} is on the board", file=sys.stderr)
        return 1
    deaths = live.store.killed_on(machine, since=since, here=here)
    if args.count:
        print(len(deaths))
        return 0
    for death in sorted(deaths, key=lambda d: d.last_alive_at or d.named_at):
        when = (death.last_alive_at or death.named_at).strftime("%Y-%m-%d %H:%MZ")
        print(
            f"{when}  {death.project} #{death.card_number}  {death.session_id[:8]}  {death.words}"
        )
    if not deaths:
        print(f"no lane was killed by the system on {machine} in the last {args.since_hours} h")
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


def _tally_line(tally: Tally) -> str:
    hours = f"{tally.hours:.1f} h" if tally.hours is not None else "hours unread"
    tokens = f"{tally.tokens:,} tokens" if tally.tokens is not None else "tokens unread"
    corrections = (
        f"{tally.correcting} of {tally.trials} corrected before build ({tally.corrections} "
        f"corrections{f', {tally.unrecorded} unrecorded' if tally.unrecorded else ''})"
        if tally.challenge != Challenge.ALONE
        else "no challenge before build"
    )
    return (
        f"    {tally.challenge.value:<15} {tally.trials} trial{'s' if tally.trials != 1 else ''}: "
        f"{corrections}; {tally.escaping} escaped a defect ({tally.escapes}"
        f"{f', {tally.maturing} still inside the window' if tally.maturing else ''}); "
        f"{tally.findings} review findings; {tally.stops} stops; {tally.send_backs} send-backs; "
        f"{tally.reverts} reverts; {tally.fixes_after} fixing commits within a week; "
        f"{hours} mean; {tokens} mean"
    )


def team(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    """The team reading (card #58): reproducible from the corpus, the board
    and git, quality before time, and every conclusion with its sample."""
    if args.slug not in live.projects:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    reading = doors.team.reading(args.slug)
    if args.json:
        print(reading.model_dump_json(indent=1))
        return 0
    print(f"policy {reading.policy}; read {reading.read_at.isoformat()}")
    for shape in reading.shapes:
        print(f"{shape.shape.value}: {shape.conclusion.value} — {shape.why}")
        for tally in shape.tallies:
            print(_tally_line(tally))
        for confound in shape.confounds:
            print(f"    confound: {confound}")
        for seen in shape.observations:
            corrections = (
                f"{seen.corrections} corrections"
                if seen.corrections is not None
                else "corrections unread"
            )
            hours = f"{seen.hours:.1f} h" if seen.hours is not None else "not closed"
            tokens = f"{seen.tokens:,} tokens" if seen.tokens is not None else "tokens unread"
            print(
                f"    #{seen.card_number:<4} {seen.challenge.value:<15} {corrections}; "
                f"{seen.findings} findings (inside {seen.inside}, adjacent {seen.adjacent}, "
                f"outside {seen.outside}); {seen.escapes} escaped; {seen.stops} stops; "
                f"{seen.send_backs} send-backs; "
                f"{'reverted' if seen.reverted else 'fold stands'}; {seen.fixes_after} fixing "
                f"commits within a week; {hours}; {tokens}; "
                f"declared in {seen.declared_in}; read from {', '.join(seen.sources)}"
            )
    if not reading.assigned:
        print("no team assigned yet: the first Start after this slice assigns one")
    for held in reading.assigned:
        print(
            f"assigned #{held.card_number:<4} {held.assigned_at.isoformat()} "
            f"{team_words(held.route)}"
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


def rows(args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors) -> int:
    """The record as JSON, for a project's own tooling (plan 08, item 3):
    every row standing on every card, with the card, the time and the
    writer. `--since` keeps rows written on or after a day; `--kind` keeps
    one kind. A rewritten row's earlier text is on the card's history, not
    here: the record is what the cards say now, dated."""
    if args.slug not in live.projects:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
        except ValueError:
            print(
                f"--since takes a day or a moment in ISO form, not {args.since!r}",
                file=sys.stderr,
            )
            return 1
        if since.tzinfo is None:
            since = since.replace(tzinfo=UTC)
    records = live.store.rows_written(args.slug, since=since)
    if args.kind:
        wanted = RowKind(args.kind.upper())
        records = [r for r in records if r.kind == wanted]
    print(json.dumps([r.model_dump(mode="json") for r in records], indent=2, ensure_ascii=False))
    return 0


def retire(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """Retire a card the board should never have born into the card that
    carries its document (plan 08, item 1): rows and history merge onto the
    survivor, and the retired number keeps one line saying where it went."""
    why = args.why.strip()
    if not why:
        print('a retirement says why: needle retire SLUG N --into M "…"', file=sys.stderr)
        return 1
    survivor = live.retire(args.slug, args.number, args.into, why)
    print(
        f"#{args.number} retired into #{args.into} ({survivor.title}); its history and rows "
        "read there now"
    )
    return 0


# ── a project's focus (card #87) ───────────────────────────────────────


def _strip_words(strip: FocusStrip) -> str:
    """The strip in the words the page shows, for a terminal."""
    lines = [strip.sentence]
    if strip.what_matters:
        lines.append(f"  what matters now: {strip.what_matters}")
    if strip.what_holds:
        lines.append(f"  what holds it back: {strip.what_holds}")
    document = strip.document
    if document is not None:
        lines.append(f"  document: {document.path} at {document.fingerprint}")
        for doubt in document.doubts:
            lines.append(f"  cannot be chosen: {doubt}")
    if strip.ruling is not None:
        chosen = "chosen" if strip.state in (FocusState.CHOSEN, FocusState.PAUSED) else "ruled"
        lines.append(
            f"  {chosen}: {strip.ruling.fingerprint} on {strip.ruling.chosen_at.isoformat()}"
        )
    if strip.check is not None:
        lines.append(f"  the other kind says it {strip.check.verdict.value}: {strip.check.line}")
    elif strip.checking:
        lines.append("  a reader of the other kind is checking the diagnosis")
    elif strip.check_note:
        lines.append(f"  no second reading: {strip.check_note}")
    if strip.conversation is not None:
        lines.append(f"  conversation: {strip.conversation.short_id} on {strip.conversation.slot}")
    if strip.coverage is not None:
        c = strip.coverage
        lines.append(
            f"  {c.assessed} of {c.total} cards assessed; {c.unread} unread, "
            f"{c.needs_evidence} need evidence, {c.stale} stale, {c.reading} being read; "
            f"{strip.moves_proposed} moves proposed"
        )
        lines.append(f"  {c.line}")
    for reading in strip.measures:
        lines.append(
            f"  {reading.side.value}: {reading.words}"
            + (" (baseline)" if reading.baseline else "")
            + f" — {reading.at.isoformat(timespec='minutes')}"
        )
    if strip.recheck_due is not None:
        lines.append(f"  recheck due {strip.recheck_due.isoformat()}")
    if strip.recheck is not None:
        lines.append(f"  recheck said {strip.recheck.outcome.value}: {strip.recheck.words}")
    if strip.accepted is not None:
        lines.append(
            f"  order accepted {strip.accepted.at.isoformat(timespec='minutes')}: "
            f"{len(strip.accepted.moves)} moves"
            + ("; put it back is offered" if strip.put_back_offered else "")
        )
    if strip.paused:
        lines.append(f"  paused: {strip.paused}")
    for door in (strip.talk, strip.choose, strip.propose):
        lines.append(f"  {door.label}: {'offered' if door.offered else 'closed'} — {door.why}")
    return "\n".join(lines)


def focus(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """The strip from the terminal (card #87, item 1): the same object the
    page reads, as words or as JSON. `--unbound --count` is the loop's
    trace: how many projects show a chosen focus with no ruling bound to
    its document — zero by construction, and counted rather than trusted."""
    loops.reconcile_now()
    if args.unbound:
        unbound = 0
        for slug in live.projects:
            strip = live.focus_of(slug)[0]
            if strip.state in (FocusState.CHOSEN, FocusState.PAUSED) and (
                strip.document is None
                or strip.ruling is None
                or strip.document.fingerprint != strip.ruling.fingerprint
            ):
                unbound += 1
        print(unbound if args.count else f"{unbound} focus shown as chosen with no bound ruling")
        return 0
    if args.slug is None:
        print("name a project, or --unbound --count", file=sys.stderr)
        return 1
    if args.slug not in live.projects:
        print(f'no project "{args.slug}" is on the board', file=sys.stderr)
        return 1
    if args.choose:
        print(doors.choose_focus(args.slug).said)
        return 0
    strip, _, arrangement = live.focus_of(args.slug)
    if args.json:
        print(strip.model_dump_json(indent=1))
        return 0
    print(_strip_words(strip))
    if arrangement.available:
        for move in arrangement.moves:
            print(
                f"  move #{move.number}: {move.from_place.column.value} → "
                f"{move.to_place.column.value} — {move.why}"
            )
    else:
        print(f"  Leverage order unavailable: {arrangement.why}")
    return 0


def focus_check(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """A reader of the other kind's verdict on the proposed focus (card #87, item 3)."""
    result = doors.focus_check(
        args.slug,
        verdict=FocusVerdict(args.verdict),
        line=args.line,
        how_known=HowKnown(args.how_known) if args.how_known else None,
        session_id=None,
    )
    print(result.said)
    return 0


def leverage(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """One card's reading against the chosen focus (card #87, item 4): the
    verb that lands the four classes and the three words, and refuses any
    other word before it reaches the record."""
    result = doors.leverage(
        args.slug,
        args.number,
        leverage=Leverage(args.leverage),
        likelihood=Likelihood(args.likelihood) if args.likelihood else None,
        why=args.why,
        session_id=None,
    )
    print(result.said)
    return 0


def focus_recheck(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """The scheduled recheck's word (card #87, item 6)."""
    result = doors.focus_recheck(
        args.slug, outcome=RecheckOutcome(args.outcome), words=args.words, session_id=None
    )
    print(result.said)
    return 0


def leverage_accept(
    args: argparse.Namespace, live: Live, runtime: Runtime, loops: Loops, doors: Doors
) -> int:
    """ "Accept this order" from the terminal, or "Put it back" (card #87, item 5)."""
    if args.put_back:
        print(doors.put_back(args.slug).said)
        return 0
    print(doors.accept_order(args.slug, args.numbers).said)
    return 0


def register(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    p_card = sub.add_parser("card", help="the card as text: the brief a lane opens with")
    p_card.add_argument("slug")
    p_card.add_argument("number", type=int)
    p_card.add_argument("--lane", action="store_true", help="with the riders a launched lane gets")
    p_card.set_defaults(board=True, run=_with_board(card))

    p_row = sub.add_parser("row", help="write one row on a card")
    p_row.add_argument("slug")
    p_row.add_argument("number", type=int)
    p_row.add_argument("kind", choices=[k.value for k in RowKind])
    p_row.add_argument("text")
    p_row.set_defaults(board=True, run=_with_board(row))

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
    p_close.set_defaults(board=True, run=_with_board(close))

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
    p_reading.set_defaults(board=True, run=_with_board(reading))

    p_triage = sub.add_parser(
        "triage",
        help="a reading's result on a card: a defect's mark with the source it read, and "
        "whether the owner could place the card from its title",
    )
    p_triage.add_argument("slug")
    p_triage.add_argument("number", type=int)
    p_triage.add_argument(
        "result",
        nargs="?",
        choices=[r.value for r in TriageResult],
        help="the mark's result; a defect's reading lands one, a plan's or an idea's lands none",
    )
    p_triage.add_argument(
        "words", nargs="?", help="what the source said, in the words the result needs"
    )
    p_triage.add_argument(
        "-t",
        "--title",
        required=True,
        help='the title\'s verdict: "passes", or what you could not place, in words the '
        "writer can act on",
    )
    p_triage.add_argument("--failed", help="the words that failed, comma-separated")
    p_triage.add_argument("--source", help="the path or #N the result rests on")
    p_triage.add_argument(
        "--direction",
        choices=[d.value for d in Direction],
        help="which way it moves the product; required with now",
    )
    p_triage.set_defaults(board=True, run=_with_board(triage))

    p_decisions = sub.add_parser(
        "decisions", help="every decision a colleague took on the rail, with source and fate"
    )
    p_decisions.add_argument("slug", help="a project's slug, or all")
    p_decisions.add_argument("--first", type=int, help="only the first N, for the cold audit")
    p_decisions.set_defaults(board=True, run=_with_board(decisions))

    p_fold = sub.add_parser(
        "fold", help="fast-forward push this lane to origin/develop; level the trunk"
    )
    p_fold.add_argument("--main", action="store_true", help="promote main from the same commit")
    p_fold.add_argument("--worktree", help="the lane's worktree; the current directory if omitted")
    p_fold.set_defaults(board=True, run=_with_board(fold))

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
    p_sync.set_defaults(board=True, run=_with_board(sync))

    p_signals = sub.add_parser("signals", help="read every due signal now")
    p_signals.add_argument("slug", nargs="?")
    p_signals.set_defaults(board=True, run=_with_board(signals))

    p_lanes = sub.add_parser("lanes", help="every card's lane, as the board reads it")
    p_lanes.add_argument("slug", nargs="?")
    p_lanes.add_argument(
        "--killed", action="store_true", help="the lanes the system killed, across projects"
    )
    p_lanes.add_argument("--machine", help="on this machine, by the board's name for it")
    p_lanes.add_argument("--count", action="store_true", help="print how many, nothing else")
    p_lanes.add_argument(
        "--since", dest="since_hours", type=float, default=24.0, help="hours back (24)"
    )
    p_lanes.set_defaults(board=True, run=_with_board(lanes))

    p_verdicts = sub.add_parser(
        "verdicts", help="the verdicts the board's own facts settle, for cards carrying none"
    )
    p_verdicts.add_argument("slug")
    p_verdicts.add_argument("--write", action="store_true", help="write them as VERDICT rows")
    p_verdicts.set_defaults(board=True, run=_with_board(verdicts))

    p_kinds = sub.add_parser(
        "kinds", help="every live suggestion's kind as the board reads it, and why"
    )
    p_kinds.add_argument("slug")
    p_kinds.set_defaults(board=True, run=_with_board(kinds))

    p_rows = sub.add_parser(
        "rows", help="the record as JSON: every row on every card, with its time and writer"
    )
    p_rows.add_argument("slug")
    p_rows.add_argument("--since", help="a day or a moment, ISO; rows written from then on")
    p_rows.add_argument("--kind", help="one row kind, e.g. DELIVERED")
    p_rows.set_defaults(board=True, run=_with_board(rows))

    p_retire = sub.add_parser(
        "retire", help="retire a duplicate card into the card that carries its document"
    )
    p_retire.add_argument("slug")
    p_retire.add_argument("number", type=int, help="the card to retire")
    p_retire.add_argument("--into", type=int, required=True, help="the card that survives")
    p_retire.add_argument("why", help="why, in a sentence, for both cards' history")
    p_retire.set_defaults(board=True, run=_with_board(retire))

    p_water = sub.add_parser(
        "watercooler", help="the project's watercooler: read it, or say one line as a card's lane"
    )
    p_water.add_argument("slug")
    p_water.add_argument("number", type=int, nargs="?", help="the card whose lane is speaking")
    p_water.add_argument("text", nargs="?", help="the line")
    p_water.set_defaults(board=True, run=_with_board(watercooler))

    p_dial = sub.add_parser(
        "dial", help="the dial: read it, or turn auto-fix on or off and set the number of fix lanes"
    )
    p_dial.add_argument("setting", nargs="?", choices=["on", "off"])
    p_dial.add_argument("--lanes", type=int, help="how many fix lanes may run at once")
    p_dial.set_defaults(board=True, run=_with_board(dial))

    p_fixes = sub.add_parser(
        "fixes", help="every fix lane the dial ran, and the rail now against dial-on"
    )
    p_fixes.add_argument("slug", help="a project's slug, or all")
    p_fixes.set_defaults(board=True, run=_with_board(fixes))
    p_team = sub.add_parser("team", help="which team earns its place, per kind of work (card #58)")
    p_team.add_argument("slug", help="a project's slug")
    p_team.add_argument("--json", action="store_true")
    p_team.set_defaults(board=True, run=_with_board(team))

    # `focus` is the runtime's verb for bringing a session's window forward
    # (api/runtime_cli.py), so a project's focus prints under the name of
    # the surface that shows it.
    p_focus = sub.add_parser(
        "strip",
        help="a project's focus as the strip shows it; --json the typed shape; "
        "--choose the owner's click; --unbound --count the loop's trace",
    )
    p_focus.add_argument("slug", nargs="?")
    p_focus.add_argument("--json", action="store_true", help="the typed shape the page reads")
    p_focus.add_argument(
        "--choose", action="store_true", help='"Use this focus", from the terminal'
    )
    p_focus.add_argument(
        "--unbound", action="store_true", help="projects shown chosen with no bound ruling"
    )
    p_focus.add_argument("--count", action="store_true", help="print the number alone")
    p_focus.set_defaults(board=True, run=_with_board(focus))

    p_check = sub.add_parser(
        "focus-check", help="a cold reading's verdict on a project's proposed focus"
    )
    p_check.add_argument("slug")
    p_check.add_argument("verdict", choices=[v.value for v in FocusVerdict])
    p_check.add_argument("line", help="one sentence saying why, naming the weakest link")
    p_check.add_argument("--how-known", choices=[h.value for h in HowKnown])
    p_check.set_defaults(board=True, run=_with_board(focus_check))

    p_leverage = sub.add_parser(
        "leverage", help="one card's reading against the chosen focus: its class and why"
    )
    p_leverage.add_argument("slug")
    p_leverage.add_argument("number", type=int)
    p_leverage.add_argument("leverage", choices=[lv.value for lv in Leverage])
    p_leverage.add_argument("why", help="one sentence citing the card's document and the diagnosis")
    p_leverage.add_argument(
        "--likelihood",
        choices=[lk.value for lk in Likelihood],
        help="how likely it is to work; with helps remove this limit only",
    )
    p_leverage.set_defaults(board=True, run=_with_board(leverage))

    p_recheck = sub.add_parser(
        "focus-recheck", help="the scheduled recheck's word on a chosen focus"
    )
    p_recheck.add_argument("slug")
    p_recheck.add_argument("outcome", choices=[o.value for o in RecheckOutcome])
    p_recheck.add_argument("words", help="one sentence, with the numbers")
    p_recheck.set_defaults(board=True, run=_with_board(focus_recheck))

    p_accept = sub.add_parser(
        "leverage-accept",
        help="accept the leverage order's moves for these cards, or --put-back the last",
    )
    p_accept.add_argument("slug")
    p_accept.add_argument("numbers", type=int, nargs="*", help="the cards whose moves are ticked")
    p_accept.add_argument("--put-back", action="store_true")
    p_accept.set_defaults(board=True, run=_with_board(leverage_accept))
