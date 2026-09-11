"""The team a card runs with, read from what the board, the corpus and git
already hold, and assigned before every Start (card #58).

This is the one place the facts are gathered: the store's compositions,
each card's history, the documents' `Composition:` and `Challenged:`
lines, the review records under `docs/reviews/` matched to their plans,
the live defects naming the card, the trunk's reverts and the lane's
transcripts. `board/team.py` joins them and routes; nothing is written
but the one assignment, at Start, once.
"""

import re
from datetime import datetime
from pathlib import Path

from board.assemble import document_of
from board.brief import lane_name, lane_path
from board.dial import filed_against
from board.parse import head_fields_of, plan_stem_of, review_of
from board.team import (
    CardFacts,
    Declaration,
    Defect,
    declared_in,
    observation_of,
    read_shape,
    route_for,
    shape_of,
)
from domain.card import Card
from domain.document import Document, DocumentKind, HeadField, Review
from domain.session import Session
from domain.slot import Make, Placement
from domain.team import (
    POLICY,
    Composition,
    Hand,
    Observation,
    Route,
    Shape,
    ShapeReading,
    TeamReading,
)
from infrastructure import clock
from infrastructure.live import Live
from runtime import codex
from runtime.service import Runtime

REVIEWS = "docs/reviews"


def _defect(document: Document, born: datetime | None) -> Defect:
    if born is not None:
        return Defect(path=document.path, born=born, precise=True)
    if document.date is not None:
        day = datetime.combine(document.date, datetime.min.time(), tzinfo=clock.now().tzinfo)
        return Defect(path=document.path, born=day, precise=False)
    return Defect(path=document.path, born=None, precise=False)


_OTHER_MAKE = re.compile(r"\((\w+)\)")
"""How the Start line names a make that is not Claude's — `(codex)` after
the rung (`board/lane.py::driver`): the one place a card started before
this slice says which make drove."""


def hand_of(placement: Placement) -> Hand:
    return Hand(make=placement.make, model=placement.model, slot=placement.slot)


