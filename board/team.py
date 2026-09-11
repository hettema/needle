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
from domain.card import Actor
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


def send_backs_in(history: list[AuditEntry], closed: datetime | None) -> int:
    """The owner's moves of the card out of Executed or Done after its
    close: the work sent back."""
    if closed is None:
        return 0
    return sum(
        1
        for e in history
        if e.kind == AuditKind.MOVED
        and e.actor == Actor.OWNER
        and e.at > closed
        and e.from_place is not None
        and e.from_place.column in (Column.EXECUTED, Column.DONE)
        and e.to_place is not None
        and e.to_place.column not in (Column.EXECUTED, Column.DONE)
    )


class Defect(BaseModel):
    """One defect filed against a card, as the api layer found it: its
    path, and when it was born — the board's own birth of its card when it
    has one, else the day in its stem."""

    path: str
    born: datetime | None
    precise: bool
    """Whether `born` is the board's moment or a stem's day."""


def escapes_of(defects: list[Defect], closed: datetime | None) -> int:
    """Defects filed against the card after its close and within
    ESCAPE_DAYS of it, by each defect's birth. A defect born on the day of
    the close whose birth is known only to the day cannot be placed before
    or after the close, and counts: the reader cannot say it was earlier.
    A defect with no date counts for the same reason."""
    if closed is None:
        return 0
    window = closed + timedelta(days=ESCAPE_DAYS)
    counted = 0
    for defect in defects:
        if defect.born is None:
            counted += 1
        elif defect.precise:
            counted += closed < defect.born <= window
        else:
            counted += closed.date() <= defect.born.date() <= window.date()
    return counted


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
    defects_against: list[Defect]
    """Every defect naming the card or its lane, live or since archived:
    a defect fixed later was still filed."""
    reverted: bool
    fixes_after: int
    """Trunk commits naming the card within a week of the lane's tip."""
    tokens: int | None
    hand_make: Make | None
    """The make that drove, when the board knows it from the lane's
    session; the composition's hand when it has one."""
    challenger_model: str | None = None
    """The model of the colleague the lane called, from the call rows and
    the runtime's knowledge of that session; None when unread."""


def observation_of(facts: CardFacts) -> Observation | None:
    """A closed card's observation; None for a card that declared no team
    before its work, or never started — nothing to attribute."""
    began = started_at(facts.history)
    if began is None or facts.gate is None:
        return None
    sources: list[str] = ["history"]
    hand_model: str | None = None
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
    sources.extend(d.path for d in facts.defects_against)
    if facts.reverted or facts.fixes_after:
        sources.append("git")
    if facts.tokens is not None:
        sources.append("transcripts")
    if facts.challenger_model is not None:
        sources.append("calls")
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
        challenger_model=facts.challenger_model,
        declared_in=declared_in_words,
        corrections=corrections,
        findings=findings,
        inside=inside,
        adjacent=adjacent,
        outside=outside,
        escapes=escapes_of(facts.defects_against, closed),
        stops=stops_in(facts.history),
        send_backs=send_backs_in(facts.history, closed),
        reverted=facts.reverted,
        fixes_after=facts.fixes_after,
        hours=(closed - began).total_seconds() / 3600 if closed is not None else None,
        tokens=facts.tokens,
        closed_at=closed,
        sources=[s for s in dict.fromkeys(sources) if s],
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def matured(observation: Observation, now: datetime) -> bool:
    """Whether the card's fourteen-day escape window has passed: before
    that its zero escapes are a fact about the calendar, not the work."""
    return (
        observation.closed_at is not None
        and observation.closed_at + timedelta(days=ESCAPE_DAYS) <= now
    )


def tally_of(challenge: Challenge, observations: list[Observation], now: datetime) -> Tally:
    own = [o for o in observations if o.challenge == challenge]
    hours = _mean([o.hours for o in own if o.hours is not None])
    tokens = _mean([float(o.tokens) for o in own if o.tokens is not None])
    return Tally(
        challenge=challenge,
        trials=len(own),
        maturing=sum(1 for o in own if not matured(o, now)),
        correcting=sum(1 for o in own if (o.corrections or 0) > 0),
        corrections=sum(o.corrections or 0 for o in own),
        unrecorded=sum(1 for o in own if o.corrections is None and challenge != Challenge.ALONE),
        escapes=sum(o.escapes for o in own),
        escaping=sum(1 for o in own if o.escapes > 0),
        findings=sum(o.findings for o in own),
        stops=sum(o.stops for o in own),
        send_backs=sum(o.send_backs for o in own),
        reverts=sum(1 for o in own if o.reverted),
        fixes_after=sum(o.fixes_after for o in own),
        hours=hours,
        tokens=int(tokens) if tokens is not None else None,
    )


