"""The focus loop: the readings a project's focus asks for, each in a
fresh thread of the other make (card #87, items 3, 4 and 6).

Three readings, one beat. When a proposed focus lands, a colleague of the
other make checks the diagnosis cold before the ruling is offered (item
3). While a focus is chosen, every open card is read against it once, and
again when the focus or the card's document changes — oldest first, one
per beat (item 4). On the recheck's date the two measures are read against
the diagnosis's prediction and one word lands: which link broke, or none
(item 6); between rechecks the machine-readable measures are read on the
recheck's cadence, baseline first.

Every reading is a call the loop records (`needle wait` reads it) and
tends on the next beat: the answer landed and is landed through the one
door for its kind, or the thread ended without one and the record says
why. A reading that dies is counted, and after the cap the card or the
proposal says so instead of looping. The loop never moves a card, never
writes a rank, never starts a lane and never reads a class to choose work
— it reads classes only to know which cards have none yet — and a ratchet
holds that the dial cannot see the class at all
(`tests/ratchets/test_the_lens_never_chooses_work.py`).

Why the loop and not `api/dial.py`: the dial is the seat that plans and
starts a defect on the owner's standing ruling, and the plan's class rule
is that nothing under it may read a leverage result. A loop of its own on
the same cadence keeps that boundary a fact about imports rather than a
convention inside one module.
"""

import asyncio
import contextlib
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from api.doors import DoorFailed, DoorRefused, Doors
from api.loops import Loops
from board.assemble import document_of
from board.brief import check_brief, leverage_brief, recheck_brief
from board.focus import READ_COLUMNS, is_chosen, recheck_due, wants_card_reading
from board.signals import is_due
from domain.card import Card
from domain.column import Column
from domain.focus import (
    MACHINE_READ_KINDS,
    CheckAnswer,
    FocusCall,
    FocusDocument,
    FocusRuling,
    Leverage,
    LeverageAnswer,
    MeasureSide,
    ReadingKind,
    RecheckAnswer,
    RecheckOutcome,
)
from domain.gate import Gate
from domain.launch import LaunchVerdict
from domain.session import Session
from domain.triage import Source
from infrastructure import clock
from infrastructure.live import Live, LiveProject
from infrastructure.paths import data_dir
from runtime import codex
from runtime.calls import answer_landed
from runtime.service import Runtime

log = logging.getLogger("needle")

FOCUS_SECONDS = 60.0
"""The loop's beat: one reading opened per beat at most, so a board of
forty open cards is read in forty minutes and every ask re-reads the
machine."""
READING_EFFORT = Gate.HIGH
"""Reading two documents and applying one written rule is work, not
thinking work: the same effort a defect's mark gets."""
ASK_CEILING_SECONDS = 1800.0
"""A reading still without an answer past this is stopped and the record
says so."""
CARD_ATTEMPTS = 3
CHECK_ATTEMPTS = 2
RECHECK_ATTEMPTS = 2
"""How many readings may die on one card, one proposal or one recheck
before the loop stops opening them and the strip or the card says why."""
SHIPPED: frozenset[Column] = frozenset({Column.EXECUTED, Column.DONE})

_CITED = re.compile(r"(?:docs|src|api|board|runtime|domain|infrastructure|tests|frontend)/[\w./-]+")
"""Paths a focus document's Evidence line names: what the check brief
carries as the board read them."""


def _said(delivered: bool | None) -> str:
    return "delivered" if delivered else "not delivered" if delivered is False else "unreadable"


