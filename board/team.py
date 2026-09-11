"""The reader that joins what a closed card left behind into a reading per
kind of work, and the router that applies it before a Start (card #58).

Pure: every fact comes in as data the api layer read from the corpus, the
store and git, so a reading can be reproduced from those facts alone and
changing any of them changes the reading. Nothing here is a scorecard; a
tally is recomputed from its observations on every read.

Quality decides first — corrections before build and defects that escaped
after close — and time and tokens break a tie between compositions that do
not differ on quality (plan item 3). Every conclusion says its sample and
its confounds, so an incomplete reading is reported as exploring and never
as a winner.
"""

import re
from datetime import datetime, timedelta

from pydantic import BaseModel

from domain.audit import AuditEntry, AuditKind
from domain.column import Column
from domain.document import HeadField, Review
from domain.gate import Gate
from domain.slot import Make, rung_words
from domain.team import (
    CORRECTING_TRIALS_TO_EARN,
    ESCAPE_DAYS,
    EXPLORE_EVERY,
    TRIALS_TO_JUDGE,
    Challenge,
    Composition,
    Conclusion,
    Hand,
    Observation,
    Route,
    Shape,
    ShapeReading,
    Tally,
)

COMPOSITION_LINE = "composition"
"""The head line that declares a team in a document: `**Composition:**` on
a plan (#59's, 2026-09-05, was the first) or on a review record (#54's,
`Composition, for card 58's reader`). Before this card it was the only
declaration; on a live plan it pins the card's team, with the reason after
the dash (plan item 4: a card-specific constraint overrides the router and
says why)."""

CHALLENGED_LINE = "challenged"
"""The head line a lane writes on its plan once the challenge before build
has landed: `**Challenged:** … <N> material corrections before build …`.
#59's plan wrote it first ("Twelve material corrections before build"),
and the reader counts from it, so the fact lives in the plan and nowhere
else."""

