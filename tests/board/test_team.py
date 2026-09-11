"""The team's reader and router (card #58): one reading joins facts that
already exist, quality decides before time, incomplete evidence explores
and says so, and every route links to its observations.
"""

from datetime import UTC, datetime, timedelta

import pytest

from board.parse import head_fields_of, review_of
from board.team import (
    CardFacts,
    Declaration,
    Defect,
    Unexecutable,
    closed_at,
    corrections_in,
    declared_in,
    escapes_of,
    observation_of,
    read_shape,
    rings_of,
    route_for,
    shape_of,
)
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Place
from domain.column import Column
from domain.gate import Gate
from domain.slot import Make
from domain.team import (
    POLICY,
    Challenge,
    Composition,
    Conclusion,
    Hand,
    Observation,
    Route,
    Shape,
)

T0 = datetime(2026, 9, 1, tzinfo=UTC)
NOW = T0 + timedelta(days=400)
"""Long after every fixture trial's fourteen-day window."""
CLAUDE = Hand(make=Make.CLAUDE, model="fable", slot="eduard")


def observation(
    number: int,
    challenge: Challenge,
    *,
    shape: Shape = Shape.JUDGMENT,
    corrections: int | None = None,
    escapes: int = 0,
    hours: float | None = 4.0,
    tokens: int | None = None,
    hand_model: str | None = "fable",
    closed: datetime | None = None,
    challenger_model: str | None = None,
) -> Observation:
    return Observation(
        project="proj",
        card_number=number,
        title=f"card {number}",
        shape=shape,
        challenge=challenge,
        hand_make=Make.CLAUDE,
        hand_model=hand_model,
        challenger_model=challenger_model,
        declared_in="the board's record at Start",
        corrections=corrections,
        findings=0,
        inside=0,
        adjacent=0,
        outside=0,
        escapes=escapes,
        stops=0,
        send_backs=0,
        reverted=False,
        fixes_after=0,
        hours=hours,
        tokens=tokens,
        closed_at=closed or (T0 + timedelta(days=number)),
        sources=["history"],
    )


def trials(challenge: Challenge, n: int, start: int, **kw) -> list[Observation]:
    return [observation(start + i, challenge, **kw) for i in range(n)]


# ── the reading per shape ──────────────────────────────────────────────


def test_incomplete_evidence_explores_and_says_the_sample():
    reading = read_shape(
        Shape.JUDGMENT, trials(Challenge.DIFFERENT_MAKE, 2, 1, corrections=3), CLAUDE, NOW
    )
    assert reading.conclusion == Conclusion.EXPLORING and reading.leader is None
    assert "fewer than 3 trials" in reading.why and "different-make 2" in reading.why
    assert "a sample of 2" in reading.confounds


def full_sample(**different) -> list[Observation]:
    return (
        trials(Challenge.ALONE, 3, 1)
        + trials(Challenge.SAME_MAKE, 3, 11, corrections=0)
        + trials(Challenge.DIFFERENT_MAKE, 3, 21, **different)
    )


def test_a_challenge_earns_the_lead_by_corrections_and_no_escape():
    reading = read_shape(Shape.JUDGMENT, full_sample(corrections=2), CLAUDE, NOW)
    assert reading.conclusion == Conclusion.EARNED
    assert reading.leader == Challenge.DIFFERENT_MAKE
    assert "corrected before build in 3 of its first 3 trials" in reading.why


def test_one_escaped_defect_denies_the_lead_however_many_corrections():
    sample = full_sample(corrections=5)
    sample[-1] = observation(23, Challenge.DIFFERENT_MAKE, corrections=5, escapes=1)
    sample[0] = observation(1, Challenge.ALONE, hours=3.0)
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert reading.conclusion == Conclusion.BEST_QUALITY
    # Quality first: the two compositions with no escape tie on escapes;
    # same-make made no corrections and alone can make none, so the tie
    # is broken by time, never by the escaping composition's corrections.
    assert reading.leader == Challenge.ALONE
    assert "no composition met the threshold" in reading.why


