"""A project's focus, read and derived (card #87, items 1 and 4): the
document reads into the typed shape and names what it cannot read; a
ruling binds to one fingerprint and any other document is proposed; the
strip has one state per fact; and a card's reading is stale the moment
either text it judged changes."""

from datetime import UTC, datetime

from board.focus import (
    card_leverage,
    coverage_of,
    is_chosen,
    parse_focus,
    paused_why,
    recheck_due,
    strip_of,
    unavailable_why,
    wants_card_reading,
)
from board.parse import parse_document
from domain.card import Place
from domain.column import Column
from domain.document import DocumentKind
from domain.focus import (
    FocusCheck,
    FocusRecheck,
    FocusRuling,
    FocusState,
    FocusVerdict,
    Leverage,
    LeverageReading,
    LeverageState,
    Likelihood,
    RecheckOutcome,
)
from domain.lane import Conversation
from domain.window import WindowKind
from tests.conftest import HARBOURMASTER

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)
TEXT = (HARBOURMASTER / "docs" / "FOCUS.md").read_text(encoding="utf-8")


def test_the_fixture_focus_reads_whole_into_the_typed_shape():
    focus = parse_focus(TEXT, read_at=NOW)
    assert focus.complete, focus.doubts
    assert focus.what_matters == "Every season berth is paid before the boat arrives"
    assert focus.outcome.signal is not None
    assert focus.outcome.signal.kind.value == "command" and focus.outcome.signal.expect == ">= 40"
    assert focus.outcome.signal.every_hours == 7 * 24
    assert focus.what_holds.startswith("The invoice leaves the office late")
    assert focus.bottleneck.signal is not None and focus.bottleneck.signal.expect == ">= 30"
    assert focus.recheck.signal is not None and focus.recheck.signal.kind.value == "session"
    assert focus.recheck.signal.due.isoformat() == "2026-10-15"
    assert focus.evidence and "every-metered-kilowatt" in focus.evidence
    assert focus.rival and "price" in focus.rival
    assert focus.proposed == "conversation 9a3c1e7f, 2026-09-04"
    assert focus.fingerprint and len(focus.fingerprint) == 16


def test_a_missing_measure_or_an_unreadable_recheck_reads_as_a_doubt_naming_the_line():
    no_measure = TEXT.replace(
        "**What holds it back:** The invoice leaves the office late, because the meter readings "
        "it waits on arrive as text the office drops — invoices sent within a day of the reading "
        '— command grep -c "sent within a day" office/invoices.log expect >= 30 by 2026-10-31 '
        "every 7d",
        "**What holds it back:** The invoice leaves the office late",
    )
    focus = parse_focus(no_measure, read_at=NOW)
    assert not focus.complete
    assert focus.doubts == ["**What holds it back:** the line names no measure"]
    assert focus.what_holds == "The invoice leaves the office late"

    bad_recheck = TEXT.replace(
        "**Recheck:** the diagnosis is read again against both measures — session harbourmaster "
        "by 2026-10-15",
        "**Recheck:** sometime in October",
    )
    focus = parse_focus(bad_recheck, read_at=NOW)
    assert len(focus.doubts) == 1 and focus.doubts[0].startswith(
        "**Recheck:** the WATCH row names no reader"
    )

    focus = parse_focus("# Nothing\n\nprose only\n", read_at=NOW)
    assert focus.what_matters is None
    assert "**What matters now:** names no outcome" in focus.doubts
    assert "**Evidence:** is missing" in focus.doubts and "**Rival:** is missing" in focus.doubts


def _ruling(
    fingerprint: str, what_matters: str = "Every season berth is paid before the boat arrives"
) -> FocusRuling:
    return FocusRuling(
        id=1, project="proj", fingerprint=fingerprint, what_matters=what_matters, chosen_at=NOW
    )


def _strip(document, ruling, **changes):
    fields = dict(
        document=document,
        ruling=ruling,
        check=None,
        checking=False,
        check_note=None,
        conversation=None,
        talked_before=False,
        coverage=None,
        moves_proposed=0,
        accepted=None,
        put_back_offered=False,
        recheck=None,
        measures=[],
        now=NOW,
    )
    fields.update(changes)
    return strip_of(**fields)