def _first(challenge: Challenge, observations: list[Observation]) -> list[Observation]:
    """A composition's first TRIALS_TO_JUDGE trials, by close."""
    return sorted(
        (o for o in observations if o.challenge == challenge),
        key=lambda o: (o.closed_at is None, o.closed_at or datetime.max, o.card_number),
    )[:TRIALS_TO_JUDGE]


def _correcting_first(challenge: Challenge, observations: list[Observation]) -> int:
    return sum(1 for o in _first(challenge, observations) if (o.corrections or 0) > 0)


def _earned(tally: Tally, observations: list[Observation]) -> bool:
    """The plan's threshold: a challenge earns the lead when at least two
    of its first three trials produced a material correction before build
    and no trial escaped a defect within fourteen days."""
    if tally.challenge == Challenge.ALONE or tally.trials < TRIALS_TO_JUDGE:
        return False
    return (
        _correcting_first(tally.challenge, observations) >= CORRECTING_TRIALS_TO_EARN
        and tally.escaping == 0
    )


def _quality(tally: Tally) -> tuple[float, float]:
    """The share of trials that escaped a defect first, fewer better, then
    the share that corrected before build, more better — shares, so a
    composition sampled more often is not read as better for it."""
    if not tally.trials:
        return (0.0, 0.0)
    return (tally.escaping / tally.trials, -tally.correcting / tally.trials)


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


def _stale(observation: Observation, hand_now: Hand | None, challenger_now: str | None) -> bool:
    """Whether a model that took part is not the one that would take part
    now, when both are named: the hand's against the rule's answer, the
    challenger's against what the call would run. An unnamed model on
    either side is no evidence of a change (the rule names no model for a
    top rung today, card #63)."""
    hand_changed = (
        hand_now is not None
        and hand_now.model is not None
        and observation.hand_model is not None
        and observation.hand_model != hand_now.model
    )
    challenger_changed = (
        challenger_now is not None
        and observation.challenger_model is not None
        and observation.challenger_model != challenger_now
    )
    return hand_changed or challenger_changed


