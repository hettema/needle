"""A card parked on the owner, read cold (card #82): when it is read, what
on it is a commitment, where each result sends it, and what the move is
re-tested against — pure over the card's rows and history."""

from datetime import timedelta

from board.parked import (
    WAITINGS_PER_CARD,
    commitments_of,
    now_refused,
    owner_parked,
    parked_doubt,
    parked_words,
    record_answered_missing,
    record_fingerprint,
    waiting_refused,
    wants_parked_reading,
    where_after_parked_reading,
)
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Place
from domain.column import Column
from domain.document import DocumentKind, SuggestionKind
from domain.evidence import Evidence
from domain.row import Row, RowKind
from domain.triage import Commitment, Ground, Source, Triage, TriageResult
from tests.board.test_assemble import doc
from tests.board.test_evidence import placed, reading
from tests.board.test_lane import NOW, card, facts, lane_for, session

PARKED = Place(column=Column.DECISION_MOMENT, group=None, position=0)


def entry(kind: AuditKind, detail: str, *, hours_ago: float, actor: Actor = Actor.SESSION):
    return AuditEntry(
        id=1,
        at=NOW - timedelta(hours=hours_ago),
        actor=actor,
        kind=kind,
        card_number=7,
        from_place=None,
        to_place=None,
        detail=detail,
    )


def read(result: TriageResult, *, hours_ago: float, words: str = "words") -> Triage:
    return Triage(
        id=1,
        project="proj",
        card_number=7,
        at=NOW - timedelta(hours=hours_ago),
        actor=Actor.SESSION,
        result=result,
        words=words,
        decision="d1",
        parent=None,
        direction=None,
        source_ref="docs/plans/p.md" if result == TriageResult.NOW else None,
        source_path="docs/plans/p.md" if result == TriageResult.NOW else None,
        source_fingerprint="abc" if result == TriageResult.NOW else None,
        document_fingerprint="rec",
        session_id="s1",
        ground=Ground.PARKED,
    )


# ── when a parked card is read ──────────────────────────────────────────


def test_a_parked_card_is_read_once_per_park_and_again_on_the_owners_answer():
    parked = card(column=Column.DECISION_MOMENT)
    park = placed(Actor.MACHINE, Column.DECISION_MOMENT, evidence=Evidence.LANE_ENDED)
    assert wants_parked_reading(parked, park, None, None, None)
    after = read(TriageResult.HIS, hours_ago=0.5)
    assert not wants_parked_reading(parked, park, after, None, None), "read since the park"
    before = read(TriageResult.HIS, hours_ago=2)
    assert wants_parked_reading(parked, park, before, None, None), "parked again since"
    answered = entry(AuditKind.ANSWERED, "Ruled: the left one", hours_ago=0.25, actor=Actor.OWNER)
    assert wants_parked_reading(parked, park, after, answered, None), "his answer re-reads"
    earlier_answer = entry(AuditKind.ANSWERED, "Ruled", hours_ago=0.75, actor=Actor.OWNER)
    assert not wants_parked_reading(parked, park, after, earlier_answer, None)


def test_only_a_live_session_a_fold_or_another_column_holds_the_reading_back():
    parked = card(column=Column.DECISION_MOMENT)
    park = placed(Actor.IMPORT, Column.DECISION_MOMENT, kind=AuditKind.BORN)
    assert not wants_parked_reading(card(column=Column.EXECUTED), park, None, None, None)
    folded = parked.model_copy(update={"folded_into": 3})
    assert not wants_parked_reading(folded, park, None, None, None)
    live = lane_for(parked, facts(sessions=[session(state="working")]))
    assert not wants_parked_reading(parked, park, None, None, live)
    ended = lane_for(parked, facts(worktrees={}))
    assert wants_parked_reading(parked, park, None, None, ended), (
        "an ended lane with its copy of the code on disk is read: the reading runs in the "
        "project's own checkout"
    )


