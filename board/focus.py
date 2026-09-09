"""A project's focus, read from its document and derived once for every
reader (card #87) — pure over domain values; the loop that opens readings
lives in `api/focus.py`, the doors in `api/doors.py`.

Three things live here: the reader of `docs/FOCUS.md`, the one function
that says what state the strip is in from the document and the store's
facts together, and the one function that says where a card stands against
the chosen focus. Nothing anywhere else decides whether a focus is chosen
by comparing fingerprints, and nothing anywhere else decides whether a
reading is stale — that is the drift this module exists to make impossible.
"""

from datetime import datetime

from board.parse import head_fields_of
from board.signals import past_due, read_or_decline
from board.triage import fingerprint
from domain.card import Place
from domain.column import Column
from domain.document import Document, HeadField
from domain.focus import (
    Acceptance,
    CardLeverage,
    Coverage,
    FocusCheck,
    FocusDocument,
    FocusRecheck,
    FocusRuling,
    FocusState,
    FocusStrip,
    Leverage,
    LeverageReading,
    LeverageState,
    Measure,
    MeasureReading,
    RecheckOutcome,
)
from domain.lane import Conversation, Door
from domain.meaning import Meaning, say

FOCUS_PATH = "docs/FOCUS.md"
"""Where a project's focus lives: one document, in the project's own
repository, read by the corpus reader like a plan."""

WHAT_MATTERS = "What matters now"
WHAT_HOLDS = "What holds it back"
EVIDENCE = "Evidence"
RIVAL = "Rival"
RECHECK = "Recheck"
PROPOSED = "Proposed"
"""The head lines the board reads; every other line is prose."""

_SEPARATORS = (" — ", " – ", " -- ")


def _field(fields: list[HeadField], key: str) -> str | None:
    for field in fields:
        if field.key.lower() == key.lower():
            return field.value.strip() or None
    return None


def _sentence_and_measure(value: str | None) -> tuple[str | None, Measure]:
    """A line of the shape `<sentence> — <what> — <kind> <target> … by <date>`:
    the sentence before the first separator, the measure after it. A line
    with no separator is a sentence with no measure."""
    if value is None:
        return None, Measure(line=None, signal=None, note="the line is missing")
    for separator in _SEPARATORS:
        if separator in value:
            sentence, rest = value.split(separator, 1)
            signal, note = read_or_decline(rest.strip())
            return sentence.strip() or None, Measure(line=rest.strip(), signal=signal, note=note)
    return value.strip() or None, Measure(line=None, signal=None, note="the line names no measure")


def _measure(value: str | None) -> Measure:
    if value is None:
        return Measure(line=None, signal=None, note="the line is missing")
    signal, note = read_or_decline(value)
    return Measure(line=value, signal=signal, note=note)


def parse_focus(text: str, *, path: str = FOCUS_PATH, read_at: datetime) -> FocusDocument:
    """The focus document as the board reads it (card #87, item 1). Every
    field the board needs is named in `doubts` when it is missing or cannot
    be read, so the strip says which line to fix rather than showing a
    focus that cannot be chosen."""
    fields = head_fields_of(text)
    lines = text.split("\n")
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "Focus")
    what_matters, outcome = _sentence_and_measure(_field(fields, WHAT_MATTERS))
    what_holds, bottleneck = _sentence_and_measure(_field(fields, WHAT_HOLDS))
    recheck = _measure(_field(fields, RECHECK))
    doubts: list[str] = []
    if what_matters is None:
        doubts.append(f"**{WHAT_MATTERS}:** names no outcome")
    if outcome.signal is None:
        doubts.append(f"**{WHAT_MATTERS}:** {outcome.note}")
    if what_holds is None:
        doubts.append(f"**{WHAT_HOLDS}:** names no diagnosis")
    if bottleneck.signal is None:
        doubts.append(f"**{WHAT_HOLDS}:** {bottleneck.note}")
    evidence = _field(fields, EVIDENCE)
    rival = _field(fields, RIVAL)
    if evidence is None:
        doubts.append(f"**{EVIDENCE}:** is missing")
    if rival is None:
        doubts.append(f"**{RIVAL}:** is missing")
    if recheck.signal is None:
        doubts.append(f"**{RECHECK}:** {recheck.note}")
    return FocusDocument(
        path=path,
        fingerprint=fingerprint(text),
        title=title,
        what_matters=what_matters,
        outcome=outcome,
        what_holds=what_holds,
        bottleneck=bottleneck,
        evidence=evidence,
        rival=rival,
        recheck=recheck,
        proposed=_field(fields, PROPOSED),
        doubts=doubts,
        read_at=read_at,
    )