def test_time_breaks_only_a_quality_tie():
    sample = (
        trials(Challenge.ALONE, 3, 1, hours=2.0)
        + trials(Challenge.SAME_MAKE, 3, 11, corrections=0, hours=8.0)
        + trials(Challenge.DIFFERENT_MAKE, 3, 21, corrections=0, hours=1.0)
    )
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert reading.conclusion == Conclusion.BEST_QUALITY
    assert reading.leader == Challenge.DIFFERENT_MAKE
    assert "time (1.0 h against 2.0 h), quality being equal" in reading.why
    # A slower composition with a correction outranks the fast one that made none.
    sample[-1] = observation(23, Challenge.DIFFERENT_MAKE, corrections=0, hours=1.0)
    sample[5] = observation(13, Challenge.SAME_MAKE, corrections=1, hours=8.0)
    slower = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert slower.leader == Challenge.SAME_MAKE and "quality" in slower.why


def test_compositions_that_differ_on_nothing_are_tied():
    sample = (
        trials(Challenge.ALONE, 3, 1, hours=2.0)
        + trials(Challenge.SAME_MAKE, 3, 11, corrections=0, hours=2.0)
        + trials(Challenge.DIFFERENT_MAKE, 3, 21, corrections=0, hours=2.0)
    )
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert reading.conclusion == Conclusion.TIED and reading.leader is None


def test_a_changed_model_sets_the_old_trials_aside_and_a_fresh_cohort_judges_again():
    now = Hand(make=Make.CLAUDE, model="fable-6", slot="eduard")
    reading = read_shape(Shape.JUDGMENT, full_sample(corrections=2), now, NOW)
    assert reading.conclusion == Conclusion.STALE and reading.leader is None
    assert reading.why.startswith("a model changed: 9 of 9 trials are set aside")
    assert any("9 trials ran on fable, which is not a model" in c for c in reading.confounds)
    assert len(reading.observations) == 9, "the record is kept whole"
    # A rung with no model named is no evidence of a change.
    unnamed = Hand(make=Make.CLAUDE, model=None, slot="eduard")
    assert read_shape(Shape.JUDGMENT, full_sample(corrections=2), unnamed, NOW).conclusion == (
        Conclusion.EARNED
    )
    # A complete fresh cohort beside the old one is judged on its own.
    fresh = (
        trials(Challenge.ALONE, 3, 31, hand_model="fable-6")
        + trials(Challenge.SAME_MAKE, 3, 41, corrections=0, hand_model="fable-6")
        + trials(Challenge.DIFFERENT_MAKE, 3, 51, corrections=2, hand_model="fable-6")
    )
    again = read_shape(Shape.JUDGMENT, full_sample(corrections=2) + fresh, now, NOW)
    assert again.conclusion == Conclusion.EARNED and again.leader == Challenge.DIFFERENT_MAKE
    assert len(again.observations) == 18
    # A challenger's model that changed counts the same way.
    challenged = [
        o.model_copy(update={"challenger_model": "gpt-5.6"}) for o in full_sample(corrections=2)
    ]
    assert read_shape(Shape.JUDGMENT, challenged, CLAUDE, NOW, "gpt-6").conclusion == (
        Conclusion.STALE
    )
    assert read_shape(Shape.JUDGMENT, challenged, CLAUDE, NOW, "gpt-5.6").conclusion == (
        Conclusion.EARNED
    )


def test_an_unrecorded_round_is_a_confound_not_a_zero_and_blocks_the_judgment():
    sample = full_sample(corrections=None, hours=1.0)
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert any("3 trials under a challenge left no Challenged line" in c for c in reading.confounds)
    by = {t.challenge: t for t in reading.tallies}
    assert by[Challenge.DIFFERENT_MAKE].unrecorded == 3
    assert by[Challenge.DIFFERENT_MAKE].correcting == 0
    # Unread quality never wins on time: the shape is not judged until it is read.
    assert reading.conclusion == Conclusion.EXPLORING and reading.leader is None
    assert reading.why == (
        "the sample is full (alone 3, same-make 3, different-make 3) but not yet judged — "
        "different-make: 3 with corrections unread"
    )