def test_the_owners_own_park_is_read_and_never_moved():
    his = placed(Actor.OWNER, Column.DECISION_MOMENT)
    assert wants_parked_reading(card(column=Column.DECISION_MOMENT), his, None, None, None)
    assert owner_parked(his)
    assert not owner_parked(placed(Actor.MACHINE, Column.DECISION_MOMENT))
    assert not owner_parked(placed(Actor.OWNER, Column.PLANNED))
    assert not owner_parked(placed(Actor.IMPORT, Column.DECISION_MOMENT, kind=AuditKind.BORN))


# ── the commitments on a card ───────────────────────────────────────────


def test_a_delivered_with_no_readable_signal_is_a_commitment():
    rows = [
        Row(kind=RowKind.DELIVERED, text="The read-out, side by side."),
        Row(kind=RowKind.WATCH, text="Your ruling on the five forks."),
    ]
    found = commitments_of(card(rows=rows), [], None)
    assert len(found) == 1
    assert found[0].row == RowKind.DELIVERED and found[0].transferable
    assert found[0].words.startswith("a DELIVERED with no signal the board can read")
    assert "The read-out, side by side." in found[0].words


def test_a_watch_is_accounted_for_only_when_read_as_delivered():
    rows = [
        Row(kind=RowKind.DELIVERED, text="Shipped."),
        Row(kind=RowKind.WATCH, text="the bank confirms — owner by 2026-12-01"),
    ]
    unread = commitments_of(card(rows=rows), [], None)
    assert [c.words for c in unread] == ["a WATCH nobody has read yet: the bank confirms"]
    assert unread[0].row == RowKind.WATCH and unread[0].transferable
    failed = commitments_of(card(rows=rows), [], reading(False, "no confirmation"))
    assert failed[0].words.startswith("a WATCH whose last reading did not say delivered")
    assert commitments_of(card(rows=rows), [], reading(True)) == []


def test_a_question_in_his_words_is_a_commitment_until_he_answers_after_it():
    rows = [Row(kind=RowKind.ASK, text="Which account?")]
    asked = entry(AuditKind.ROW, "ASK Which account?", hours_ago=2)
    [question] = commitments_of(card(rows=rows), [asked], None)
    assert question.words == "a question in your words with no answer (ASK): Which account?"
    assert question.row == RowKind.ASK and not question.transferable, (
        "a WATCH cannot carry a question in his words"
    )
    answered = entry(AuditKind.ANSWERED, "Ruled: the new one", hours_ago=1, actor=Actor.OWNER)
    assert commitments_of(card(rows=rows), [answered, asked], None) == []
    stale_answer = entry(AuditKind.ANSWERED, "Ruled", hours_ago=3, actor=Actor.OWNER)
    assert commitments_of(card(rows=rows), [asked, stale_answer], None), (
        "an answer from before the question was written does not answer it"
    )
    imported = commitments_of(card(rows=rows), [stale_answer], None)
    assert imported == [], "a row with no writing on the history is answered by any answer"


def test_a_ruling_nobody_ruled_on_is_a_commitment_and_a_ruled_one_is_not():
    ruling = [Row(kind=RowKind.RULING, text="Which of the two?")]
    [open_ruling] = commitments_of(card(rows=ruling), [], None)
    assert open_ruling.words == "a RULING nobody has ruled on: Which of the two?"
    assert open_ruling.row == RowKind.RULING and not open_ruling.transferable
    ruled = ruling + [Row(kind=RowKind.RULED, text="The left.")]
    assert commitments_of(card(rows=ruled), [], None) == []


def test_age_shipped_code_and_an_absent_signal_are_not_read_at_all():
    """A card with no rows has nothing unaccounted for, however old and
    however much code it shipped: the rule cannot see either."""
    old = card(rows=[], archived=True)
    assert commitments_of(old, [], None) == []


# ── the refusals ────────────────────────────────────────────────────────


def test_now_needs_a_live_document():
    assert now_refused(None) is not None and "has none" in now_refused(None)
    archived = doc("p", archived=True)
    assert "is archived" in (now_refused(archived) or "")
    assert now_refused(doc("p")) is None