# ── the one place a ruling meets a document ────────────────────────────


def is_chosen(document: FocusDocument | None, ruling: FocusRuling | None) -> bool:
    """A focus is chosen only while the document on disk has the ruling's
    fingerprint; any other document is proposed."""
    return (
        document is not None
        and ruling is not None
        and document.complete
        and document.fingerprint == ruling.fingerprint
    )


def paused_why(
    document: FocusDocument, ruling: FocusRuling, recheck: FocusRecheck | None, now: datetime
) -> str | None:
    """Why the leverage order is paused on a chosen focus, in the strip's
    words, or None while it orders (card #87, item 6). Expiry, a failed
    recheck and a changed outcome sentence pause it by themselves; the
    board never turns any of them into a change of priority."""
    if document.what_matters != ruling.what_matters:
        return (
            "The outcome sentence changed after this focus was chosen. Leverage order is "
            "paused until you choose the focus again."
        )
    signal = document.recheck.signal
    if recheck is not None and recheck.fingerprint == document.fingerprint:
        if recheck.outcome == RecheckOutcome.DIAGNOSIS_CHALLENGED:
            return (
                f"The bottleneck measure improved, but {document.what_matters} did not. We are "
                "checking the diagnosis."
            )
        if recheck.outcome == RecheckOutcome.WORK_NOT_LINKED:
            bottleneck = document.bottleneck.signal.what if document.bottleneck.signal else ""
            return (
                f"The work shipped, but {bottleneck} has not improved. We are checking whether "
                "the work changed the limiting cause."
            )
        if recheck.outcome == RecheckOutcome.EXPIRED:
            when = signal.due.isoformat() if signal is not None else "its recheck date"
            return (
                f"The evidence for this diagnosis expired on {when}. Leverage order is paused "
                "while it is checked."
            )
        return None
    if signal is not None and past_due(signal, now):
        return (
            f"The evidence for this diagnosis expired on {signal.due.isoformat()}. Leverage "
            "order is paused while it is checked."
        )
    return None


def recheck_due(document: FocusDocument, recheck: FocusRecheck | None, now: datetime) -> bool:
    """Whether the recheck date has arrived and no reading of this
    document has landed since it: the moment the loop opens one."""
    signal = document.recheck.signal
    if signal is None:
        return False
    if now.date() < signal.due:
        return False
    return recheck is None or recheck.fingerprint != document.fingerprint


# ── the strip ──────────────────────────────────────────────────────────


def _door(label: str, offered: bool, meaning: Meaning, what: str, why: str | None = None) -> Door:
    return Door(offered=offered, label=label, why=say(meaning, what, why=why))