def read_shape(
    shape: Shape,
    observations: list[Observation],
    hand_now: Hand | None,
    now: datetime,
    challenger_now: str | None = None,
) -> ShapeReading:
    """What the evidence says for one shape. Stale observations — a model
    that took part is not the model now — stay in the record and are set
    aside: the fresh cohort is judged on its own, and while it is short
    the shape reads `stale` and explores. A composition is judged only
    when its trials are past their escape window and, for a challenge,
    when every trial's corrections are read; otherwise it is exploring,
    with the reason."""
    all_own = [o for o in observations if o.shape == shape]
    stale = [o for o in all_own if _stale(o, hand_now, challenger_now)]
    own = [o for o in all_own if o not in stale]
    tallies = [tally_of(c, own, now) for c in ORDER]
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
    maturing = sum(t.maturing for t in tallies)
    if maturing:
        confounds.append(
            f"{maturing} trial{'s' if maturing != 1 else ''} still inside the "
            f"{ESCAPE_DAYS}-day window, so its escapes are not yet a fact"
        )
    if 0 < len(own) < TRIALS_TO_JUDGE:
        confounds.append(f"a sample of {len(own)}")
    if stale:
        old = sorted({m for o in stale for m in (o.hand_model, o.challenger_model) if m})
        confounds.append(
            f"{len(stale)} trial{'s' if len(stale) != 1 else ''} ran on {', '.join(old)}, "
            "which is not a model that would take part now; set aside, kept in the record"
        )

    def reading(conclusion: Conclusion, leader: Challenge | None, why: str) -> ShapeReading:
        return ShapeReading(
            shape=shape,
            observations=all_own,
            tallies=tallies,
            conclusion=conclusion,
            leader=leader,
            why=why,
            confounds=confounds,
        )

    sample = ", ".join(f"{t.challenge.value} {t.trials}" for t in tallies)
    under = [t for t in tallies if t.trials < TRIALS_TO_JUDGE]
    if under:
        why = (
            f"fewer than {TRIALS_TO_JUDGE} trials under "
            f"{', '.join(t.challenge.value for t in under)} ({sample})"
        )
        if stale:
            return reading(
                Conclusion.STALE,
                None,
                f"a model changed: {len(stale)} of {len(all_own)} trials are set aside, and "
                f"the fresh trials are {why}",
            )
        return reading(Conclusion.EXPLORING, None, why)
    unjudged = [t for t in tallies if t.maturing or t.unrecorded]
    if unjudged:
        reasons = "; ".join(
            f"{t.challenge.value}: "
            + ", ".join(
                part
                for part in (
                    f"{t.maturing} still inside the window" if t.maturing else "",
                    f"{t.unrecorded} with corrections unread" if t.unrecorded else "",
                )
                if part
            )
            for t in unjudged
        )
        return reading(
            Conclusion.EXPLORING,
            None,
            f"the sample is full ({sample}) but not yet judged — {reasons}",
        )
    earned = [t for t in tallies if _earned(t, own)]
    if earned:
        ranked = sorted(earned, key=lambda t: (_quality(t), _efficiency(t)))
        if (
            len(ranked) > 1
            and _quality(ranked[0]) == _quality(ranked[1])
            and _efficiency(ranked[0]) == _efficiency(ranked[1])
        ):
            return reading(
                Conclusion.TIED,
                None,
                f"{ranked[0].challenge.value} and {ranked[1].challenge.value} both met "
                "the threshold and differ on neither quality nor time",
            )
        lead = ranked[0]
        return reading(
            Conclusion.EARNED,
            lead.challenge,
            f"{lead.challenge.value} corrected before build in "
            f"{_correcting_first(lead.challenge, own)} of its first {TRIALS_TO_JUDGE} trials "
            f"and escaped no defect within {ESCAPE_DAYS} days",
        )
    ranked = sorted(tallies, key=lambda t: (_quality(t), _efficiency(t)))
    best, runner = ranked[0], ranked[1]
    if _quality(best) == _quality(runner) and _efficiency(best) == _efficiency(runner):
        return reading(
            Conclusion.TIED,
            None,
            f"no composition met the threshold, and {best.challenge.value} and "
            f"{runner.challenge.value} differ on neither quality nor time",
        )
    tie_broken = _quality(best) == _quality(runner)
    return reading(
        Conclusion.BEST_QUALITY,
        best.challenge,
        "no composition met the threshold; "
        f"{best.challenge.value} leads on "
        + (
            f"time ({best.hours:.1f} h against {runner.hours:.1f} h), quality being equal"
            if tie_broken and best.hours is not None and runner.hours is not None
            else f"quality ({best.escaping} of {best.trials} trials escaped a defect, "
            f"{best.correcting} corrected before build)"
        ),
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
    another make has a launcher. A reading seat holds one reader (#59).
    Whether a colleague of the make can be reached when the lane calls,
    hours after this Start, is the call's fact and not this one's: the
    brief says what a lane does when the call is refused."""
    if shape == Shape.READING:
        return [Challenge.ALONE]
    able = [Challenge.ALONE, Challenge.SAME_MAKE]
    if any(m != hand for m in Make):
        able.append(Challenge.DIFFERENT_MAKE)
    return able


class Unexecutable(Exception):
    """The card pins a team the runtime cannot execute, or pins one with
    no reason; Start refuses it with the words."""


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
        if not pinned.why:
            # A pin is a safety or intent constraint and says why (plan
            # item 4); convenience does not override the evidence, and a
            # line with no reason cannot be told from convenience.
            raise Unexecutable(
                f"the plan pins {pinned.challenge.value} and gives no reason; write one after "
                "the dash on its Composition line, or remove the line and let the evidence choose"
            )
        return route(pinned.challenge, Conclusion.PINNED, f"the plan pins it: {pinned.why}")
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