class Focus:
    def __init__(self, live: Live, runtime: Runtime, loops: Loops, doors: Doors):
        self.live = live
        self.runtime = runtime
        self.loops = loops
        self.doors = doors
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    # ── lifecycle ──────────────────────────────────────────────────────

    async def run(self) -> None:
        self._task = asyncio.create_task(self._timer())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _timer(self) -> None:
        while not self._stop.is_set():
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), FOCUS_SECONDS)
            if self._stop.is_set():
                return
            try:
                await self.tick()
            except Exception as error:  # noqa: BLE001 — the loop never dies quietly
                log.warning(
                    "the focus loop failed (%s: %s); it runs again", type(error).__name__, error
                )

    async def tick(self) -> None:
        async with self.loops.lock:
            await asyncio.to_thread(self.tick_now)

    # ── the beat ───────────────────────────────────────────────────────

    def tick_now(self) -> None:
        """Tend every open reading, then open at most one: the check of a
        proposal first, the recheck when it is due, then the oldest card
        without a reading; the machine-readable measures are read on their
        cadence beside it."""
        sessions = [s for s in self.runtime.sessions() if not s.stale]
        for live in list(self.live.projects.values()):
            self._tend(live, sessions)
        for live in list(self.live.projects.values()):
            document = live.index.focus
            if document is None:
                continue
            ruling = self.live.store.focus_ruling(live.project.slug)
            if not is_chosen(document, ruling):
                if self._check(live, document):
                    return
                continue
            assert ruling is not None
            self._measures(live, document)
            if self._recheck(live, document, ruling):
                return
            if self._read_a_card(live, document, ruling):
                return

    # ── tending what the loop opened ───────────────────────────────────

    def _tend(self, live: LiveProject, sessions: list[Session]) -> None:
        slug = live.project.slug
        store = self.live.store
        now = clock.now()
        for opened in store.focus_calls(slug, open_only=True):
            if opened.call_id is None:
                store.end_focus_call(opened.id, now, landed=False, note="the ask never came alive")
                continue
            call = store.call(opened.call_id)
            if call is None:
                store.end_focus_call(opened.id, now, landed=False, note="the call record is gone")
                continue
            if answer_landed(call) is not None:
                self._land(live, opened, call.answer)
                continue
            verdict = self.runtime.judge_call(call, sessions)
            if verdict is None and (now - opened.opened_at).total_seconds() < ASK_CEILING_SECONDS:
                continue
            if verdict is None:
                session = next((s for s in sessions if s.session_id == call.session_id), None)
                if session is not None:
                    self.runtime.stop(session.short_id)
                words = (
                    f"the reading ran {ASK_CEILING_SECONDS / 60:.0f} min without an answer "
                    "and was stopped"
                )
            else:
                words = verdict.words
            store.end_focus_call(opened.id, now, landed=False, note=words)
            if call.ended_at is None:
                store.end_call(call.id, now, words)
            self.live.bump()

    def _land(self, live: LiveProject, opened: FocusCall, answer: str) -> None:
        """The answer landed: read it in the shape its kind asks and land it
        through the one door for that kind. A door's refusal is the
        reading's failure, with the door's words on the record."""
        slug = live.project.slug
        store = self.live.store
        now = clock.now()
        try:
            text = Path(answer).read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            store.end_focus_call(
                opened.id, now, landed=False, note=f"the answer could not be read: {error}"
            )
            return
        try:
            if opened.kind == ReadingKind.CHECK:
                check = CheckAnswer.model_validate_json(text)
                self.doors.focus_check(
                    slug,
                    verdict=check.verdict,
                    line=check.line,
                    how_known=check.how_known,
                    session_id=opened.session_id,
                    read=opened.fingerprint,
                )
            elif opened.kind == ReadingKind.CARD:
                assert opened.card_number is not None
                read = LeverageAnswer.model_validate_json(text)
                self.doors.leverage(
                    slug,
                    opened.card_number,
                    leverage=read.leverage,
                    likelihood=read.likelihood,
                    why=read.why,
                    session_id=opened.session_id,
                    read=(opened.fingerprint, opened.document_fingerprint or ""),
                )
            else:
                recheck = RecheckAnswer.model_validate_json(text)
                self.doors.focus_recheck(
                    slug,
                    outcome=recheck.outcome,
                    words=recheck.words,
                    session_id=opened.session_id,
                    read=opened.fingerprint,
                )
        except (ValidationError, ValueError) as error:
            note = f"the answer was not in the shape asked: {str(error).splitlines()[0][:200]}"
            store.end_focus_call(opened.id, now, landed=False, note=note)
        except (DoorRefused, DoorFailed) as refusal:
            store.end_focus_call(
                opened.id, now, landed=False, note=f"the door refused it: {refusal}"
            )
        finally:
            # The door ends the open record when it lands; a record still
            # open here landed nothing, and is closed above.
            call = store.call(opened.call_id) if opened.call_id is not None else None
            if call is not None and call.ended_at is None:
                store.end_call(call.id, now, "the answer landed")
            self.live.bump()

    # ── opening a reading ──────────────────────────────────────────────

    def _died(
        self, live: LiveProject, kind: ReadingKind, *, card: int | None, fingerprint: str
    ) -> int:
        """How many readings of this kind on this text ended without landing."""
        return sum(
            1
            for c in self.live.store.focus_calls(live.project.slug, kind=kind)
            if c.card_number == card
            and c.fingerprint == fingerprint
            and c.ended_at is not None
            and not c.landed
        )

    def _open(self, live: LiveProject, kind: ReadingKind) -> bool:
        return any(
            c.kind == kind for c in self.live.store.focus_calls(live.project.slug, open_only=True)
        )

    def _ask(
        self,
        live: LiveProject,
        *,
        kind: ReadingKind,
        card: int | None,
        fingerprint: str,
        document_fingerprint: str | None,
        brief: str,
        schema: type[BaseModel],
    ) -> None:
        """One reading in a fresh thread: the schema and the brief written
        beside where the answer lands, the ask through the runtime, and the
        record of the call whether or not it came alive."""
        slug, project = live.project.slug, live.project
        store = self.live.store
        stamp = uuid.uuid4().hex[:8]
        who = f"{kind.value}-{card}" if card is not None else kind.value
        folder = data_dir() / "focus" / slug
        folder.mkdir(parents=True, exist_ok=True)
        answer = folder / f"{who}-{stamp}.json"
        note = folder / f"{who}-{stamp}.brief.md"
        schema_file = codex.schema_path(str(answer))
        try:
            note.write_text(brief, encoding="utf-8")
            schema_file.write_text(
                json.dumps(schema.model_json_schema(), indent=1), encoding="utf-8"
            )
        except OSError as error:
            store.open_focus_call(
                slug,
                kind=kind,
                card_number=card,
                fingerprint=fingerprint,
                document_fingerprint=document_fingerprint,
                call_id=None,
                session_id=None,
                at=clock.now(),
                ended=f"the brief could not be written: {error}",
            )
            return
        name = f"focus-{kind.value}-{slug}" + (f"-{card}" if card is not None else "")
        called_at = clock.now()
        launch = self.runtime.ask(
            cwd=project.path,
            name=name,
            brief=brief,
            answer=str(answer),
            schema=str(schema_file),
            effort=READING_EFFORT,
        )
        if launch.verdict != LaunchVerdict.ALIVE:
            store.open_focus_call(
                slug,
                kind=kind,
                card_number=card,
                fingerprint=fingerprint,
                document_fingerprint=document_fingerprint,
                call_id=None,
                session_id=None,
                at=called_at,
                ended=f"the board could not start a reading: {launch.reason}",
            )
            self.live.bump()
            return
        session_id = launch.session.session_id if launch.session is not None else "unknown"
        record = store.record_call(
            session_id=session_id,
            slot=codex.SLOT,
            name=name,
            note=str(note),
            answer=str(answer),
            brief=brief,
            caller=project.path,
            at=called_at,
        )
        store.open_focus_call(
            slug,
            kind=kind,
            card_number=card,
            fingerprint=fingerprint,
            document_fingerprint=document_fingerprint,
            call_id=record.id,
            session_id=session_id if launch.session is not None else None,
            at=called_at,
        )
        self.live.bump()

    def _focus_text(self, live: LiveProject, document: FocusDocument) -> str:
        try:
            return (Path(live.project.path) / document.path).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as error:
            return f"(the board could not read {document.path}: {error})"

    def _intent_text(self, live: LiveProject) -> str | None:
        return self.doors._intent_text(live.project)

    # ── item 3: the check of a proposal ────────────────────────────────

    def _check(self, live: LiveProject, document: FocusDocument) -> bool:
        slug = live.project.slug
        if not document.complete:
            return False
        if self.live.store.focus_check(slug, document.fingerprint) is not None:
            return False
        if self._open(live, ReadingKind.CHECK):
            return False
        if (
            self._died(live, ReadingKind.CHECK, card=None, fingerprint=document.fingerprint)
            >= CHECK_ATTEMPTS
        ):
            return False
        sources = self.live.sources(slug)
        cited: list[str] = []
        for ref in _CITED.findall(document.evidence or ""):
            resolved: Source | None = sources.resolve(ref)
            if resolved is None:
                continue
            cited.append(
                f"--- {resolved.ref}: {resolved.note} ---\n{resolved.text or '(nothing readable)'}"
            )
        brief = check_brief(
            live.project,
            clock.now().date().isoformat(),
            focus_text=self._focus_text(live, document),
            intent_text=self._intent_text(live),
            sources=cited,
        )
        self._ask(
            live,
            kind=ReadingKind.CHECK,
            card=None,
            fingerprint=document.fingerprint,
            document_fingerprint=None,
            brief=brief,
            schema=CheckAnswer,
        )
        return True

    # ── item 6: the measures and the recheck ───────────────────────────

    def _measures(self, live: LiveProject, document: FocusDocument) -> None:
        slug = live.project.slug
        store = self.live.store
        now = clock.now()
        readings = store.measure_readings(slug, document.fingerprint)
        for side, measure in (
            (MeasureSide.OUTCOME, document.outcome),
            (MeasureSide.BOTTLENECK, document.bottleneck),
        ):
            signal = measure.signal
            if signal is None or signal.kind not in MACHINE_READ_KINDS:
                continue
            last = [r for r in readings if r.side == side]
            if not is_due(signal, last_read=last[-1].at if last else None, now=now):
                continue
            delivered, words = self.runtime.read_signal(signal, live.project.path)
            store.record_measure_reading(
                slug,
                fingerprint=document.fingerprint,
                side=side,
                at=now,
                delivered=delivered,
                words=words,
            )
            self.live.bump()

    def _recheck(self, live: LiveProject, document: FocusDocument, ruling: FocusRuling) -> bool:
        slug = live.project.slug
        store = self.live.store
        now = clock.now()
        if not recheck_due(document, store.focus_recheck(slug), now):
            return False
        if self._open(live, ReadingKind.RECHECK):
            return False
        if (
            self._died(live, ReadingKind.RECHECK, card=None, fingerprint=document.fingerprint)
            >= RECHECK_ATTEMPTS
        ):
            return False
        readings = store.measure_readings(slug, document.fingerprint)

        def lines(side: MeasureSide) -> str:
            own = [r for r in readings if r.side == side]
            if not own:
                return "(never read)"
            return "\n".join(
                f"- {r.at.isoformat(timespec='minutes')}{' (baseline)' if r.baseline else ''}: "
                f"{_said(r.delivered)} — {r.words}"
                for r in own
            )

        shipped = self._shipped_helping(live, document, ruling)
        brief = recheck_brief(
            live.project,
            now.date().isoformat(),
            focus_text=self._focus_text(live, document),
            outcome_readings=lines(MeasureSide.OUTCOME),
            bottleneck_readings=lines(MeasureSide.BOTTLENECK),
            shipped="\n".join(f"- #{c.number} {c.title}" for c in shipped) or "(none)",
        )
        self._ask(
            live,
            kind=ReadingKind.RECHECK,
            card=None,
            fingerprint=document.fingerprint,
            document_fingerprint=None,
            brief=brief,
            schema=RecheckAnswer,
        )
        return True

    def _shipped_helping(
        self, live: LiveProject, document: FocusDocument, ruling: FocusRuling
    ) -> list[Card]:
        """Every card read as helping remove the limit that shipped since the ruling."""
        slug = live.project.slug
        store = self.live.store
        readings = store.latest_leverage_readings(slug)
        placements = store.placements(slug)
        found: list[Card] = []
        for card in store.cards(slug):
            if card.folded_into is not None or card.place.column not in SHIPPED:
                continue
            reading = readings.get(card.number)
            placed = placements.get(card.number)
            if (
                reading is None
                or reading.leverage != Leverage.HELPS_REMOVE
                or reading.focus_fingerprint != document.fingerprint
                or placed is None
                or placed.at < ruling.chosen_at
            ):
                continue
            found.append(card)
        return found

    # ── item 4: every open card, one per beat ──────────────────────────

    def _read_a_card(self, live: LiveProject, document: FocusDocument, ruling: FocusRuling) -> bool:
        slug = live.project.slug
        store = self.live.store
        if self._open(live, ReadingKind.CARD):
            return False
        readings = store.latest_leverage_readings(slug)
        recheck = store.focus_recheck(slug)
        reread_since = (
            recheck.at
            if recheck is not None
            and recheck.fingerprint == document.fingerprint
            and recheck.outcome == RecheckOutcome.WORK_NOT_LINKED
            else None
        )
        candidates: list[tuple[datetime, int, Card]] = []
        for card in store.cards(slug):
            if card.folded_into is not None:
                continue
            shipped = card.place.column in SHIPPED
            if card.place.column not in READ_COLUMNS and not shipped:
                continue
            doc = document_of(card, live.index)
            if doc is None:
                continue
            if not wants_card_reading(
                readings.get(card.number),
                document.fingerprint,
                doc,
                reread_since=reread_since,
                shipped=shipped,
            ):
                continue
            if (
                self._died(
                    live, ReadingKind.CARD, card=card.number, fingerprint=document.fingerprint
                )
                >= CARD_ATTEMPTS
            ):
                continue
            candidates.append((card.born_at, card.number, card))
        if not candidates:
            return False
        _, _, card = min(candidates, key=lambda c: (c[0], c[1]))
        doc = document_of(card, live.index)
        assert doc is not None
        detail = self.live.detail(slug, card.number)
        try:
            text = (Path(live.project.path) / doc.path).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as error:
            text = f"(the board could not read {doc.path}: {error})"
        brief = leverage_brief(
            detail,
            live.project,
            clock.now().date().isoformat(),
            focus_text=self._focus_text(live, document),
            document_text=text,
        )
        self._ask(
            live,
            kind=ReadingKind.CARD,
            card=card.number,
            fingerprint=document.fingerprint,
            document_fingerprint=doc.fingerprint,
            brief=brief,
            schema=LeverageAnswer,
        )
        return True