def strip_of(
    *,
    document: FocusDocument | None,
    ruling: FocusRuling | None,
    check: FocusCheck | None,
    checking: bool,
    check_note: str | None,
    conversation: Conversation | None,
    talked_before: bool,
    coverage: Coverage | None,
    moves_proposed: int,
    accepted: Acceptance | None,
    put_back_offered: bool,
    recheck: FocusRecheck | None,
    measures: list[MeasureReading],
    now: datetime,
) -> FocusStrip:
    """The strip from the document and the store's facts together: one
    state, its sentence in the plan's words, and the three doors with why
    each opens or not. `check` is the latest reading of *this* document
    (the caller matches the fingerprint); `talked_before` is whether a
    focus conversation was ever opened, so an ended one can be said."""
    talk = _door(
        "Talk it through",
        conversation is None,
        Meaning.LIVE if conversation is not None else Meaning.QUIET,
        "a focus conversation is already open for this project"
        if conversation is not None
        else "press it and a conversation opens to sharpen what matters now and find what "
        "holds it back",
        why=f"{conversation.short_id} on {conversation.slot}" if conversation else None,
    )
    propose = _door(
        "Propose moves",
        conversation is None and is_chosen(document, ruling),
        Meaning.QUIET,
        "press it and the conversation proposes what else could move this limit, each as a "
        "suggestion on your word"
        if is_chosen(document, ruling)
        else "moves are proposed against a chosen focus",
    )
    closed_choose = _door(
        "Use this focus", False, Meaning.QUIET, "there is no complete focus document to choose"
    )
    if document is None:
        if conversation is not None:
            return FocusStrip(
                state=FocusState.TALKING,
                sentence="Working out what holds this back",
                what_matters=None,
                what_holds=None,
                document=None,
                ruling=ruling,
                check=None,
                checking=False,
                check_note=None,
                conversation=conversation,
                coverage=None,
                moves_proposed=0,
                accepted=None,
                put_back_offered=False,
                paused=None,
                recheck_due=None,
                recheck=None,
                measures=[],
                talk=talk,
                choose=closed_choose,
                propose=propose,
            )
        return FocusStrip(
            state=FocusState.ENDED if talked_before else FocusState.NONE,
            sentence=(
                "A conversation ended before a focus was written"
                if talked_before
                else "No focus chosen"
            ),
            what_matters=None,
            what_holds=None,
            document=None,
            ruling=ruling,
            check=None,
            checking=False,
            check_note=None,
            conversation=None,
            coverage=None,
            moves_proposed=0,
            accepted=None,
            put_back_offered=False,
            paused=None,
            recheck_due=None,
            recheck=None,
            measures=[],
            talk=talk,
            choose=closed_choose,
            propose=propose,
        )
    due = document.recheck.signal.due if document.recheck.signal is not None else None
    if is_chosen(document, ruling):
        assert ruling is not None
        paused = paused_why(document, ruling, recheck, now)
        if paused is None and recheck_due(document, recheck, now):
            head = "Time to check this focus again"
        elif coverage is not None:
            head = (
                f"Focus chosen · {coverage.assessed} of {coverage.total} cards assessed · "
                f"{moves_proposed} move{'' if moves_proposed == 1 else 's'} proposed"
            )
        else:
            head = "Focus chosen"
        if accepted is not None and put_back_offered:
            head += f" · Order accepted {accepted.at.date().isoformat()} · Put it back"
        return FocusStrip(
            state=FocusState.PAUSED if paused is not None else FocusState.CHOSEN,
            sentence=paused if paused is not None else head,
            what_matters=document.what_matters,
            what_holds=document.what_holds,
            document=document,
            ruling=ruling,
            check=check,
            checking=False,
            check_note=None,
            conversation=conversation,
            coverage=coverage,
            moves_proposed=moves_proposed,
            accepted=accepted,
            put_back_offered=put_back_offered,
            paused=paused,
            recheck_due=due,
            recheck=recheck,
            measures=measures,
            talk=talk,
            choose=_door("Use this focus", False, Meaning.QUIET, "this focus is chosen already"),
            propose=propose,
        )
    # Proposed: a document the ruling does not bind, complete or not.
    if not document.complete:
        unsettled = document.what_matters is not None and document.what_holds is None
        state = FocusState.OUTCOME_ONLY if unsettled else FocusState.PROPOSED
        sentence = (
            f"What matters now: {document.what_matters} · What holds it back is not settled"
            if unsettled
            else "A focus is written and cannot be chosen yet: " + document.doubts[0]
        )
        choose = _door(
            "Use this focus",
            False,
            Meaning.QUIET,
            "this document cannot be chosen until every line reads",
            why="; ".join(document.doubts),
        )
        return FocusStrip(
            state=state,
            sentence=sentence,
            what_matters=document.what_matters,
            what_holds=document.what_holds,
            document=document,
            ruling=ruling,
            check=None,
            checking=False,
            check_note=None,
            conversation=conversation,
            coverage=None,
            moves_proposed=0,
            accepted=None,
            put_back_offered=False,
            paused=None,
            recheck_due=due,
            recheck=None,
            measures=[],
            talk=talk,
            choose=choose,
            propose=propose,
        )
    if check is not None:
        choose = _door(
            "Use this focus",
            True,
            Meaning.YOURS,
            "choose this focus, or keep discussing it",
            why=f"a reader of the other kind says it {check.verdict.value}: {check.line}",
        )
    elif check_note is not None:
        choose = _door(
            "Use this focus",
            True,
            Meaning.YOURS,
            "choose this focus, or keep discussing it",
            why=f"no second reading landed: {check_note}",
        )
    else:
        choose = _door(
            "Use this focus",
            False,
            Meaning.LIVE if checking else Meaning.QUIET,
            "a reader of the other kind is checking the diagnosis"
            if checking
            else "the board is about to open a second reading of the diagnosis",
        )
    return FocusStrip(
        state=FocusState.PROPOSED,
        sentence="A focus is ready for your decision",
        what_matters=document.what_matters,
        what_holds=document.what_holds,
        document=document,
        ruling=ruling,
        check=check,
        checking=checking,
        check_note=check_note,
        conversation=conversation,
        coverage=None,
        moves_proposed=0,
        accepted=None,
        put_back_offered=False,
        paused=None,
        recheck_due=due,
        recheck=None,
        measures=[],
        talk=talk,
        choose=choose,
        propose=propose,
    )