def test_a_ruling_bound_to_one_fingerprint_over_a_document_now_at_another_is_proposed():
    focus = parse_focus(TEXT, read_at=NOW)
    edited = parse_focus(TEXT + "\nOne more line.\n", read_at=NOW)
    assert focus.fingerprint != edited.fingerprint
    assert is_chosen(focus, _ruling(focus.fingerprint))
    assert not is_chosen(edited, _ruling(focus.fingerprint))
    chosen = _strip(focus, _ruling(focus.fingerprint), coverage=coverage_of({}, {}))
    assert chosen.state == FocusState.CHOSEN
    assert chosen.sentence == "Focus chosen · 0 of 0 cards assessed · 0 moves proposed"
    proposed = _strip(edited, _ruling(focus.fingerprint))
    assert proposed.state == FocusState.PROPOSED
    assert proposed.choose.offered is False, "no second reading yet: the click waits"
    assert "about to open a second reading" in proposed.choose.why


def test_every_strip_state_has_its_sentence_and_its_doors():
    focus = parse_focus(TEXT, read_at=NOW)
    none = _strip(None, None)
    assert none.state == FocusState.NONE and none.sentence == "No focus chosen"
    assert none.talk.offered and not none.choose.offered and not none.propose.offered

    talk = Conversation(
        short_id="ab12cd34",
        slot="alpha",
        card_number=None,
        what="Focus",
        started_at=NOW,
        kind=WindowKind.FOCUS,
    )
    talking = _strip(None, None, conversation=talk)
    assert talking.state == FocusState.TALKING
    assert talking.sentence == "Working out what holds this back"
    assert not talking.talk.offered and "already open" in talking.talk.why

    ended = _strip(None, None, talked_before=True)
    assert ended.state == FocusState.ENDED
    assert ended.sentence == "A conversation ended before a focus was written"

    outcome_only = parse_focus(
        TEXT.replace(
            "**What holds it back:** The invoice leaves the office late, because the meter "
            "readings it waits on arrive as text the office drops — invoices sent within a day "
            'of the reading — command grep -c "sent within a day" office/invoices.log expect '
            ">= 30 by 2026-10-31 every 7d\n",
            "",
        ),
        read_at=NOW,
    )
    unsettled = _strip(outcome_only, None)
    assert unsettled.state == FocusState.OUTCOME_ONLY
    assert unsettled.sentence == (
        "What matters now: Every season berth is paid before the boat arrives · What holds it "
        "back is not settled"
    )
    assert not unsettled.choose.offered and "names no diagnosis" in unsettled.choose.why

    check = FocusCheck(
        id=1,
        project="proj",
        fingerprint=focus.fingerprint,
        at=NOW,
        verdict=FocusVerdict.STANDS,
        line="the log shows it berth by berth",
        how_known=None,
        session_id=None,
    )
    ready = _strip(focus, None, check=check)
    assert ready.state == FocusState.PROPOSED
    assert ready.sentence == "A focus is ready for your decision"
    assert ready.choose.offered and "says it stands: the log shows it" in ready.choose.why
    checking = _strip(focus, None, checking=True)
    assert not checking.choose.offered and "is checking the diagnosis" in checking.choose.why
    without = _strip(
        focus, None, check_note="`codex exec` ended 3.0 s after the ask without an answer"
    )
    assert without.choose.offered, "a call that ended without an answer offers the ruling anyway"
    assert "No second reading landed: `codex exec` ended" in without.choose.why
    disagree = _strip(
        focus, None, check=check.model_copy(update={"verdict": FocusVerdict.DOES_NOT_STAND})
    )
    assert disagree.choose.offered, "disagreement shows as disagreement and never blocks his click"
    assert "does not stand" in disagree.choose.why

    chosen = _strip(focus, _ruling(focus.fingerprint), coverage=coverage_of({}, {}))
    assert chosen.propose.offered and not chosen.choose.offered
    assert unavailable_why(chosen) is None
    assert unavailable_why(none) == "no focus is chosen"
    assert unavailable_why(ready) == "the proposed focus waits for your decision"


