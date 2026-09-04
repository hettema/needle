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

from board.assemble import assemble_board, assemble_detail, folded_under
from board.dial import dial_state
from board.lane import nothing_read
from board.reconcile import Effects, reconcile
from domain.audit import AuditKind
from domain.board import BoardState, CardDetail, MachineState
from domain.card import Actor, Card, CardOrigin, Place
from domain.column import DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex
from domain.dial import DialState
from domain.document import DocumentKind, SuggestionKind
from domain.evidence import Evidence
from domain.lane import Doors, Lane, LaneSnapshot
from domain.project import Project
from domain.row import Row
from domain.signal import SessionWork
from domain.watercooler import WatercoolerLine
from infrastructure import clock
from infrastructure.corpus import scan, watch
from infrastructure.store import Store, StoreRefusal

log = logging.getLogger("needle")

WATERCOOLER_SHOWN = 20
"""How many of the newest watercooler lines the page and a brief carry; the
whole file is `needle watercooler SLUG`."""

WRITE_POLL_SECONDS = 1.0
"""How often the server asks the store whether another process committed
(plan 06, item 6): a session's `needle row` is on the page within this."""


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
        self.on_change: Callable[[], Awaitable[None]] | None = None
        """What to run when another process wrote to the store, or the corpus
        changed a card: the loops set it, so a row written from the command
        line and a plan that landed are acted on at once, not at the floor."""
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
        """An ear on every project's corpus, and one on the store's writes."""
        for live in self.projects.values():
            if live.task is None:
                live.task = asyncio.create_task(self._watch_loop(live))
        if self._store_task is None:
            self._store_task = asyncio.create_task(self._hear_writes_loop())

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
                effects = self.rescan(live.project.slug)
                # A card born, relinked or archived changes what the loops
                # would move and which doors it has: read the machine now.
                if not effects.empty() and self.on_change is not None:
                    await self.on_change()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — the reason is shown, never swallowed
            live.watching = False
            live.watch_note = f"{type(error).__name__}: {error}"
            self.bump()

    async def _hear_writes_loop(self) -> None:
        """Every second, ask the store's write stamp whether a process other
        than this one committed (plan 06, item 6): a session's `needle row`,
        a `needle close`, a `needle add`. The server's own commits are
        subtracted, so it never re-reads itself — the file watcher this
        replaces heard the lane loop's own lane records land, re-read, wrote
        again, and turned the page over twice a second (measured 2026-09-04).
        On a foreign write the project list is re-read, a project whose own
        corpus watcher has failed is rescanned, the page is told, and the
        loops act."""
        seq, _ = await asyncio.to_thread(self.store.write_stamp)
        self.store.own_commits_upto(seq)
        last = seq
        try:
            while not self._stop.is_set():
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._stop.wait(), WRITE_POLL_SECONDS)
                if self._stop.is_set():
                    return
                seq, _ = await asyncio.to_thread(self.store.write_stamp)
                own = self.store.own_commits_upto(seq)
                foreign = (seq - last) - own
                last = seq
                if foreign <= 0:
                    continue
                await self.sync_projects()
                for live in list(self.projects.values()):
                    if not live.watching:
                        self.rescan(live.project.slug)
                self.bump()
                if self.on_change is not None:
                    await self.on_change()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 — the reason is logged, never swallowed
            log.warning(
                "The board stopped hearing other processes write (%s: %s); a row written from "
                "the command line is on the page at the next reload, not before.",
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
            watercooler=self.store.watercooler(slug, limit=WATERCOOLER_SHOWN),
            reading_sessions=self.store.open_windowless_sessions(slug, SessionWork.READING),
            planning_sessions=self.store.open_windowless_sessions(slug, SessionWork.PLANNING),
            dial=self.dial_state(),
        )

    def dial_state(self) -> DialState:
        """The dial with the fix lanes live against its number, and whether
        the machine is quiet, from every project's last read (plan 11)."""
        lanes = {
            slug: live.snapshot.lanes
            for slug, live in self.projects.items()
            if live.snapshot is not None
        }
        return dial_state(self.store.dial(), self.store.fix_lanes(), lanes)

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
            watercooler=self.store.watercooler(slug, limit=WATERCOOLER_SHOWN),
            folded=folded_under(self.store.cards(slug)).get(number),
            reading=self.store.open_windowless_sessions(slug, SessionWork.READING).get(number),
            heard=self.store.heard_mark(slug, number),
            machine=self.machine,
            planning=self.store.open_windowless_sessions(slug, SessionWork.PLANNING).get(number),
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
        self._refuse_a_move_against_the_rail(live, number, to)
        self.store.move(
            live.project.slug, number, to, actor, self.now(), detail=detail, evidence=evidence
        )
        self.bump()
        return self.board(slug)

    def _refuse_a_move_against_the_rail(self, live: LiveProject, number: int, to: Place) -> None:
        """Backlog's defects rail is a lens on the document's `Kind:` line
        (plan 06, item 2): the corpus puts a defect on it and an idea below
        it on every read, so a hand move that disagrees with the line would
        be undone at the next read. It is refused now instead, with the line
        to edit named, so the board never fights the owner later in silence."""
        if to.column != Column.BACKLOG:
            return
        card = self.store.card(live.project.slug, number)
        if card is None or card.link is None or card.link.kind != DocumentKind.SUGGESTION:
            return
        document = live.index.find(card.link.kind, card.link.stem)
        if document is None or document.suggestion_kind is None:
            return
        is_defect = document.suggestion_kind == SuggestionKind.DEFECT
        if (to.group == DEFECTS_RAIL) == is_defect:
            return
        word = document.suggestion_kind.value
        raise StoreRefusal(
            f"#{number}'s document says Kind: {word}, so it reads "
            + ("on the defects rail" if is_defect else "below the rail")
            + f"; to move it, change the `**Kind:**` line in {document.path}."
        )

    def add_row(self, slug: str, number: int, row: Row, actor: Actor) -> Card:
        self._live(slug)
        card = self.store.add_row(slug, number, row, actor, self.now())
        self.bump()
        return card

    def rule_on_verdict(
        self,
        slug: str,
        number: int,
        *,
        accepted: bool,
        word: str | None,
        to: Place | None,
        replace: bool,
        said: str,
    ) -> Card:
        self._live(slug)
        card = self.store.rule_on_verdict(
            slug,
            number,
            self.now(),
            accepted=accepted,
            word=word,
            to=to,
            replace=replace,
            said=said,
        )
        self.bump()
        return card

    def say(self, slug: str, number: int | None, actor: Actor, text: str) -> WatercoolerLine:
        """One line on the project's watercooler, from a card's lane or the board."""
        self._live(slug)
        line = self.store.say(slug, number, actor, self.now(), text)
        self.bump()
        return line

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
