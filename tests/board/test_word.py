"""What the board tells a running lane, once (plan 10, item 1), pure over
the loop's lane, the watercooler and the heard-mark."""

from datetime import UTC, datetime, timedelta

from board.word import CLEARED, SAY_SO, compose, notes_word
from domain.card import Actor
from domain.hook import HeardMark
from domain.lane import Collision, CollisionVerdict, Lane, LaneState
from domain.watercooler import Note, WatercoolerLine

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
READ_AT = NOW - timedelta(seconds=20)
HANDS_ON_SINCE = NOW - timedelta(minutes=30)


def lane(
    number: int = 253,
    *,
    state: LaneState = LaneState.WORKING,
    colliding: Collision | None = None,
    path: str | None = "/srv/p/.claude/worktrees/card-253-x",
) -> Lane:
    return Lane(
        card_number=number,
        name="card-253-x",
        path=path,
        state=state,
        sentence="Working.",
        session=None,
        question=None,
        said=None,
        said_at=None,
        discussing=[],
        window_open=False,
        hands_on_since=HANDS_ON_SINCE,
        died=None,
        moved=None,
        folded=False,
        trunk_synced=False,
        main_synced=False,
        edits=["README.md"] if colliding else [],
        declared=[],
        colliding=colliding,
    )


def line(id: int, who: int | None, text: str, *, at: datetime = NOW) -> WatercoolerLine:
    return WatercoolerLine(
        id=id,
        project="proj",
        card_number=who,
        actor=Actor.MACHINE if who is None else Actor.SESSION,
        at=at,
        text=text,
    )


DRIFT = Collision(
    verdict=CollisionVerdict.COLLIDES,
    sentence="#241's lane is also editing README.md.",
    files=["README.md"],
    cards=[241],
)