def test_expiry_a_failed_recheck_and_a_changed_outcome_pause_the_order_and_holds_does_not():
    focus = parse_focus(TEXT, read_at=NOW)
    ruling = _ruling(focus.fingerprint)
    assert paused_why(focus, ruling, None, NOW) is None
    late = datetime(2026, 10, 16, tzinfo=UTC)
    assert paused_why(focus, ruling, None, late) == (
        "The evidence for this diagnosis expired on 2026-10-15. Leverage order is paused while "
        "it is checked."
    )
    assert recheck_due(focus, None, datetime(2026, 10, 15, tzinfo=UTC))
    assert not recheck_due(focus, None, datetime(2026, 10, 14, tzinfo=UTC))

    def recheck(outcome: RecheckOutcome, fingerprint: str = focus.fingerprint) -> FocusRecheck:
        return FocusRecheck(
            id=1,
            project="proj",
            fingerprint=fingerprint,
            at=late,
            outcome=outcome,
            words="w",
            session_id=None,
        )

    assert paused_why(focus, ruling, recheck(RecheckOutcome.HOLDS), late) is None
    assert not recheck_due(focus, recheck(RecheckOutcome.HOLDS), late)
    assert recheck_due(focus, recheck(RecheckOutcome.HOLDS, "other"), late)
    challenged = paused_why(focus, ruling, recheck(RecheckOutcome.DIAGNOSIS_CHALLENGED), late)
    assert challenged == (
        "The bottleneck measure improved, but Every season berth is paid before the boat "
        "arrives did not. We are checking the diagnosis."
    )
    linked = paused_why(focus, ruling, recheck(RecheckOutcome.WORK_NOT_LINKED), late)
    assert linked is not None and linked.startswith(
        "The work shipped, but invoices sent within a day of the reading has not improved."
    )
    expired = paused_why(focus, ruling, recheck(RecheckOutcome.EXPIRED), NOW)
    assert expired is not None and expired.startswith(
        "The evidence for this diagnosis expired on 2026-10-15"
    )
    renamed = paused_why(focus, _ruling(focus.fingerprint, "something else"), None, NOW)
    assert renamed is not None and renamed.startswith("The outcome sentence changed")
    paused = _strip(focus, ruling, recheck=recheck(RecheckOutcome.DIAGNOSIS_CHALLENGED), now=late)
    assert paused.state == FocusState.PAUSED and paused.sentence == challenged
    assert unavailable_why(paused) == challenged
    due = _strip(
        focus, ruling, coverage=coverage_of({}, {}), now=datetime(2026, 10, 15, tzinfo=UTC)
    )
    assert due.state == FocusState.CHOSEN and due.sentence == "Time to check this focus again"


def _plan(text: str):
    return parse_document(
        text, kind=DocumentKind.PLAN, path="docs/plans/2026-09-01-x.md", archived=False, read_at=NOW
    )


def _reading(leverage: Leverage, focus_fp: str, doc_fp: str, **changes) -> LeverageReading:
    fields = dict(
        id=1,
        project="proj",
        card_number=7,
        at=NOW,
        leverage=leverage,
        likelihood=Likelihood.HIGH if leverage == Leverage.HELPS_REMOVE else None,
        words="the plan bills the reading the invoice waits on",
        focus_fingerprint=focus_fp,
        document_fingerprint=doc_fp,
        session_id=None,
    )
    fields.update(changes)
    return LeverageReading(**fields)