def test_waiting_is_refused_on_a_failed_signal_a_question_and_a_third_time():
    rows = [Row(kind=RowKind.WATCH, text="the bank confirms — owner by 2026-08-01")]
    parked = card(rows=rows)
    same = "the bank confirms — owner by 2026-12-01"

    def refused(target, words, *, last=None, earlier=(), commitments=()):
        return waiting_refused(
            target, words, last=last, earlier=list(earlier), commitments=list(commitments), now=NOW
        )

    assert refused(parked, "not a signal")
    failed = refused(parked, same, last=reading(False))
    assert failed is not None and "already read as not delivered" in failed
    overdue = refused(parked, same)
    assert overdue is not None and "past its due date" in overdue
    other = "the council minutes name the account — owner by 2026-12-01"
    assert refused(parked, other, last=reading(False)) is None
    twice = [read(TriageResult.WAITING, hours_ago=h) for h in (48, 24)]
    assert len(twice) == WAITINGS_PER_CARD
    third = refused(card(), other, earlier=twice)
    assert third is not None and "third `waiting` is refused" in third
    # A question in his words cannot be carried by a WATCH (review finding 4).
    question = Commitment(row=RowKind.ASK, words="a question: which?", transferable=False)
    held = refused(card(), other, commitments=[question])
    assert held is not None and "cannot carry a question" in held and "which?" in held
    watch = Commitment(row=RowKind.WATCH, words="a WATCH nobody has read", transferable=True)
    assert refused(card(), other, commitments=[watch]) is None, "a watch transfers"


# ── where each result sends the card ────────────────────────────────────


def test_each_result_lands_where_the_plan_says():
    plan = doc("p")
    defect = doc("d", kind=DocumentKind.SUGGESTION).model_copy(
        update={"suggestion_kind": SuggestionKind.DEFECT, "path": "docs/slice-suggestions/d.md"}
    )
    source = Source(
        ref="docs/plans/p.md", path="docs/plans/p.md", text="x", fingerprint="f", note="n"
    )
    now = where_after_parked_reading(
        TriageResult.NOW, "the plan says so", source=source, document=plan, replaced_watch=None
    )
    assert now.column == Column.PLANNED and now.evidence == Evidence.RECORD_ANSWERED
    assert "source `docs/plans/p.md`" in now.reason
    home = where_after_parked_reading(
        TriageResult.NOW, "w", source=source, document=defect, replaced_watch=None
    )
    assert home.column == Column.DEFECTS, "a suggestion goes home, never to a rank"
    waiting = where_after_parked_reading(
        TriageResult.WAITING,
        "x — owner by 2026-12-01",
        source=None,
        document=None,
        replaced_watch="Your ruling on the five forks.",
    )
    assert waiting.column == Column.EXECUTED
    assert "the WATCH it replaced: Your ruling on the five forks." in waiting.reason
    stale = where_after_parked_reading(
        TriageResult.STALE, "the season ended", source=None, document=None, replaced_watch=None
    )
    assert stale.column == Column.DONE and "over" in stale.reason
    his = where_after_parked_reading(
        TriageResult.HIS, "which?", source=None, document=None, replaced_watch=None
    )
    assert his.column is None and his.evidence is None and "yours" in his.reason


# ── the re-test, and the doubt on the face ──────────────────────────────


