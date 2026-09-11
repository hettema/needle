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

from board.assemble import (
    assemble_board,
    assemble_detail,
    card_gate,
    document_of,
    folded_under,
    watch_signal,
)
from board.dial import dial_state, held_lanes
from board.focus import (
    READ_COLUMNS,
    card_leverage,
    coverage_of,
    is_chosen,
    paused_why,
    strip_of,
    unavailable_why,
)
from board.lane import nothing_read
from board.leverage import Judged, arrange, wake_line
from board.reconcile import Effects, reconcile
from board.triage import Sources
from domain.audit import AuditKind
from domain.board import BoardState, CardDetail, MachineState
from domain.card import Actor, Card, CardOrigin, Place
from domain.column import DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex
from domain.dial import DialState, Headroom
from domain.document import DocumentKind, SuggestionKind
from domain.evidence import Evidence
from domain.focus import (
    Arrangement,
    CardLeverage,
    FocusStrip,
    Leverage,
    LeverageState,
    MeasureReading,
    ReadingKind,
)
from domain.lane import Doors, Lane, LaneSnapshot
from domain.notice import Shown
from domain.project import Project
from domain.row import Row
from domain.signal import SessionWork, SignalKind
from domain.watercooler import WatercoolerLine
from domain.window import WindowKind
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


RenamesOf = Callable[[Path], dict[str, str]]
"""What git knows about renames in a project's corpus, old path → new path;
the runtime's reader, handed in by the door that composes the board, since
the store's layer runs nothing (plan 08, item 1)."""