def unavailable_why(strip: FocusStrip) -> str | None:
    """Why the leverage order cannot be shown, or None when it can."""
    if strip.state == FocusState.PAUSED:
        return strip.paused
    if strip.state != FocusState.CHOSEN:
        return {
            FocusState.NONE: "no focus is chosen",
            FocusState.OUTCOME_ONLY: "what holds it back is not settled",
            FocusState.TALKING: "a conversation is still working out what holds this back",
            FocusState.ENDED: "the conversation ended before a focus was written",
            FocusState.PROPOSED: "the proposed focus waits for your decision",
        }[strip.state]
    return None


# ── where a card stands ────────────────────────────────────────────────


def reading_is_current(
    reading: LeverageReading, focus_fingerprint: str, document: Document | None
) -> bool:
    """A reading holds only while both texts it judged are the texts on
    disk: the focus document's, and the card's own."""
    if reading.focus_fingerprint != focus_fingerprint:
        return False
    return document is not None and reading.document_fingerprint == document.fingerprint


def wants_card_reading(
    reading: LeverageReading | None,
    focus_fingerprint: str,
    document: Document | None,
    *,
    reread_since: datetime | None,
    shipped: bool,
) -> bool:
    """Whether the loop should read this card against the focus now: no
    reading since the focus was chosen or the card's document changed, or
    a helps-remove reading on a card that shipped when the recheck said the
    work did not move the bottleneck (card #87, item 6)."""
    if document is None or (document.archived and not shipped):
        return False
    if shipped:
        # A shipped card is read again only when the recheck said the work
        # did not move the bottleneck, and only if it was read as helping.
        return (
            reread_since is not None
            and reading is not None
            and reading.leverage == Leverage.HELPS_REMOVE
            and reading.at < reread_since
        )
    return reading is None or not reading_is_current(reading, focus_fingerprint, document)