class Team:
    def __init__(self, live: Live, runtime: Runtime):
        self.live = live
        self.runtime = runtime

    # ── reading ────────────────────────────────────────────────────────

    def _reviews(self, slug: str) -> dict[str, list[tuple[str, list[HeadField], Review]]]:
        """Every review record in the project's checkout by the stem of the
        plan it names: path, head and the parsed record."""
        root = Path(self.live.projects[slug].project.path) / REVIEWS
        found: dict[str, list[tuple[str, list[HeadField], Review]]] = {}
        if not root.is_dir():
            return found
        for path in sorted(root.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            stem = plan_stem_of(text)
            if stem is None:
                continue
            relative = f"{REVIEWS}/{path.name}"
            found.setdefault(stem, []).append(
                (relative, head_fields_of(text), review_of(text, relative))
            )
        return found

    def _facts(
        self,
        slug: str,
        card: Card,
        document: Document | None,
        reviews_by_stem: dict[str, list[tuple[str, list[HeadField], Review]]],
        born_by_stem: dict[str, datetime],
        sessions: list[Session],
    ) -> CardFacts | None:
        """The card's facts when a team was declared for it anywhere; None
        when none was, so the history is read only for the cards that can
        be observations."""
        live = self.live.projects[slug]
        store = self.live.store
        composition = store.composition(slug, card.number)
        reviews = reviews_by_stem.get(document.stem, []) if document is not None else []
        head = document.head_fields if document is not None else []
        if (
            composition is None
            and declared_in(head) is None
            and not any(declared_in(h) for _, h, _ in reviews)
        ):
            return None
        history = store.history(slug, card.number)
        name = lane_name(card.number, card.title)
        record = store.lane(slug, card.number)
        path = record.path if record is not None else lane_path(live.project.path, name)
        reverted = (
            record is not None
            and record.tip is not None
            and record.folded_at is not None
            and self.runtime.reverted(live.project.path, record.tip)
        )
        fixes_after = (
            self.runtime.fixes_after(live.project.path, record.tip, card.number)
            if record is not None and record.tip is not None and record.folded_at is not None
            else 0
        )
        hand_make = composition.route.hand.make if composition is not None else None
        if hand_make is None:
            started = next((e.detail for e in history if e.kind.value == "started"), None)
            if started is not None:
                named = _OTHER_MAKE.search(started)
                word = named.group(1) if named else None
                hand_make = Make(word) if word in {m.value for m in Make} else Make.CLAUDE
        challenger = composition.route.challenger if composition is not None else None
        return CardFacts(
            project=slug,
            card_number=card.number,
            title=card.title,
            gate=document.gate if document is not None else None,
            document_path=document.path if document is not None else None,
            document_head=head,
            review_paths=[p for p, _, _ in reviews],
            review_heads=[h for _, h, _ in reviews],
            reviews=[r for _, _, r in reviews],
            composition=composition,
            history=history,
            defects_against=[
                _defect(d, born_by_stem.get(d.stem))
                for d in filed_against(card.number, name, live.index.documents, live_only=False)
                if d.stem != (document.stem if document is not None else None)
            ],
            reverted=reverted,
            fixes_after=fixes_after,
            tokens=self.runtime.tokens(path),
            hand_make=hand_make,
            challenger_model=self._challenger_model(path, challenger, sessions),
        )

    def _challenger_model(
        self, lane_path: str, challenger: Make | None, sessions: list[Session]
    ) -> str | None:
        """The model the colleague the lane called ran on, from the call
        rows made from the lane's worktree and the one list's knowledge of
        that session (a Codex rollout names its model in its head; a
        Claude session's registry row carries it): what the stale test
        compares a challenger with. None when the lane called nobody of
        that make, or the session is gone from every registry."""
        if challenger is None:
            return None
        by_id = {s.session_id: s for s in sessions}
        for call in reversed(self.live.store.calls()):
            if call.caller != lane_path:
                continue
            session = by_id.get(call.session_id)
            if session is None:
                continue
            make = Make.CODEX if session.slot == codex.SLOT else Make.CLAUDE
            if make == challenger and session.model:
                return session.model
        return None

    def observations(self, slug: str) -> list[Observation]:
        """Every closed card that declared its team, oldest close first."""
        live = self.live.projects[slug]
        found: list[Observation] = []
        reviews = self._reviews(slug)
        cards = self.live.store.cards(slug)
        # A suggestion's card is born the moment the board sees the file,
        # so a defect's birth is known to the second when it has a card
        # and to the day of its stem when it does not (a defect archived
        # before this board read it).
        born_by_stem = {c.link.stem: c.born_at for c in cards if c.link is not None}
        sessions = self.runtime.sessions()
        for card in cards:
            document = document_of(card, live.index)
            if document is not None and document.kind == DocumentKind.SUGGESTION:
                continue
            facts = self._facts(slug, card, document, reviews, born_by_stem, sessions)
            if facts is None:
                continue
            seen = observation_of(facts)
            if seen is not None and seen.closed_at is not None:
                found.append(seen)
        return sorted(found, key=lambda o: (o.closed_at or datetime.max, o.card_number))

    def hand_now(self, slug: str) -> Hand | None:
        """The hand the rule would choose for the project now, from the
        cached rule: what the stale test compares the observations with."""
        where = self.runtime.where(None, [], cached=True)
        return hand_of(where.placement) if where.placement is not None else None

    def challenger_now(self) -> str | None:
        """The model a fresh challenger of the other make would run now:
        Codex's configured model. A Claude colleague called warm runs as
        its own session, whose model is not known before the call."""
        return codex.configured_model()

    def reading(self, slug: str, hand: Hand | None = None) -> TeamReading:
        hand = hand or self.hand_now(slug)
        observations = self.observations(slug)
        now = clock.now()
        challenger = self.challenger_now()
        return TeamReading(
            project=slug,
            policy=POLICY,
            shapes=[read_shape(shape, observations, hand, now, challenger) for shape in Shape],
            assigned=self.live.store.compositions(slug),
            read_at=now,
        )

    # ── routing ────────────────────────────────────────────────────────

    def route(self, slug: str, number: int, placement: Placement) -> Route:
        """The team for this card's Start, from the shape's reading and the
        plan's pin; raises `board.team.Unexecutable` when the pin cannot
        run."""
        live = self.live.projects[slug]
        card = self.live.card(slug, number)
        document = document_of(card, live.index)
        gate = document.gate if document is not None else None
        if gate is None:
            raise ValueError(f"#{number} has no effort gate, so its shape cannot be read")
        hand = hand_of(placement)
        shape = shape_of(gate)
        challenger = self.challenger_now()
        reading: ShapeReading = read_shape(
            shape, self.observations(slug), hand, clock.now(), challenger
        )
        pinned: Declaration | None = declared_in(document.head_fields) if document else None
        routed = route_for(reading, hand, number, pinned)
        if routed.challenger is Make.CODEX:
            routed = routed.model_copy(update={"challenger_model": challenger})
        return routed

    def assign(self, slug: str, number: int, route: Route) -> Composition:
        """Write the team, before the launch: durable from this moment, so
        a board that dies between the launch and its record still has the
        team the brief carried (the independent review of card #58)."""
        return self.live.store.record_composition(slug, number, route, clock.now())

    def unassign(self, slug: str, number: int) -> None:
        """A launch that died assigned nothing: the row written before it
        goes, so the next Start reads the evidence again. The one caller
        is the dead-launch path of the Start door."""
        self.live.store.forget_composition(slug, number)

    def reassign(self, slug: str, number: int, route: Route) -> Composition:
        """The launch landed on another make than the one the team was
        routed for, seconds after the row was written and before any
        work: the row is replaced by the team routed for the hand that
        drives. The one caller is the Start door, which says so on the
        card's history."""
        self.live.store.forget_composition(slug, number)
        return self.live.store.record_composition(slug, number, route, clock.now())