def sweep(
    store: Store,
    project: Project,
    *,
    origin: CardOrigin,
    at: datetime,
    previous: CorpusIndex | None = None,
    renames_of: RenamesOf | None = None,
) -> tuple[CorpusIndex, Effects]:
    index = scan(Path(project.path), at)
    moves = (lambda: renames_of(Path(project.path))) if renames_of is not None else None
    effects = reconcile(index, store.cards(project.slug), previous=previous, moves=moves)
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
    def __init__(
        self,
        store: Store,
        now: Callable[[], datetime] = clock.now,
        renames_of: RenamesOf | None = None,
    ):
        self.store = store
        self.now = now
        self.renames_of = renames_of
        self.version = 0
        self.projects: dict[str, LiveProject] = {}
        self.closing = False
        """Set once the server was told to stop; every open stream ends on it."""
        self.machine = MachineState(missing=[])
        """What the runtime cannot reach, as the loop last found; shown on the page."""
        self.headroom: Headroom | None = None
        """The machine's memory against the dial's floor, as the dial last
        read it before a beat; None until the first beat."""
        self.on_change: Callable[[], Awaitable[None]] | None = None
        """What to run when another process wrote to the store, or the corpus
        changed a card: the loops set it, so a row written from the command
        line and a plan that landed are acted on at once, not at the floor."""
        self.shown: Shown | None = None
        """The card the runtime last asked every open page to put in front of
        the owner (card #41): carried on the stream, never in a board."""
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
            index, effects = sweep(
                self.store,
                project,
                origin=CardOrigin.ARRIVED,
                at=self.now(),
                renames_of=self.renames_of,
            )
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
        index, effects = sweep(
            self.store,
            live.project,
            origin=CardOrigin.ARRIVED,
            at=self.now(),
            previous=live.index,
            renames_of=self.renames_of,
        )
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

    def sources(self, slug: str) -> Sources:
        """A source reader for one read of one project: the corpus's own
        paths resolved against the project root, and a card number resolved
        to the document behind it (plan 59, item 3). One per read, never
        kept: a cached fingerprint that outlived its read would be exactly
        the stale row the fingerprint exists to catch."""
        live = self._live(slug)

        def card_document(number: int) -> str | None:
            card = self.store.card(slug, number)
            return card.link.path() if card is not None and card.link is not None else None

        return Sources(Path(live.project.path), card_document)

    def board(self, slug: str) -> BoardState:
        live = self._live(slug)
        focus, leverages, leverage = self.focus_of(slug)
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
            triage_sessions=self.store.open_windowless_sessions(slug, SessionWork.TRIAGE),
            triages=self.store.latest_triages(slug),
            sources=self.sources(slug),
            dial=self.dial_state(),
            title_readings=self.store.latest_title_readings(slug),
            focus=focus,
            leverage=leverage,
            leverages=leverages,
        )

    def focus_of(self, slug: str) -> tuple[FocusStrip, dict[int, CardLeverage], Arrangement]:
        """The project's focus as the strip shows it, every card's standing
        against it, and the board as the focus would arrange it (card #87):
        one read of the store's facts, derived by the pure functions in
        `board/focus.py` and `board/leverage.py`, so the page, the verb and
        the API read one answer."""
        live = self._live(slug)
        store = self.store
        now = self.now()
        document = live.index.focus
        ruling = store.focus_ruling(slug)
        snapshot = live.snapshot
        conversations = snapshot.conversations if snapshot is not None else []
        conversation = next((c for c in conversations if c.kind == WindowKind.FOCUS), None)
        talked_before = any(d.kind == WindowKind.FOCUS for d in store.discussions(slug))
        calls = store.focus_calls(slug)
        open_calls = [c for c in calls if c.ended_at is None]
        check = None
        checking = False
        check_note = None
        recheck = store.focus_recheck(slug)
        measures: list[MeasureReading] = []
        if document is not None:
            check = store.focus_check(slug, document.fingerprint)
            checks = [
                c
                for c in calls
                if c.kind == ReadingKind.CHECK and c.fingerprint == document.fingerprint
            ]
            checking = any(c.ended_at is None for c in checks)
            if check is None and not checking and checks and not checks[-1].landed:
                check_note = checks[-1].note or "the reading ended without an answer"
            latest: dict[str, MeasureReading] = {}
            for reading in store.measure_readings(slug, document.fingerprint):
                latest[reading.side.value] = reading
            measures = sorted(latest.values(), key=lambda m: m.side.value)
        chosen = is_chosen(document, ruling)
        cards = [c for c in store.cards(slug) if c.folded_into is None]
        leverages: dict[int, CardLeverage] = {}
        judged: dict[int, Judged] = {}
        accepted = None
        put_back_offered = False
        if chosen:
            assert document is not None and ruling is not None
            readings = store.latest_leverage_readings(slug)
            reading_open = {c.card_number for c in open_calls if c.kind == ReadingKind.CARD}
            doors = snapshot.doors if snapshot is not None else {}
            last_readings = store.last_readings(slug)
            documents = {c.number: document_of(c, live.index) for c in cards}
            for card in cards:
                doc = documents[card.number]
                shipped = card.place.column in (Column.EXECUTED, Column.DONE)
                if doc is None or (doc.archived and not shipped):
                    # A card behind an archived document off the shipped
                    # columns is nobody's to read: the loop skips it too.
                    continue
                found = doors.get(card.number)
                waits = found.readiness.waits if found is not None else []
                held = [w.label for w in waits if not w.shipped]
                leverages[card.number] = card_leverage(
                    readings.get(card.number),
                    document.fingerprint,
                    doc,
                    reading_open=card.number in reading_open,
                    hold=", ".join(held) if held else None,
                )
            unblocks: dict[int, int] = {}
            for card in cards:
                lv = leverages.get(card.number)
                doc = documents[card.number]
                if (
                    lv is None
                    or doc is None
                    or lv.state != LeverageState.READ
                    or lv.leverage != Leverage.HELPS_REMOVE
                ):
                    continue
                for named in doc.sequenced:
                    if named.words is None:
                        unblocks[named.number] = unblocks.get(named.number, 0) + 1
            for card in cards:
                doc = documents[card.number]
                signal, _ = watch_signal(card)
                last = last_readings.get(card.number)
                judged[card.number] = Judged(
                    number=card.number,
                    place=card.place,
                    gate=card_gate(card, doc),
                    kind=doc.kind if doc is not None else None,
                    suggestion_kind=doc.suggestion_kind if doc is not None else None,
                    document_fingerprint=doc.fingerprint if doc is not None else None,
                    leverage=leverages.get(card.number),
                    unblocks=unblocks.get(card.number, 0),
                    owner_signal=signal is not None and signal.kind == SignalKind.OWNER,
                    last_read=last.at if last is not None else None,
                )
            accepted = store.latest_acceptance(slug)
            if accepted is not None and accepted.put_back_at is None:
                own = (f"(batch {accepted.id},", f"(batch {accepted.id})")
                by_hand = [
                    m
                    for m in store.owner_moves_since(slug, accepted.at)
                    if not any(mark in m.detail for mark in own)
                ]
                put_back_offered = (
                    not by_hand and accepted.focus_fingerprint == document.fingerprint
                )
                if not put_back_offered:
                    # A hand move retired it: there is no old state any more.
                    accepted = None
            else:
                accepted = None
        paused = paused_why(document, ruling, recheck, now) if chosen else None
        arrangement = arrange(
            store.layout(slug),
            judged,
            focus_fingerprint=document.fingerprint if document is not None else "",
            declines=store.declines(slug),
            wake=wake_line(
                document.recheck.signal.what if document.recheck.signal else None,
                document.recheck.line,
            )
            if document is not None
            else None,
            available=chosen and paused is None,
            why=None,
        )
        places = {c.number: c.place for c in cards}
        shown = {n: lv for n, lv in leverages.items() if places[n].column in READ_COLUMNS}
        strip = strip_of(
            document=document,
            ruling=ruling,
            check=check,
            checking=checking,
            check_note=check_note,
            conversation=conversation,
            talked_before=talked_before,
            coverage=coverage_of(places, shown) if chosen else None,
            moves_proposed=len(arrangement.moves),
            accepted=accepted,
            put_back_offered=put_back_offered,
            recheck=recheck,
            measures=measures,
            now=now,
        )
        if not arrangement.available:
            arrangement = arrangement.model_copy(update={"why": unavailable_why(strip)})
        return strip, leverages, arrangement

    def dial_state(self) -> DialState:
        """The dial with the fix lanes live against its number, the planned
        cards it holds without counting, the memory floor's word, and
        whether the machine is quiet, from every project's last read (plan
        11; the plan "as many lanes as the machine can hold", item 3)."""
        lanes = {
            slug: live.snapshot.lanes
            for slug, live in self.projects.items()
            if live.snapshot is not None
        }
        fix_lanes = self.store.fix_lanes()
        triaging = sum(
            len(self.store.open_windowless_sessions(slug, SessionWork.TRIAGE))
            for slug in self.projects
        )
        return dial_state(
            self.store.dial(),
            fix_lanes,
            lanes,
            held=held_lanes(fix_lanes, self.start_offered),
            room=self.headroom,
            triaging=triaging,
        )

    def start_offered(self, slug: str, number: int) -> bool | None:
        """Whether a card's Start door is open, from the loop's last read of
        its project; None while that project is unread."""
        live = self.projects.get(slug)
        if live is None or live.snapshot is None:
            return None
        doors = live.snapshot.doors.get(number)
        return doors.start.offered if doors is not None else None

    def set_headroom(self, room: Headroom) -> None:
        before = self.headroom
        self.headroom = room
        if before is None or (before.full, before.sentence) != (room.full, room.sentence):
            self.bump()

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
            triaging=self.store.open_windowless_sessions(slug, SessionWork.TRIAGE).get(number),
            triage=self.store.triage(slug, number),
            sources=self.sources(slug),
            title_reading=self.store.latest_title_readings(slug).get(number),
            leverage=self.focus_of(slug)[1].get(number),
            team=self.store.composition(slug, number),
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

    def retire(self, slug: str, number: int, into: int, why: str) -> Card:
        """Retire a card into another (plan 08, item 1). Refused while the
        card's document is in the corpus: a card whose document exists is
        not a duplicate, whatever else it looks like."""
        live = self._live(slug)
        card = self.card(slug, number)
        if card.link is not None and live.index.find(card.link.kind, card.link.stem) is not None:
            raise StoreRefusal(
                f"#{number} cannot be retired: its document {card.link.path()} is in the corpus, "
                "so it is a card of its own."
            )
        survivor = self.store.retire_into(slug, number, into, why=why, at=self.now())
        self.bump()
        return survivor

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

    def show(self, slug: str, number: int) -> Shown:
        """Ask every open page to put the card in front of the owner (card
        #41): the notification's button, through the runtime's `show`."""
        self._live(slug)
        if self.store.card(slug, number) is None:
            raise StoreRefusal(f"There is no card #{number} on this board.")
        last = self.shown.id if self.shown is not None else 0
        self.shown = Shown(id=last + 1, project=slug, card_number=number, at=self.now())
        self.bump()
        return self.shown

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