_COUNT_WORDS = {
    "zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}  # fmt: skip
_CORRECTIONS = re.compile(
    r"\b(\d+|" + "|".join(_COUNT_WORDS) + r")\s+material\s+corrections?\b", re.I
)
_RINGS = {"feature": "inside", "seam": "adjacent", "boundary": "outside"}
_CLOSED = "closed by the session"
"""What the close's move says on the card's history (`api/doors.py::close`),
after the store's own `Moved A → B — ` prefix."""

BOOTSTRAP: dict[Shape, Challenge] = {
    Shape.JUDGMENT: Challenge.DIFFERENT_MAKE,
    Shape.BOUNDED: Challenge.ALONE,
    Shape.READING: Challenge.ALONE,
}
"""Where each shape explores from while its evidence is incomplete (the
plan's Loop): judgment from #54's and #59's different-make observations,
bounded work with one accountable hand. After the bootstrap composition
has its trials, exploration takes the least-sampled one."""

ORDER = [Challenge.ALONE, Challenge.SAME_MAKE, Challenge.DIFFERENT_MAKE]


def shape_of(gate: Gate) -> Shape:
    """A card's shape from its effort gate: the one fact every started card
    has, so no shape is ever guessed."""
    return Shape.JUDGMENT if gate in (Gate.HIGH, Gate.XHIGH) else Shape.BOUNDED


class Declaration(BaseModel):
    """A team as a document's head declares it."""

    challenge: Challenge
    why: str
    """The words after the challenge: a pin's reason, or the declaration's
    account of who did what."""


def declared_in(fields: list[HeadField]) -> Declaration | None:
    """The `Composition:` line's team, when the head has one the reader
    can name; None when there is no line or its words name no
    composition."""
    for field in fields:
        if not field.key.lower().startswith(COMPOSITION_LINE):
            continue
        value = field.value.strip()
        lowered = value.lower()
        challenge = next(
            (c for c in (Challenge.DIFFERENT_MAKE, Challenge.SAME_MAKE) if c.value in lowered),
            Challenge.ALONE if re.search(r"\balone\b", lowered) else None,
        )
        if challenge is None and len({m.value for m in Make if m.value in lowered}) > 1:
            # #54's record declared its team for this reader before the
            # words existed: "one Claude lane … one Codex thread". Two
            # makes named on the line is the different-make challenge.
            challenge = Challenge.DIFFERENT_MAKE
        if challenge is None:
            return None
        _, dash, rest = value.partition("—")
        if not dash:
            _, dash, rest = value.partition(" - ")
        return Declaration(challenge=challenge, why=rest.strip() if dash else "")
    return None


def corrections_in(fields: list[HeadField]) -> int | None:
    """Material corrections before build, from the `Challenged:` line;
    None when no line says."""
    for field in fields:
        if field.key.lower() != CHALLENGED_LINE:
            continue
        match = _CORRECTIONS.search(field.value)
        if match is None:
            return None
        word = match.group(1).lower()
        return int(word) if word.isdigit() else _COUNT_WORDS[word]
    return None


def rings_of(reviews: list[Review]) -> tuple[int, int, int, int]:
    """Findings in all, and by ring: inside (feature), adjacent (seam),
    outside (boundary), from each disposition's class."""
    counts = {"inside": 0, "adjacent": 0, "outside": 0}
    total = 0
    for review in reviews:
        for disposition in review.dispositions:
            total += 1
            ring = _RINGS.get(disposition.finding_class or "")
            if ring:
                counts[ring] += 1
    return total, counts["inside"], counts["adjacent"], counts["outside"]


def started_at(history: list[AuditEntry]) -> datetime | None:
    starts = [
        e.at
        for e in history
        if e.kind == AuditKind.STARTED and not e.detail.startswith("Start failed")
    ]
    return min(starts) if starts else None


def closed_at(history: list[AuditEntry]) -> datetime | None:
    """When the card's close moved it on: the first move into Executed or
    Done that the close wrote, after the first Start."""
    began = started_at(history)
    if began is None:
        return None
    closes = [
        e.at
        for e in history
        if e.kind == AuditKind.MOVED
        and e.at >= began
        and e.to_place is not None
        and e.to_place.column in (Column.EXECUTED, Column.DONE)
        and _CLOSED in e.detail
    ]
    return min(closes) if closes else None


def stops_in(history: list[AuditEntry]) -> int:
    began = started_at(history)
    return sum(
        1 for e in history if e.kind == AuditKind.STOPPED and began is not None and e.at >= began
    )


def escapes_of(defects: list[tuple[str, datetime | None]], closed: datetime | None) -> int:
    """Live defects filed against the card within ESCAPE_DAYS of its close,
    by each suggestion's own date. A defect with no date counts: the
    reader cannot say it was late."""
    if closed is None:
        return 0
    window = closed + timedelta(days=ESCAPE_DAYS)
    return sum(
        1 for _, born in defects if born is None or closed.date() <= born.date() <= window.date()
    )


class CardFacts(BaseModel):
    """Everything the reader needs about one card, as the api layer read
    it. Each field names its source so the observation can."""

    project: str
    card_number: int
    title: str
    gate: Gate | None
    document_path: str | None
    document_head: list[HeadField]
    review_paths: list[str]
    review_heads: list[list[HeadField]]
    reviews: list[Review]
    composition: Composition | None
    history: list[AuditEntry]
    defects_against: list[tuple[str, datetime | None]]
    """Each live defect naming the card, by path and its date."""
    reverted: bool
    tokens: int | None
    hand_make: Make | None
    """The make that drove, when the board knows it from the lane's
    session; the composition's hand when it has one."""


def observation_of(facts: CardFacts) -> Observation | None:
    """A closed card's observation; None for a card that declared no team
    before its work, or never started — nothing to attribute."""
    began = started_at(facts.history)
    if began is None or facts.gate is None:
        return None
    sources: list[str] = ["history"]
    hand_model: str | None = None
    challenger_model: str | None = None
    if facts.composition is not None:
        route = facts.composition.route
        challenge, shape = route.challenge, route.shape
        hand_make: Make | None = route.hand.make
        hand_model = route.hand.model
        declared_in_words = "the board's record at Start"
    else:
        declaration = declared_in(facts.document_head)
        where = facts.document_path
        if declaration is None:
            for path, head in zip(facts.review_paths, facts.review_heads, strict=True):
                declaration = declared_in(head)
                if declaration is not None:
                    where = path
                    break
        if declaration is None:
            return None
        challenge, shape = declaration.challenge, shape_of(facts.gate)
        hand_make = facts.hand_make
        declared_in_words = f"{where}, its Composition line"
        sources.append(where or "")
    closed = closed_at(facts.history)
    findings, inside, adjacent, outside = rings_of(facts.reviews)
    sources.extend(facts.review_paths)
    sources.extend(path for path, _ in facts.defects_against)
    if facts.reverted:
        sources.append("git")
    if facts.tokens is not None:
        sources.append("transcripts")
    corrections = corrections_in(facts.document_head)
    if corrections is not None and facts.document_path:
        sources.append(f"{facts.document_path}, its Challenged line")
    return Observation(
        project=facts.project,
        card_number=facts.card_number,
        title=facts.title,
        shape=shape,
        challenge=challenge,
        hand_make=hand_make,
        hand_model=hand_model,
        challenger_model=challenger_model,
        declared_in=declared_in_words,
        corrections=corrections,
        findings=findings,
        inside=inside,
        adjacent=adjacent,
        outside=outside,
        escapes=escapes_of(facts.defects_against, closed),
        stops=stops_in(facts.history),
        reverted=facts.reverted,
        hours=(closed - began).total_seconds() / 3600 if closed is not None else None,
        tokens=facts.tokens,
        closed_at=closed,
        sources=[s for s in dict.fromkeys(sources) if s],
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def tally_of(challenge: Challenge, observations: list[Observation]) -> Tally:
    own = [o for o in observations if o.challenge == challenge]
    hours = _mean([o.hours for o in own if o.hours is not None])
    tokens = _mean([float(o.tokens) for o in own if o.tokens is not None])
    return Tally(
        challenge=challenge,
        trials=len(own),
        correcting=sum(1 for o in own if (o.corrections or 0) > 0),
        corrections=sum(o.corrections or 0 for o in own),
        unrecorded=sum(1 for o in own if o.corrections is None and challenge != Challenge.ALONE),
        escapes=sum(o.escapes for o in own),
        escaping=sum(1 for o in own if o.escapes > 0),
        findings=sum(o.findings for o in own),
        stops=sum(o.stops for o in own),
        reverts=sum(1 for o in own if o.reverted),
        hours=hours,
        tokens=int(tokens) if tokens is not None else None,
    )


def _earned(tally: Tally, observations: list[Observation]) -> bool:
    """The plan's threshold: a challenge earns the lead when at least two
    of its first three trials produced a material correction before build
    and no trial escaped a defect within fourteen days."""
    if tally.challenge == Challenge.ALONE or tally.trials < TRIALS_TO_JUDGE:
        return False
    first = sorted(
        (o for o in observations if o.challenge == tally.challenge),
        key=lambda o: (o.closed_at is None, o.closed_at or datetime.max),
    )[:TRIALS_TO_JUDGE]
    correcting = sum(1 for o in first if (o.corrections or 0) > 0)
    return correcting >= CORRECTING_TRIALS_TO_EARN and tally.escaping == 0


def _quality(tally: Tally) -> tuple[float, int]:
    """Fewer escaping trials per trial first, then more correcting ones."""
    return (tally.escaping / tally.trials if tally.trials else 0.0, -tally.correcting)


def _efficiency(tally: Tally) -> tuple[float, float]:
    return (
        tally.hours if tally.hours is not None else float("inf"),
        float(tally.tokens) if tally.tokens is not None else float("inf"),
    )


def _least_sampled(shape: Shape, tallies: list[Tally], among: list[Challenge]) -> Challenge:
    """The next composition to explore: the shape's bootstrap while it is
    under-sampled, else the least-sampled, ties in ORDER."""
    by = {t.challenge: t for t in tallies}
    boot = BOOTSTRAP[shape]
    if boot in among and by[boot].trials < TRIALS_TO_JUDGE:
        return boot
    return min(among, key=lambda c: (by[c].trials, ORDER.index(c)))


def read_shape(
    shape: Shape, observations: list[Observation], hand_now: Hand | None
) -> ShapeReading:
    """What the evidence says for one shape. The stale test compares each
    observation's hand model with the hand the rule names now, when both
    are named; an unnamed model on either side is no evidence of a change
    (the rule names no model for a top rung today, card #63)."""
    own = [o for o in observations if o.shape == shape]
    tallies = [tally_of(c, own) for c in ORDER]
    confounds: list[str] = []
    hands = {o.hand_make.value for o in own if o.hand_make is not None}
    if len(hands) > 1:
        confounds.append(f"the hands differ across trials ({', '.join(sorted(hands))})")
    unrecorded = sum(t.unrecorded for t in tallies)
    if unrecorded:
        confounds.append(
            f"{unrecorded} trial{'s' if unrecorded != 1 else ''} under a challenge left no "
            "Challenged line, so its corrections are unread, not zero"
        )
    if 0 < len(own) < TRIALS_TO_JUDGE:
        confounds.append(f"a sample of {len(own)}")
    stale = [
        o
        for o in own
        if hand_now is not None
        and hand_now.model is not None
        and o.hand_model is not None
        and o.hand_model != hand_now.model
    ]
    if stale:
        old = sorted({o.hand_model for o in stale if o.hand_model})
        return ShapeReading(
            shape=shape,
            observations=own,
            tallies=tallies,
            conclusion=Conclusion.STALE,
            leader=None,
            why=(
                f"{len(stale)} of {len(own)} trials ran on {', '.join(old)} and the hand now "
                f"is {hand_now.model}; a model changed, so the shape explores again"
                if hand_now is not None
                else ""
            ),
            confounds=confounds,
        )
    under = [t for t in tallies if t.trials < TRIALS_TO_JUDGE]
    if under:
        sample = ", ".join(f"{t.challenge.value} {t.trials}" for t in tallies)
        return ShapeReading(
            shape=shape,
            observations=own,
            tallies=tallies,
            conclusion=Conclusion.EXPLORING,
            leader=None,
            why=(
                f"fewer than {TRIALS_TO_JUDGE} trials under "
                f"{', '.join(t.challenge.value for t in under)} ({sample})"
            ),
            confounds=confounds,
        )
    earned = [t for t in tallies if _earned(t, own)]
    if earned:
        ranked = sorted(earned, key=lambda t: (_quality(t), _efficiency(t)))
        if (
            len(ranked) > 1
            and _quality(ranked[0]) == _quality(ranked[1])
            and _efficiency(ranked[0]) == _efficiency(ranked[1])
        ):
            return ShapeReading(
                shape=shape,
                observations=own,
                tallies=tallies,
                conclusion=Conclusion.TIED,
                leader=None,
                why=(
                    f"{ranked[0].challenge.value} and {ranked[1].challenge.value} both met "
                    "the threshold and differ on neither quality nor time"
                ),
                confounds=confounds,
            )
        lead = ranked[0]
        return ShapeReading(
            shape=shape,
            observations=own,
            tallies=tallies,
            conclusion=Conclusion.EARNED,
            leader=lead.challenge,
            why=(
                f"{lead.challenge.value} corrected before build in {lead.correcting} of its "
                f"first {TRIALS_TO_JUDGE} trials and escaped no defect within {ESCAPE_DAYS} days"
            ),
            confounds=confounds,
        )
    ranked = sorted(tallies, key=lambda t: (_quality(t), _efficiency(t)))
    best, runner = ranked[0], ranked[1]
    if _quality(best) == _quality(runner) and _efficiency(best) == _efficiency(runner):
        return ShapeReading(
            shape=shape,
            observations=own,
            tallies=tallies,
            conclusion=Conclusion.TIED,
            leader=None,
            why=(
                f"no composition met the threshold, and {best.challenge.value} and "
                f"{runner.challenge.value} differ on neither quality nor time"
            ),
            confounds=confounds,
        )
    tie_broken = _quality(best) == _quality(runner)
    return ShapeReading(
        shape=shape,
        observations=own,
        tallies=tallies,
        conclusion=Conclusion.BEST_QUALITY,
        leader=best.challenge,
        why=(
            f"no composition met the threshold; {best.challenge.value} leads on "
            + (
                f"time ({best.hours:.1f} h against {runner.hours:.1f} h), quality being equal"
                if tie_broken and best.hours is not None and runner.hours is not None
                else f"quality ({best.escaping} of {best.trials} trials escaped a defect, "
                f"{best.correcting} corrected before build)"
            )
        ),
        confounds=confounds,
    )


def challenger_of(challenge: Challenge, hand: Make) -> Make | None:
    if challenge == Challenge.ALONE:
        return None
    if challenge == Challenge.SAME_MAKE:
        return hand
    return next(m for m in Make if m != hand)


def executable(hand: Make, shape: Shape) -> list[Challenge]:
    """The compositions the runtime can execute for this hand: alone
    always; a same-make challenge whenever the hand's make can be called
    (both makes can, plan 57 and #73); a different-make challenge when
    another make has a launcher. A reading seat holds one reader (#59)."""
    if shape == Shape.READING:
        return [Challenge.ALONE]
    able = [Challenge.ALONE, Challenge.SAME_MAKE]
    if any(m != hand for m in Make):
        able.append(Challenge.DIFFERENT_MAKE)
    return able


class Unexecutable(Exception):
    """The card pins a team the runtime cannot execute; Start refuses it."""


def route_for(
    reading: ShapeReading,
    hand: Hand,
    card_number: int,
    pinned: Declaration | None,
) -> Route:
    """The team for this card from the shape's reading: a pin first, then
    the leader, one card in four exploring past it, exploring when nothing
    leads, and unavailable when only one composition can run."""
    shape = reading.shape
    able = executable(hand.make, shape)
    links = [f"#{o.card_number}" for o in reading.observations]

    def route(challenge: Challenge, conclusion: Conclusion, why: str) -> Route:
        return Route(
            shape=shape,
            challenge=challenge,
            hand=hand,
            challenger=challenger_of(challenge, hand.make),
            conclusion=conclusion,
            why=why,
            observations=links,
        )

    if pinned is not None:
        if pinned.challenge not in able:
            raise Unexecutable(
                f"the plan pins {pinned.challenge.value}, which cannot run for a "
                f"{hand.make.value} hand on a {shape.value} card; it can run "
                + ", ".join(c.value for c in able)
            )
        return route(
            pinned.challenge,
            Conclusion.PINNED,
            f"the plan pins it: {pinned.why}"
            if pinned.why
            else "the plan pins it, giving no reason",
        )
    if len(able) == 1:
        return route(
            able[0],
            Conclusion.UNAVAILABLE,
            f"only {able[0].value} can run for a {shape.value} card",
        )
    if reading.leader is not None and reading.leader in able:
        if card_number % EXPLORE_EVERY == 0:
            others = [c for c in able if c != reading.leader]
            chosen = _least_sampled(shape, reading.tallies, others)
            return route(
                chosen,
                Conclusion.EXPLORING,
                f"one card in {EXPLORE_EVERY} explores past the leader ({reading.leader.value}); "
                f"#{card_number} is one",
            )
        return route(reading.leader, reading.conclusion, reading.why)
    chosen = _least_sampled(shape, reading.tallies, able)
    # A stale or tied reading keeps its word on the route, so the card says
    # why the shape is exploring and not merely that it is.
    conclusion = (
        reading.conclusion
        if reading.conclusion in (Conclusion.STALE, Conclusion.TIED)
        else Conclusion.EXPLORING
    )
    return route(chosen, conclusion, f"exploring {chosen.value}: {reading.why}")


def challenge_words(challenge: Challenge) -> str:
    return {
        Challenge.ALONE: "the accountable hand alone",
        Challenge.SAME_MAKE: "a same-make challenge",
        Challenge.DIFFERENT_MAKE: "a different-make challenge",
    }[challenge]


def team_words(route: Route) -> str:
    """The team in one line, as every face says it: the card's history at
    Start, the open card, `needle team`. Built once so no reader has to
    decide how to name a hand or a challenger."""
    hand = f"{route.hand.make.value}, {rung_words(route.hand.model, route.hand.slot)}"
    who = (
        f"{route.challenger.value} challenges"
        if route.challenger is not None
        else "nobody challenges"
    )
    return (
        f"{challenge_words(route.challenge)} — the hand is {hand}; {who}; "
        f"{route.conclusion.value}: {route.why}"
    )