def test_a_drift_is_said_once_with_the_ask_and_its_clearing_is_said_once():
    word, mark = compose(
        "proj", lane(colliding=DRIFT), [], None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert word.sentences == [f"#241's lane is also editing README.md. {SAY_SO}"]
    assert word.read_at == READ_AT
    assert mark is not None and mark.collision == DRIFT.sentence and mark.at == NOW
    assert mark.text == word.sentences[0]

    again, moved = compose(
        "proj", lane(colliding=DRIFT), [], mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert again.sentences == [] and moved is None

    cleared, after = compose(
        "proj", lane(), [], mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert cleared.sentences == [CLEARED]
    assert after is not None and after.collision is None

    quiet, none = compose("proj", lane(), [], after, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT)
    assert quiet.sentences == [] and none is None


def test_a_drift_that_names_different_files_is_said_again():
    _, mark = compose(
        "proj", lane(colliding=DRIFT), [], None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    wider = DRIFT.model_copy(
        update={
            "sentence": "#241's lane is also editing README.md, api/app.py.",
            "files": ["README.md", "api/app.py"],
        }
    )
    word, _ = compose(
        "proj", lane(colliding=wider), [], mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert word.sentences == [f"{wider.sentence} {SAY_SO}"]


def test_other_lanes_lines_reach_the_lane_once_and_its_own_never():
    lines = [
        line(1, 241, "README.md is mine until the fold", at=NOW - timedelta(minutes=5)),
        line(2, 253, "noted", at=NOW - timedelta(minutes=4)),
        line(3, None, "#109 folded over #253's edits in README.md", at=NOW - timedelta(minutes=3)),
    ]
    word, mark = compose(
        "proj", lane(), lines, None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert word.sentences == [
        "#241 said on the watercooler: README.md is mine until the fold",
        "The board said on the watercooler: #109 folded over #253's edits in README.md",
    ]
    assert mark is not None and mark.watercooler_id == 3
    again, moved = compose(
        "proj", lane(), lines, mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert again.sentences == [] and moved is None

    only_own = lines + [line(4, 253, "folding now")]
    still, passed = compose(
        "proj", lane(), only_own, mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert still.sentences == [], "a lane never hears itself"
    assert passed is not None and passed.watercooler_id == 4, "but the mark passes its own line"
    assert passed.at == mark.at and passed.text == mark.text, "which the card is not told about"
    then = only_own + [line(5, 241, "go ahead")]
    word, mark = compose("proj", lane(), then, mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT)
    assert word.sentences == ["#241 said on the watercooler: go ahead"]
    assert mark is not None and mark.watercooler_id == 5, "the own line is passed over with it"


def test_before_any_mark_the_lines_its_brief_carried_are_already_heard():
    before = line(1, 241, "said before this lane started", at=HANDS_ON_SINCE - timedelta(minutes=1))
    after = line(2, 241, "said while it runs", at=HANDS_ON_SINCE + timedelta(minutes=1))
    word, mark = compose(
        "proj", lane(), [before, after], None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert word.sentences == ["#241 said on the watercooler: said while it runs"]
    assert mark is not None and mark.watercooler_id == 2


def test_drift_and_lines_come_as_one_word_and_a_lane_without_hands_hears_nothing():
    lines = [line(1, 241, "leave README.md", at=NOW)]
    word, _ = compose(
        "proj", lane(colliding=DRIFT), lines, None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert len(word.sentences) == 2 and word.sentences[0].endswith(SAY_SO)
    ended = lane(state=LaneState.ENDED, path=None, colliding=DRIFT)
    nothing, none = compose(
        "proj", ended, lines, None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert nothing.sentences == [] and none is None
    existing = HeardMark(
        project="proj", card_number=253, watercooler_id=0, collision=None, at=None, text=None
    )
    nothing, none = compose(
        "proj", ended, lines, existing, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert nothing.sentences == [] and none is None


def test_a_quiet_lane_records_its_baseline_so_it_never_re_reads_the_watercooler():
    """The word runs on every tool call, so hearing that moved is written
    down even when there was nothing to say: a lane told nothing records the
    baseline it started from, and a lane whose own line went by records
    passing it. Only a word that said something stamps `at` and `text`,
    which is what the card shows — so the caller can tell a silent mark from
    one worth turning the page over for."""
    said_before = line(1, 241, "in the brief", at=HANDS_ON_SINCE - timedelta(minutes=1))
    quiet, mark = compose(
        "proj", lane(), [said_before], None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert quiet.sentences == []
    assert mark is not None and mark.watercooler_id == 1, "the baseline is written down"
    assert mark.at is None and mark.text is None, "nothing was said, so the card shows nothing"

    # Nothing has changed since: no mark to write at all.
    again, none = compose("proj", lane(), [], mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT)
    assert again.sentences == [] and none is None

    # The lane's own line goes by: the mark advances, still silently.
    own = [line(2, 253, "folding now")]
    still, moved = compose(
        "proj", lane(), own, mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert still.sentences == []
    assert moved is not None and moved.watercooler_id == 2 and moved.at is None


def test_how_much_of_the_watercooler_the_caller_must_read_is_the_marks_to_decide():
    """The contract `Loops.word_now` is written against: with a mark, only
    the lines past it are needed; without one, the whole watercooler, since
    the baseline is read from what was said before `since`. Reading less
    than that on a fresh lane loses a line said after it — the one shape of
    starvation this composer cannot detect for itself."""
    said_before = line(1, 241, "in the brief", at=HANDS_ON_SINCE - timedelta(minutes=1))
    while_running = line(2, 241, "said while it runs", at=HANDS_ON_SINCE + timedelta(minutes=1))
    whole, mark = compose(
        "proj",
        lane(),
        [said_before, while_running],
        None,
        since=HANDS_ON_SINCE,
        now=NOW,
        read_at=READ_AT,
    )
    assert whole.sentences == ["#241 said on the watercooler: said while it runs"]
    assert mark is not None and mark.watercooler_id == 2

    # Starved past the running line, the fresh lane never hears it: the
    # caller reads from 0 while the mark is None, and this is why.
    starved, _ = compose("proj", lane(), [], None, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT)
    assert starved.sentences == [], "a line not handed in cannot be said"

    # With a mark, the lines past it are all the composer needs.
    past = [line(3, 241, "after the mark")]
    word, moved = compose(
        "proj", lane(), past, mark, since=HANDS_ON_SINCE, now=NOW, read_at=READ_AT
    )
    assert word.sentences == ["#241 said on the watercooler: after the mark"]
    assert moved is not None and moved.watercooler_id == 3


# ── the machine's watercooler in the same word (plan 17, item 2) ───────


def note(path: str, first: str, at: datetime) -> Note:
    return Note(path=path, first_line=first, at=at)


def test_a_note_the_lane_is_party_to_is_said_once_its_own_never_and_a_change_again():
    codex = "/srv/d/from-codex-topic.md"
    other = "/srv/d/from-codex-other.md"
    notes = [note(codex, "# From Codex — the ask", NOW), note(other, "# elsewhere", NOW)]
    said, moved = notes_word(notes, {}, party_to={codex})
    assert said == [f"A note landed on the machine's watercooler: {codex} — # From Codex — the ask"]
    assert moved == {codex: NOW}, "the note the lane is not party to is neither said nor stamped"

    again, moved_again = notes_word(notes, moved, party_to={codex})
    assert again == [] and moved_again == {}, "said once"

    changed = [note(codex, "# From Codex — the ask", NOW + timedelta(minutes=2))]
    said_changed, _ = notes_word(changed, moved, party_to={codex})
    assert said_changed == [
        f"A note changed on the machine's watercooler: {codex} — # From Codex — the ask"
    ]

    own = {codex: NOW + timedelta(minutes=2)}
    assert notes_word(changed, own, party_to={codex}) == ([], {}), (
        "a note the lane itself wrote was stamped at the write, so it never hears its own"
    )
    assert notes_word([], {}, party_to=set()) == ([], {})
