"""The running board: one index per project, kept true by the watcher.

The store holds what the documents cannot; the index holds what they say.
`sweep` is the one function that reads the corpus and makes the store agree
with it, and it is the same function at registration, at startup and on every
change the watcher hears — so there is exactly one way a document becomes a
card.

The project list is read from the store, never remembered: `sync_projects`
adds whatever `needle add` registered since the last look, and it runs on
every request for the list and whenever the store's file changes on disk, so
a project added while the server runs is on the page without a restart.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

from watchfiles import Change, awatch

from board.assemble import assemble_board, assemble_detail
from board.lane import nothing_read
from board.reconcile import Effects, reconcile
from domain.audit import AuditKind
from domain.board import BoardState, CardDetail, MachineState
from domain.card import Actor, Card, CardOrigin, Place
from domain.corpus import CorpusIndex
from domain.evidence import Evidence
from domain.lane import Doors, Lane, LaneSnapshot
from domain.project import Project
from domain.row import Row
from infrastructure import clock
from infrastructure.corpus import scan, watch
from infrastructure.store import Store, StoreRefusal

log = logging.getLogger("needle")


def sweep(
    store: Store, project: Project, *, origin: CardOrigin, at: datetime
) -> tuple[CorpusIndex, Effects]:
    index = scan(Path(project.path), at)
    effects = reconcile(index, store.cards(project.slug))
    if not effects.empty():
        store.apply_effects(project.slug, effects, origin=origin, at=at)
    return index, effects


class LiveProject:
    def __init__(self, project: Project, index: CorpusIndex):
        self.project = project
        self.index = index
        self.watching = False
        self.watch_note: str | None = "not started"
        self.task: asyncio.Task[None] | None = None
        self.snapshot: LaneSnapshot | None = None
        """Every lane and every card's doors, as the loop last read them."""


