"""`needle`: the command line. Three verbs put a project on the board and serve
it; the runtime's verbs (`api/runtime_cli.py`) list, place, start, move, stop
and open windows into sessions.

needle add /path/to/repo --name "Harbourmaster"
needle serve
needle types
needle sessions | where | start | move | stop | window | rescues

`add` on a path already on the board re-reads its corpus and says what changed,
so a rescan is always one command away.
"""

import argparse
import json
import re
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from types import FrameType

import uvicorn

from board.import_01 import ImportRefused, read_01
from board.reconcile import Effects
from domain.card import CardOrigin
from domain.corpus import CorpusIndex
from domain.project import Project
from infrastructure import clock
from infrastructure.corpus import NotACorpus, check_corpus, scan
from infrastructure.entrance import read_entrance
from infrastructure.live import Live, sweep
from infrastructure.paths import db_path
from infrastructure.store import Store, StoreRefusal

DEFAULT_PORT = 8480
CARD_FILE_01 = Path("docs/board/needle-board.json")
GRACEFUL_SHUTDOWN_SECONDS = 1.0
"""The ceiling on draining connections at a stop. Streams end by themselves
the moment the stop signal arrives; this is what bounds anything that does not."""


def slug_of(root: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "project"


def describe_read(index: CorpusIndex, effects: Effects) -> str:
    changes = [
        f"born {len(effects.born)}" if effects.born else "",
        f"relinked {len(effects.relinked)}" if effects.relinked else "",
        f"renamed {len(effects.renamed)}" if effects.renamed else "",
        f"archived {len(effects.archived)}" if effects.archived else "",
    ]
    said = ", ".join(c for c in changes if c) or "nothing changed"
    return (
        f"Read the corpus: {len(index.live())} live documents, {len(index.archived())} archived. "
        f"Cards: {said}."
    )


def say_entrance(store: Store, slug: str) -> None:
    """What a session started in this project will read as its constitution.

    A finding, never a refusal (plan 18, ruling 5): a project on a machine with
    no entrance is still a project on the board. The line is recorded on the
    project so the board shows the person the same words the door printed."""
    entrance = read_entrance(Path.home(), clock.now())
    store.note_entrance(slug, entrance)
    print(entrance.line)


def reread(store: Store, project: Project, root: Path) -> int:
    print(f"{root} is already on the board as {project.slug} ({project.name}).")
    if (root / CARD_FILE_01).is_file():
        print("Its 0.1 card file was imported at registration and is not read again.")
    index, effects = sweep(store, project, origin=CardOrigin.ARRIVED, at=clock.now())
    print(describe_read(index, effects))
    say_entrance(store, project.slug)
    return 0


def add(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    try:
        check_corpus(root)
    except NotACorpus as error:
        print(str(error), file=sys.stderr)
        return 1
    database = db_path().resolve()
    if database.is_relative_to(root):
        print(
            f"The store ({database}) sits inside {root}. The board's state never lives in a "
            "project's tree; set NEEDLE_DB elsewhere.",
            file=sys.stderr,
        )
        return 1
    store = Store(database)
    try:
        return _register(store, root, args, database)
    finally:
        store.close()


def _register(store: Store, root: Path, args: argparse.Namespace, database: Path) -> int:
    registered = next((p for p in store.projects() if Path(p.path) == root), None)
    if registered is not None:
        if args.name or args.slug:
            print("--name and --slug do not change a project already on the board.")
        return reread(store, registered, root)
    project = Project(
        slug=args.slug or slug_of(root),
        name=args.name or root.name,
        path=str(root),
        registered_at=clock.now(),
    )
    try:
        store.add_project(project)
    except StoreRefusal as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Registered {project.name} as {project.slug} at {project.path}")

    card_file = root / CARD_FILE_01
    if card_file.is_file():
        at = clock.now()
        index = scan(root, at)
        try:
            imported = read_01(json.loads(card_file.read_text(encoding="utf-8")), index)
            store.import_01(project.slug, imported, at)
        except (ImportRefused, StoreRefusal, json.JSONDecodeError) as error:
            print(f"The 0.1 import was refused and nothing was written: {error}", file=sys.stderr)
            return 1
        linked = sum(1 for c in imported.cards if c.link is not None)
        print(
            f"Imported Needle 0.1's card file: {len(imported.cards)} cards in "
            f"{len(imported.groups)} groups, {linked} linked to a document, "
            f"{len(imported.retired)} retired numbers recorded, numbering continues at "
            f"{imported.next_number}."
        )
        for ask in imported.skipped_asks:
            print(
                f"  Skipped #{ask.number} ({ask.alarm}): 0.1's own ask, stated as a count instead."
            )

    index, effects = sweep(store, project, origin=CardOrigin.FOUNDING, at=clock.now())
    print(describe_read(index, effects))
    say_entrance(store, project.slug)
    print(f"Store: {database}")
    return 0


class NeedleServer(uvicorn.Server):
    """uvicorn's server, with the board told the moment a stop signal arrives.

    uvicorn drains open connections before it runs the lifespan's shutdown,
    and an open stream never drained: it waited on the next board change
    while the page it served stayed connected, so `needle serve` outlived
    SIGTERM until systemd killed it (measured 2026-09-04: no exit in 12 s with
    one stream open). Closing the board here ends every stream at once, and
    the graceful-shutdown ceiling bounds anything else.
    """

    def __init__(self, config: uvicorn.Config, live_of: Callable[[], Live | None]):
        super().__init__(config)
        self._live_of = live_of

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        super().handle_exit(sig, frame)
        live = self._live_of()
        if live is not None:
            live.close()


def _answered(sig: int, frame: FrameType | None) -> None:
    """After a clean stop uvicorn re-raises the signal it stopped on, so the
    process would end by it (exit 143). A stop that was asked for and done is a
    success: the re-raised signal lands here and the process exits 0."""


def serve(args: argparse.Namespace) -> int:
    from api.app import create_app

    store = Store(db_path())
    if not store.projects():
        print("No project is on the board yet. Run: needle add /path/to/repo", file=sys.stderr)
        return 1
    print(f"Needle at http://{args.host}:{args.port}/  (store: {db_path()})")
    app = create_app(store)
    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level="warning",
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
    )
    server = NeedleServer(config, lambda: getattr(app.state, "live", None))
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(stop_signal, _answered)
    try:
        server.run()
    finally:
        store.close()
    return 0


def projects(args: argparse.Namespace) -> int:
    store = Store(db_path())
    for project in store.projects():
        print(f"{project.slug}\t{project.name}\t{project.path}")
    store.close()
    return 0


def types(args: argparse.Namespace) -> int:
    from api.typegen import write_types

    changed = write_types()
    for path in changed:
        print(f"wrote {path}")
    if not changed:
        print("types are current")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="needle", description="A kanban over a corpus of plans.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="put a project on the board by its path")
    p_add.add_argument("path")
    p_add.add_argument("--name", help="the project's display name; the folder name if omitted")
    p_add.add_argument("--slug", help="the project's URL slug; derived from the folder if omitted")
    p_add.set_defaults(run=add)

    p_serve = sub.add_parser("serve", help="serve the board")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_serve.set_defaults(run=serve)

    p_projects = sub.add_parser("projects", help="list the projects on the board")
    p_projects.set_defaults(run=projects)

    p_types = sub.add_parser("types", help="regenerate the frontend's types from the domain")
    p_types.set_defaults(run=types)

    from api.board_cli import register as register_board
    from api.runtime_cli import register

    register(sub)
    register_board(sub)

    args = parser.parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