def test_a_trial_inside_its_escape_window_is_not_yet_judged():
    sample = full_sample(corrections=2)
    fresh = T0 + timedelta(days=40)
    sample[-1] = observation(23, Challenge.DIFFERENT_MAKE, corrections=2, closed=fresh)
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, fresh + timedelta(days=1))
    assert reading.conclusion == Conclusion.EXPLORING
    assert "different-make: 1 still inside the window" in reading.why
    assert "1 trial still inside the 14-day window" in reading.confounds[0]
    matured = read_shape(Shape.JUDGMENT, sample, CLAUDE, fresh + timedelta(days=14))
    assert matured.conclusion == Conclusion.EARNED


def test_quality_compares_shares_not_counts():
    sample = (
        trials(Challenge.ALONE, 3, 1, hours=1.0)
        + trials(Challenge.SAME_MAKE, 30, 100, corrections=0, hours=100.0)
        + trials(Challenge.DIFFERENT_MAKE, 3, 21, corrections=0, hours=1.0)
    )
    # Fifteen of thirty same-make trials corrected, none of the first three,
    # so nothing is earned; one of three different-make trials corrected.
    for i in range(10, 25):
        sample[3 + i] = observation(100 + i, Challenge.SAME_MAKE, corrections=1, hours=100.0)
    sample[-1] = observation(23, Challenge.DIFFERENT_MAKE, corrections=1, hours=1.0)
    reading = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    assert reading.conclusion == Conclusion.BEST_QUALITY
    assert reading.leader == Challenge.SAME_MAKE, "15 of 30 outranks 1 of 3 on the share"
    assert "of its first 3 trials" not in reading.why


def test_a_shape_reads_only_its_own_observations():
    sample = full_sample(corrections=2) + trials(Challenge.ALONE, 1, 31, shape=Shape.BOUNDED)
    judgment = read_shape(Shape.JUDGMENT, sample, CLAUDE, NOW)
    bounded = read_shape(Shape.BOUNDED, sample, CLAUDE, NOW)
    assert len(judgment.observations) == 9 and len(bounded.observations) == 1
    assert bounded.conclusion == Conclusion.EXPLORING


# ── the router ─────────────────────────────────────────────────────────


def test_an_earned_leader_is_applied_and_one_card_in_four_explores_past_it():
    reading = read_shape(Shape.JUDGMENT, full_sample(corrections=2), CLAUDE, NOW)
    applied = route_for(reading, CLAUDE, 5, None)
    assert applied.challenge == Challenge.DIFFERENT_MAKE
    assert applied.conclusion == Conclusion.EARNED and applied.challenger == Make.CODEX
    assert applied.observations == [f"#{n}" for n in (1, 2, 3, 11, 12, 13, 21, 22, 23)]
    assert applied.policy == POLICY
    explored = route_for(reading, CLAUDE, 8, None)
    assert explored.conclusion == Conclusion.EXPLORING
    assert explored.challenge != Challenge.DIFFERENT_MAKE
    assert "one card in 4 explores past the leader (different-make); #8 is one" in explored.why