def test_a_move_on_a_reading_is_retested_per_result():
    assert record_answered_missing(None, card(), source_fingerprint=None, commitments=[])
    now = read(TriageResult.NOW, hours_ago=1)
    assert record_answered_missing(now, card(), source_fingerprint="abc", commitments=[]) is None
    assert "has changed" in (
        record_answered_missing(now, card(), source_fingerprint="zzz", commitments=[]) or ""
    )
    assert "is gone" in (
        record_answered_missing(now, card(), source_fingerprint=None, commitments=[]) or ""
    )
    waiting = read(
        TriageResult.WAITING, hours_ago=1, words="the bank confirms — owner by 2026-12-01"
    )
    watched = card(rows=[Row(kind=RowKind.WATCH, text="the bank confirms — owner by 2026-12-01")])
    assert (
        record_answered_missing(waiting, watched, source_fingerprint=None, commitments=[]) is None
    )
    bare = card(rows=[])
    assert "names no signal" in (
        record_answered_missing(waiting, bare, source_fingerprint=None, commitments=[]) or ""
    )
    other = card(rows=[Row(kind=RowKind.WATCH, text="something else — owner by 2026-12-01")])
    assert "watches something other" in (
        record_answered_missing(waiting, other, source_fingerprint=None, commitments=[]) or ""
    )
    stale = read(TriageResult.STALE, hours_ago=1)
    assert record_answered_missing(stale, card(), source_fingerprint=None, commitments=[]) is None
    ask = Commitment(row=RowKind.ASK, words="an ASK", transferable=False)
    assert "unaccounted for: an ASK" in (
        record_answered_missing(stale, card(), source_fingerprint=None, commitments=[ask]) or ""
    )


def test_the_doubt_names_the_commitment_after_a_refused_stale():
    stale = read(TriageResult.STALE, hours_ago=1, words="the season ended")
    delivered = Commitment(
        row=RowKind.DELIVERED, words="a DELIVERED with no signal: x", transferable=True
    )
    assert parked_doubt(stale, [delivered]) == (
        "a cold reading called it over (the season ended), but this is unaccounted for: "
        "a DELIVERED with no signal: x"
    )
    assert parked_doubt(stale, []) is None
    assert parked_doubt(read(TriageResult.HIS, hours_ago=1), [delivered]) is None
    mark = read(TriageResult.STALE, hours_ago=1).model_copy(update={"ground": Ground.MARK})
    assert parked_doubt(mark, [delivered]) is None


def test_the_face_never_says_you_parked_it_on_a_card_the_machine_parked():
    """Review finding 3: after a refused `stale` whose commitment has since
    been settled, the words say so and wait for his move — never that he
    parked it, unless he did."""
    stale = read(TriageResult.STALE, hours_ago=1, words="the season ended")
    settled = parked_words(stale, doubt=None, parked_by_owner=False, being_read=False)
    assert settled is not None and settled.startswith(
        "a cold reading of the record found it over: the season ended, and the board refused"
    )
    assert "settled since" in settled and "you parked" not in settled.lower()
    his_park = parked_words(stale, doubt=None, parked_by_owner=True, being_read=False)
    assert his_park is not None and his_park.endswith(
        "You parked it yourself, so it stays until you move it"
    )
    doubt = parked_words(stale, doubt="the doubt", parked_by_owner=True, being_read=False)
    assert doubt == "the doubt"
    line = parked_words(
        read(TriageResult.HIS, hours_ago=1, words="which?"),
        doubt=None,
        parked_by_owner=False,
        being_read=False,
    )
    assert line == "a cold reading of the record found the decision is yours: which?"
    assert parked_words(None, doubt=None, parked_by_owner=False, being_read=False) is None
    reading_now = parked_words(None, doubt=None, parked_by_owner=False, being_read=True)
    assert reading_now is not None and reading_now.startswith(
        "a cold reading of the record is judging now"
    )
    moved_nothing = parked_words(
        read(TriageResult.NOW, hours_ago=1), doubt=None, parked_by_owner=False, being_read=False
    )
    assert moved_nothing is not None and moved_nothing.endswith(
        "the board moved nothing, and the card waits for your move"
    )


def test_the_record_fingerprint_is_the_document_and_every_row():
    rows = [Row(kind=RowKind.ASK, text="Which?")]
    assert record_fingerprint("# T\n", rows) != record_fingerprint("# T\n", [])
    assert record_fingerprint(None, rows) != record_fingerprint("# T\n", rows)
    assert record_fingerprint(None, rows) == record_fingerprint(None, list(rows))