class Live:
    def __init__(self, store: Store, now: Callable[[], datetime] = clock.now):
        self.store = store
        self.now = now
        self.version = 0
        self.projects: dict[str, LiveProject] = {}
        self.closing = False
        """Set once the server was told to stop; every open stream ends on it."""
        self.machine = MachineState(missing=[])
        """What the runtime cannot reach, as the loop last found; shown on the page."""
        self.on_store_change: Callable[[], Awaitable[None]] | None = None
        """What to run when the store's file changes under the server: the
        loops set it, so a row written from the command line is read at once."""
        self._stop = asyncio.Event()
        self._store_task: asyncio.Task[None] | None = None
        self._waiters: list[asyncio.Future[int]] = []

    # ── lifecycle ──────────────────────────────────────────────────────

    def load(self) -> list[str]:
        """Read the corpus of every project the store names and this board does
        not yet hold, and make the store agree. Returns the slugs added."""
        added: list[str] = []
        for project in self.store.projects():
            if project.slug in self.projects:
                continue
            index, effects = sweep(self.store, project, origin=CardOrigin.ARRIVED, at=self.now())
            self.projects[project.slug] = LiveProject(project, index)
            added.append(project.slug)
            if not effects.empty():
                self.bump()
        return added

    async def start_watching(self) -> None:
        """An ear on every project's corpus, and one on the store's own file."""
        for live in self.projects.values():
            if live.task is None:
                live.task = asyncio.create_task(self._watch_loop(live))
        if self._store_task is None:
            self._store_task = asyncio.create_task(self._watch_store_loop())

    async def sync_projects(self) -> list[str]:
        """Pick up projects registered since the last look; watch them from now on."""
        added = self.load()
        if added:
            await self.start_watching()
            self.bump()
        return added

    def close(self) -> None:
        """The server is stopping: wake every stream so it can end."""
        self.closing = True
        self._wake(self.version)

    async def stop(self) -> None:
        self.close()
        self._stop.set()
        tasks = [live.task for live in self.projects.values() if live.task is not None]
        if self._store_task is not None:
            tasks.append(self._store_task)
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _watch_loop(self, live: LiveProject) -> None:
        try:
            live.watching = True
            live.watch_note = None
            self.bump()
            async for _changes in watch(Path(live.project.path), self._stop):
                self.rescan(live.project.slug)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — the reason is shown, never swallowed
            live.watching = False
            live.watch_note = f"{type(error).__name__}: {error}"
            self.bump()

    async def _watch_store_loop(self) -> None:
        """The store's file is how `needle add` reaches a running server: a
        write to it is heard here and the project list re-read. A project
        whose own watcher has failed is rescanned on the same signal, so a
        `needle add` re-read from the command line still lands on the page."""
        path = self.store.path

        def is_store_file(change: Change, changed: str) -> bool:
            return Path(changed).name.startswith(path.name)

        try:
            async for _changes in awatch(
                path.parent, stop_event=self._stop, recursive=False, watch_filter=is_store_file
            ):
                await self.sync_projects()
                for live in list(self.projects.values()):
                    if not live.watching:
                        self.rescan(live.project.slug)
                # A write from outside the server — a session's `needle row`,
                # a `needle close` — is a change the page has to see and the
                # loops have to act on; the server's own writes bumped already
                # and cost one more read here.
                self.bump()
                if self.on_store_change is not None:
                    await self.on_store_change()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — the reason is logged, never swallowed
            log.warning(
                "The board stopped hearing the store change (%s: %s); a project added from now "
                "on is on the page at the next reload, not before.",
                type(error).__name__,
                error,
            )

    # ── the corpus ─────────────────────────────────────────────────────

    def rescan(self, slug: str) -> Effects:
        live = self._live(slug)
        index, effects = sweep(self.store, live.project, origin=CardOrigin.ARRIVED, at=self.now())
        live.index = index
        self.bump()
        return effects

    # ── change notification ────────────────────────────────────────────

    def bump(self) -> None:
        self.version += 1
        self._wake(self.version)

    def _wake(self, version: int) -> None:
        waiters, self._waiters = self._waiters, []
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(version)

    async def wait_for_change(self, since: int, timeout: float) -> int:
        """The version after `since`, or the current one when nothing changed in
        time — or at once when the server is closing."""
        if self.version > since or self.closing:
            return self.version
        waiter: asyncio.Future[int] = asyncio.get_running_loop().create_future()
        self._waiters.append(waiter)
        try:
            return await asyncio.wait_for(waiter, timeout)
        except TimeoutError:
            return self.version

    # ── reads and the one write ────────────────────────────────────────

    def _live(self, slug: str) -> LiveProject:
        live = self.projects.get(slug)
        if live is None:
            raise StoreRefusal(f'No project "{slug}" is on the board.')
        return live

    def board(self, slug: str) -> BoardState:
        live = self._live(slug)
        return assemble_board(
            project=live.project,
            layout=self.store.layout(slug),
            cards=self.store.cards(slug),
            index=live.index,
            version=self.version,
            watching=live.watching,
            watch_note=live.watch_note,
            now=self.now(),
            snapshot=live.snapshot,
            readings=self.store.last_readings(slug),
            trunk=self.store.trunk(slug),
            machine=self.machine,
            placements=self.store.placements(slug),
        )

    def card(self, slug: str, number: int) -> Card:
        self._live(slug)
        card = self.store.card(slug, number)
        if card is None:
            raise StoreRefusal(f"There is no card #{number} on this board.")
        return card

    def detail(self, slug: str, number: int) -> CardDetail:
        live = self._live(slug)
        card = self.card(slug, number)
        lane, doors = self.lane_and_doors(slug, card)
        return assemble_detail(
            card,
            live.index,
            self.store.history(slug, number),
            self.now(),
            lane=lane,
            doors=doors,
            readings=self.store.readings(slug, number),
            read=live.snapshot is not None,
        )

    def lane_and_doors(self, slug: str, card: Card) -> tuple[Lane | None, Doors]:
        """The card's lane and doors from the loop's last read; before the
        first read, a lane derived from nothing and every door closed for
        that reason."""
        live = self._live(slug)
        if live.snapshot is not None and card.number in live.snapshot.doors:
            return live.snapshot.lanes.get(card.number), live.snapshot.doors[card.number]
        return nothing_read(card, live.project.path, self.now())

    def move(
        self,
        slug: str,
        number: int,
        to: Place,
        *,
        actor: Actor = Actor.OWNER,
        detail: str | None = None,
        evidence: Evidence | None = None,
    ) -> BoardState:
        live = self._live(slug)
        self.store.move(
            live.project.slug, number, to, actor, self.now(), detail=detail, evidence=evidence
        )
        self.bump()
        return self.board(slug)

    def add_row(self, slug: str, number: int, row: Row, actor: Actor) -> Card:
        self._live(slug)
        card = self.store.add_row(slug, number, row, actor, self.now())
        self.bump()
        return card

    def note(self, slug: str, number: int, kind: AuditKind, actor: Actor, detail: str) -> None:
        self._live(slug)
        self.store.note(slug, number, kind, actor, self.now(), detail)
        self.bump()

    def set_snapshot(self, slug: str, snapshot: LaneSnapshot) -> bool:
        """The loop's read of the project's lanes. Bumps only when a lane or
        a door changed, so a quiet machine costs the page nothing."""
        live = self._live(slug)
        before = live.snapshot
        live.snapshot = snapshot
        changed = before is None or before.lanes != snapshot.lanes or before.doors != snapshot.doors
        if changed:
            self.bump()
        return changed

    def set_machine(self, machine: MachineState) -> None:
        if machine != self.machine:
            self.machine = machine
            self.bump()