def test_bootstrap_explores_from_the_shapes_starting_composition():
    judgment = route_for(read_shape(Shape.JUDGMENT, [], CLAUDE, NOW), CLAUDE, 1, None)
    assert judgment.challenge == Challenge.DIFFERENT_MAKE
    assert judgment.conclusion == Conclusion.EXPLORING and judgment.observations == []
    bounded = route_for(read_shape(Shape.BOUNDED, [], CLAUDE, NOW), CLAUDE, 1, None)
    assert bounded.challenge == Challenge.ALONE and bounded.challenger is None
    # Once the bootstrap has its trials, the least-sampled is next.
    sampled = trials(Challenge.DIFFERENT_MAKE, 3, 1, corrections=1)
    later = route_for(read_shape(Shape.JUDGMENT, sampled, CLAUDE, NOW), CLAUDE, 1, None)
    assert later.challenge == Challenge.ALONE and later.conclusion == Conclusion.EXPLORING


def test_a_stale_or_tied_reading_keeps_its_word_on_the_route():
    now = Hand(make=Make.CLAUDE, model="fable-6", slot="eduard")
    stale = route_for(
        read_shape(Shape.JUDGMENT, full_sample(corrections=2), now, NOW), now, 1, None
    )
    assert stale.conclusion == Conclusion.STALE and "a model changed" in stale.why


def test_a_reading_seat_has_one_composition_and_says_so():
    reading = read_shape(Shape.READING, [], CLAUDE, NOW)
    applied = route_for(reading, CLAUDE, 1, None)
    assert applied.conclusion == Conclusion.UNAVAILABLE and applied.challenge == Challenge.ALONE
    assert applied.why == "only alone can run for a reading card"


def test_a_pinned_team_overrides_with_its_reason_and_an_unexecutable_pin_is_refused():
    reading = read_shape(Shape.JUDGMENT, full_sample(corrections=2), CLAUDE, NOW)
    pin = Declaration(challenge=Challenge.ALONE, why="the change touches the owner's credentials")
    pinned = route_for(reading, CLAUDE, 5, pin)
    assert pinned.challenge == Challenge.ALONE and pinned.conclusion == Conclusion.PINNED
    assert pinned.why == "the plan pins it: the change touches the owner's credentials"
    seat = read_shape(Shape.READING, [], CLAUDE, NOW)
    with pytest.raises(Unexecutable, match="pins different-make, which cannot run"):
        route_for(seat, CLAUDE, 5, Declaration(challenge=Challenge.DIFFERENT_MAKE, why="x"))
    with pytest.raises(Unexecutable, match="pins same-make and gives no reason"):
        route_for(reading, CLAUDE, 5, Declaration(challenge=Challenge.SAME_MAKE, why=""))


def test_a_codex_hand_is_challenged_by_claude_under_different_make():
    codex = Hand(make=Make.CODEX, model="gpt-5.6", slot="codex")
    applied = route_for(read_shape(Shape.JUDGMENT, [], codex, NOW), codex, 1, None)
    assert applied.challenge == Challenge.DIFFERENT_MAKE and applied.challenger == Make.CLAUDE


# ── the facts each observation is read from ────────────────────────────


def test_the_composition_line_is_read_from_a_plan_and_a_record_and_pins_with_a_reason():
    plan = head_fields_of(
        "# T\n\n**Composition:** different-make challenge — accountable hand Claude Fable 5.1 "
        "wrote the plan; Sol (Codex gpt-5.6) challenged it before any lane started.\n"
    )
    assert declared_in(plan) == Declaration(
        challenge=Challenge.DIFFERENT_MAKE,
        why="accountable hand Claude Fable 5.1 wrote the plan; Sol (Codex gpt-5.6) challenged "
        "it before any lane started.",
    )
    record = head_fields_of(
        "# Review\n\n**Plan:** x\n**Composition, for card 58's reader:** one Claude lane "
        "doing the judgment; one Codex thread called four times.\n"
    )
    assert declared_in(record) == Declaration(challenge=Challenge.DIFFERENT_MAKE, why=""), (
        "two makes named on the line is #54's different-make challenge"
    )
    one_make = head_fields_of("# T\n\n**Composition:** one Claude lane, nothing else.\n")
    assert declared_in(one_make) is None, "a line naming no composition names none"
    same = head_fields_of("# T\n\n**Composition:** same-make challenge\n")
    assert declared_in(same) == Declaration(challenge=Challenge.SAME_MAKE, why="")
    alone = head_fields_of("# T\n\n**Composition:** alone — touches his credentials\n")
    assert declared_in(alone) == Declaration(
        challenge=Challenge.ALONE, why="touches his credentials"
    )
    assert declared_in(head_fields_of("# T\n\n**Status:** PENDING\n")) is None