def card_leverage(
    reading: LeverageReading | None,
    focus_fingerprint: str,
    document: Document | None,
    *,
    reading_open: bool,
    hold: str | None,
) -> CardLeverage:
    """What the face says under the lens, in the one shape (card #75)."""
    then = f"It also waits on {hold}." if hold else None
    if reading_open:
        return CardLeverage(
            state=LeverageState.READING,
            leverage=None,
            likelihood=None,
            words=None,
            sentence=say(
                Meaning.LIVE,
                "a colleague of the other kind is reading this card against the focus",
                then=then,
            ),
            hold=hold,
            read_at=None,
        )
    if reading is None:
        return CardLeverage(
            state=LeverageState.UNREAD,
            leverage=None,
            likelihood=None,
            words=None,
            sentence=say(
                Meaning.QUIET,
                "this card has not been read against the focus yet",
                why="it keeps its place until a reading lands",
                then=then,
            ),
            hold=hold,
            read_at=None,
        )
    if not reading_is_current(reading, focus_fingerprint, document):
        changed = (
            "the focus changed"
            if reading.focus_fingerprint != focus_fingerprint
            else "its document changed"
        )
        return CardLeverage(
            state=LeverageState.STALE,
            leverage=reading.leverage,
            likelihood=reading.likelihood,
            words=reading.words,
            sentence=say(
                Meaning.QUIET,
                f"its reading of {reading.at.date().isoformat()} is stale because {changed}",
                why="it keeps its place until it is read again",
                then=then,
            ),
            hold=hold,
            read_at=reading.at,
        )
    likelihood = f" ({reading.likelihood.value} likelihood)" if reading.likelihood else ""
    return CardLeverage(
        state=LeverageState.READ,
        leverage=reading.leverage,
        likelihood=reading.likelihood,
        words=reading.words,
        sentence=say(
            Meaning.QUIET,
            f"it {reading.leverage.value}{likelihood}",
            why=reading.words,
            then=then,
        ),
        hold=hold,
        read_at=reading.at,
    )


OPEN_COLUMNS: frozenset[Column] = frozenset(
    {Column.BACKLOG, Column.PLANNED, Column.UP_NEXT, Column.EXECUTING, Column.DECISION_MOMENT}
)
"""The columns whose cards are read against the focus: everything not yet
shipped or parked. Executed and Done are read only when a recheck asks
whether shipped work moved the bottleneck; Not now is a ruling of his and
is read too, since the lens may pull a parked card forward."""

READ_COLUMNS: frozenset[Column] = OPEN_COLUMNS | {Column.NOT_NOW}


def coverage_of(places: dict[int, Place], leverages: dict[int, CardLeverage]) -> Coverage:
    """The strip's counts over the cards the readings cover."""
    total = len(leverages)
    assessed = sum(1 for lv in leverages.values() if lv.state == LeverageState.READ)
    unread = sum(1 for lv in leverages.values() if lv.state == LeverageState.UNREAD)
    stale = sum(1 for lv in leverages.values() if lv.state == LeverageState.STALE)
    reading = sum(1 for lv in leverages.values() if lv.state == LeverageState.READING)
    needs = sum(
        1
        for lv in leverages.values()
        if lv.state == LeverageState.READ and lv.leverage == Leverage.NEEDS_EVIDENCE
    )
    queued = sum(
        1
        for number, lv in leverages.items()
        if lv.state == LeverageState.READ
        and lv.leverage == Leverage.HELPS_REMOVE
        and places[number].column == Column.UP_NEXT
    )
    if queued:
        line = (
            f"{queued} queued card{'' if queued == 1 else 's'} help{'s' if queued == 1 else ''} "
            "remove this limit"
        )
    else:
        line = "Nothing queued is evidenced to remove this limit"
    return Coverage(
        assessed=assessed,
        total=total,
        unread=unread,
        needs_evidence=needs,
        stale=stale,
        reading=reading,
        queued_helping=queued,
        line=line,
    )


def check_is_current(check: FocusCheck | None, document: FocusDocument | None) -> FocusCheck | None:
    """The reading of this document, or None when the last reading judged
    another text — a re-edited document is read again."""
    if check is None or document is None or check.fingerprint != document.fingerprint:
        return None
    return check
