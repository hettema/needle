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
    declared_in,
    observation_of,
    read_shape,
    route_for,
    shape_of,
)
from domain.card import Card
from domain.document import Document, DocumentKind, HeadField, Review
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
from runtime.service import Runtime

REVIEWS = "docs/reviews"
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
        hand_make = composition.route.hand.make if composition is not None else None
        if hand_make is None:
            started = next((e.detail for e in history if e.kind.value == "started"), None)
            if started is not None:
                named = _OTHER_MAKE.search(started)
                word = named.group(1) if named else None
                hand_make = Make(word) if word in {m.value for m in Make} else Make.CLAUDE
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
                (d.path, datetime.combine(d.date, datetime.min.time(), tzinfo=clock.now().tzinfo))
                if d.date is not None
                else (d.path, None)
                for d in filed_against(card.number, name, live.index.documents)
                if d.stem != (document.stem if document is not None else None)
            ],
            reverted=reverted,
            tokens=self.runtime.tokens(path),
            hand_make=hand_make,
        )

    def observations(self, slug: str) -> list[Observation]:
        """Every closed card that declared its team, oldest close first."""
        live = self.live.projects[slug]
        found: list[Observation] = []
        reviews = self._reviews(slug)
        for card in self.live.store.cards(slug):
            document = document_of(card, live.index)
            if document is not None and document.kind == DocumentKind.SUGGESTION:
                continue
            facts = self._facts(slug, card, document, reviews)
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

    def reading(self, slug: str, hand: Hand | None = None) -> TeamReading:
        hand = hand or self.hand_now(slug)
        observations = self.observations(slug)
        return TeamReading(
            project=slug,
            policy=POLICY,
            shapes=[read_shape(shape, observations, hand) for shape in Shape],
            assigned=self.live.store.compositions(slug),
            read_at=clock.now(),
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
        reading: ShapeReading = read_shape(shape, self.observations(slug), hand)
        pinned: Declaration | None = declared_in(document.head_fields) if document else None
        return route_for(reading, hand, number, pinned)

    def assign(self, slug: str, number: int, route: Route) -> tuple[Composition, bool]:
        """Write the team once: the composition the card already has wins,
        and the second value says whether this call wrote it."""
        held = self.live.store.composition(slug, number)
        if held is not None:
            return held, False
        return self.live.store.record_composition(slug, number, route, clock.now()), True