def test_corrections_are_counted_from_the_challenged_line_in_words_or_digits():
    twelve = head_fields_of(
        "# T\n\n**Challenged:** 2026-09-05, by Sol. Twelve material corrections before build, "
        "zero confirmations.\n"
    )
    assert corrections_in(twelve) == 12
    assert corrections_in(head_fields_of("# T\n\n**Challenged:** 1 material correction\n")) == 1
    assert corrections_in(head_fields_of("# T\n\n**Challenged:** no material corrections\n")) == 0
    assert (
        corrections_in(head_fields_of("# T\n\n**Challenged:** by Sol, nothing counted\n")) is None
    )
    assert corrections_in(head_fields_of("# T\n\n**Status:** PENDING\n")) is None


def test_findings_are_counted_by_ring_from_each_dispositions_class():
    text = (
        "# Review — x\n\n**Plan:** docs/plans/done/p.md\n**Findings:** 4\n\n## Dispositions\n\n"
        "1. [feature] a — FIXED in abc\n2. [seam] b — FIXED in abc\n"
        "3. [boundary] c — filed as docs/slice-suggestions/x.md\n4. [record] d — FIXED in abc\n"
    )
    review = review_of(text, "docs/reviews/x.md")
    assert rings_of([review]) == (4, 1, 1, 1)


def entry(number: int, kind: AuditKind, at: datetime, detail: str, to: Column | None = None):
    return AuditEntry(
        id=number,
        at=at,
        actor=Actor.SESSION,
        kind=kind,
        card_number=1,
        from_place=None,
        to_place=Place(column=to, group=None, position=0) if to else None,
        detail=detail,
    )


def history(started: datetime, closed: datetime | None) -> list[AuditEntry]:
    rows = [entry(1, AuditKind.STARTED, started, "Started abcd, fable on eduard")]
    if closed is not None:
        rows.append(
            entry(
                2,
                AuditKind.MOVED,
                closed,
                "Moved Executing → Executed — closed by the session: DELIVERED and WATCH written",
                Column.EXECUTED,
            )
        )
    return rows


def test_escapes_are_defects_born_after_the_close_and_within_fourteen_days():
    closed = T0 + timedelta(days=10, hours=12)
    defects = [
        Defect(path="d1", born=T0 + timedelta(days=11), precise=True),
        Defect(path="d2", born=T0 + timedelta(days=24, hours=12), precise=True),
        Defect(path="d3", born=T0 + timedelta(days=25), precise=True),
        Defect(path="d4", born=T0 + timedelta(days=2), precise=True),
        Defect(path="d5", born=None, precise=False),
        # Born to the second, an hour before the close: filed in the review, no escape.
        Defect(path="d6", born=T0 + timedelta(days=10, hours=11), precise=True),
        # Born on the day of the close, known only to the day: counts, since the
        # reader cannot place it before or after.
        Defect(path="d7", born=T0 + timedelta(days=10), precise=False),
    ]
    assert escapes_of(defects, closed) == 4
    assert escapes_of(defects, None) == 0


def facts(**kw) -> CardFacts:
    base = dict(
        project="proj",
        card_number=7,
        title="a card",
        gate=Gate.HIGH,
        document_path="docs/plans/done/p.md",
        document_head=head_fields_of(
            "# T\n\n**Composition:** different-make challenge — Sol challenged\n"
            "**Challenged:** two material corrections before build\n"
        ),
        review_paths=[],
        review_heads=[],
        reviews=[],
        composition=None,
        history=history(T0, T0 + timedelta(hours=6)),
        defects_against=[
            Defect(path="docs/slice-suggestions/d.md", born=T0 + timedelta(days=1), precise=True)
        ],
        reverted=False,
        fixes_after=2,
        tokens=1200,
        hand_make=Make.CLAUDE,
        challenger_model="gpt-5.6",
    )
    base.update(kw)
    return CardFacts(**base)