def test_a_reading_goes_stale_when_either_fingerprint_changes_and_the_face_says_which():
    plan = _plan("# A plan\n\n**Effort gate:** low — x\n\n## Intent\n\nBills the reading.\n")
    edited = _plan(
        "# A plan\n\n**Effort gate:** low — x\n\n## Intent\n\nBills the reading, twice.\n"
    )
    reading = _reading(Leverage.HELPS_REMOVE, "focusA", plan.fingerprint)
    assert not wants_card_reading(reading, "focusA", plan, reread_since=None, shipped=False)
    assert wants_card_reading(reading, "focusB", plan, reread_since=None, shipped=False)
    assert wants_card_reading(reading, "focusA", edited, reread_since=None, shipped=False)
    assert wants_card_reading(None, "focusA", plan, reread_since=None, shipped=False)

    read = card_leverage(reading, "focusA", plan, reading_open=False, hold=None)
    assert read.state == LeverageState.READ and read.leverage == Leverage.HELPS_REMOVE
    assert read.sentence == (
        "Nothing for you: it helps remove this limit (high likelihood). The plan bills the "
        "reading the invoice waits on."
    )
    held = card_leverage(reading, "focusA", plan, reading_open=False, hold="#139")
    assert held.hold == "#139" and held.sentence.endswith("It also waits on #139.")
    stale = card_leverage(reading, "focusB", plan, reading_open=False, hold=None)
    assert stale.state == LeverageState.STALE and "because the focus changed" in stale.sentence
    stale = card_leverage(reading, "focusA", edited, reading_open=False, hold=None)
    assert stale.state == LeverageState.STALE and "because its document changed" in stale.sentence
    unread = card_leverage(None, "focusA", plan, reading_open=False, hold=None)
    assert unread.state == LeverageState.UNREAD and unread.sentence.startswith("Nothing for you:")
    live = card_leverage(None, "focusA", plan, reading_open=True, hold=None)
    assert live.state == LeverageState.READING and live.sentence.startswith("Happening now:")


def test_a_shipped_helps_remove_card_is_read_again_only_after_a_recheck_says_work_not_linked():
    plan = _plan("# A plan\n\n## Intent\n\nBills the reading.\n")
    before = datetime(2026, 9, 1, tzinfo=UTC)
    reading = _reading(Leverage.HELPS_REMOVE, "focusA", plan.fingerprint, at=before)
    assert wants_card_reading(reading, "focusA", plan, reread_since=NOW, shipped=True)
    assert not wants_card_reading(reading, "focusA", plan, reread_since=NOW, shipped=False)
    protects = _reading(Leverage.PROTECTS, "focusA", plan.fingerprint, at=before)
    assert not wants_card_reading(protects, "focusA", plan, reread_since=NOW, shipped=True)


def test_coverage_counts_every_state_and_says_whether_anything_queued_helps():
    plan = _plan("# A plan\n\n## Intent\n\nBills the reading.\n")
    places = {
        1: Place(column=Column.UP_NEXT, group=None, position=0),
        2: Place(column=Column.PLANNED, group=None, position=0),
        3: Place(column=Column.BACKLOG, group=None, position=0),
        4: Place(column=Column.UP_NEXT, group=None, position=1),
    }
    leverages = {
        1: card_leverage(
            _reading(Leverage.HELPS_REMOVE, "f", plan.fingerprint),
            "f",
            plan,
            reading_open=False,
            hold=None,
        ),
        2: card_leverage(
            _reading(Leverage.NEEDS_EVIDENCE, "f", plan.fingerprint),
            "f",
            plan,
            reading_open=False,
            hold=None,
        ),
        3: card_leverage(None, "f", plan, reading_open=False, hold=None),
        4: card_leverage(
            _reading(Leverage.HELPS_REMOVE, "old", plan.fingerprint),
            "f",
            plan,
            reading_open=False,
            hold=None,
        ),
    }
    coverage = coverage_of(places, leverages)
    assert (coverage.assessed, coverage.total, coverage.unread, coverage.stale) == (2, 4, 1, 1)
    assert coverage.needs_evidence == 1 and coverage.queued_helping == 1
    assert coverage.line == "1 queued card helps remove this limit"
    del leverages[1]
    del places[1]
    assert coverage_of(places, leverages).line == "Nothing queued is evidenced to remove this limit"