def test_an_observation_is_joined_from_the_facts_and_names_each_source():
    seen = observation_of(facts())
    assert seen is not None
    assert seen.challenge == Challenge.DIFFERENT_MAKE and seen.shape == Shape.JUDGMENT
    assert seen.corrections == 2 and seen.escapes == 1 and seen.hours == 6.0
    assert seen.tokens == 1200 and seen.declared_in == "docs/plans/done/p.md, its Composition line"
    assert seen.fixes_after == 2 and seen.challenger_model == "gpt-5.6" and seen.send_backs == 0
    assert seen.sources == [
        "history",
        "docs/plans/done/p.md",
        "docs/slice-suggestions/d.md",
        "git",
        "transcripts",
        "calls",
        "docs/plans/done/p.md, its Challenged line",
    ]


def test_send_backs_are_the_owners_moves_out_of_executed_after_the_close():
    rows = history(T0, T0 + timedelta(hours=6))
    back = AuditEntry(
        id=9,
        at=T0 + timedelta(days=1),
        actor=Actor.OWNER,
        kind=AuditKind.MOVED,
        card_number=1,
        from_place=Place(column=Column.EXECUTED, group=None, position=0),
        to_place=Place(column=Column.UP_NEXT, group=None, position=0),
        detail="Moved Executed → Up next",
    )
    seen = observation_of(facts(history=[*rows, back]))
    assert seen is not None and seen.send_backs == 1


def test_changing_or_deleting_a_source_fact_changes_the_observation():
    without_defect = observation_of(facts(defects_against=[]))
    assert without_defect is not None and without_defect.escapes == 0
    unchallenged = observation_of(
        facts(document_head=head_fields_of("# T\n\n**Composition:** different-make challenge\n"))
    )
    assert unchallenged is not None and unchallenged.corrections is None
    assert observation_of(facts(document_head=head_fields_of("# T\n\n**Status:** DONE\n"))) is None
    assert observation_of(facts(history=[])) is None, "a card never started is no observation"


def test_the_stored_team_outranks_the_document_and_is_the_shape_it_was_assigned():
    route = Route(
        shape=Shape.BOUNDED,
        challenge=Challenge.ALONE,
        hand=Hand(make=Make.CODEX, model="gpt-5.6", slot="codex"),
        challenger=None,
        conclusion=Conclusion.EXPLORING,
        why="exploring",
        observations=[],
    )
    held = Composition(project="proj", card_number=7, route=route, assigned_at=T0)
    seen = observation_of(facts(composition=held))
    assert seen is not None
    assert seen.challenge == Challenge.ALONE and seen.shape == Shape.BOUNDED
    assert seen.hand_make == Make.CODEX and seen.hand_model == "gpt-5.6"
    assert seen.declared_in == "the board's record at Start"


def test_the_close_is_the_first_move_the_close_wrote_after_the_start():
    rows = history(T0, T0 + timedelta(hours=6))
    rows.insert(
        1, entry(3, AuditKind.MOVED, T0 + timedelta(hours=1), "the owner moved it", Column.EXECUTED)
    )
    assert closed_at(rows) == T0 + timedelta(hours=6)
    assert closed_at(history(T0, None)) is None
    assert observation_of(facts(history=history(T0, None))).hours is None


def test_shape_is_read_from_the_gate():
    assert shape_of(Gate.LOW) == shape_of(Gate.MEDIUM) == Shape.BOUNDED
    assert shape_of(Gate.HIGH) == shape_of(Gate.XHIGH) == Shape.JUDGMENT
