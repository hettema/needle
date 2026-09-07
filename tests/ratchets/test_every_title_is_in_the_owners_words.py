"""Every live title on Needle's own board is one the owner can place from
the title alone, and a plan carries no number of its own (card #74, items
1 and 5).

The owner ranks cards from their titles and directs on intent, never
mechanism; the rule was written in `docs/plans/README.md` and, on
2026-09-07, nineteen of the twenty-eight live titles here used a word the
board or the code defines and he does not. A boundary held by memory
erodes (HOW-WE-WORK §5), so the cheap half of the rule is refused here: a
live plan or suggestion title that uses a word from `docs/vocabulary.md`,
and a live plan whose title or stem begins with a sequence number — the
second identifier his ruling of 2026-09-07 retired, because the card's
number is the one he sees and a plan is cited by its card.

The floor, not the test: a title can avoid every listed word and still say
nothing he can place. His test is applied by the cold read at a card's
birth (item 3), on every project's board. This ratchet reads Needle's own
corpus because Needle's tests can; the archive under `done/` is not read,
because he does not rank Done and renaming an archived plan costs every
citation to it.
"""

from pathlib import Path

from board.parse import stem_of
from board.title import VOCABULARY_PATH, jargon_in, read_vocabulary, sequence_number_in
from tests.ratchets.paths import REPO

FOLDERS = [REPO / "docs" / "plans", REPO / "docs" / "slice-suggestions"]
NAMED_IN_THE_INTENT = {
    "lane",
    "make",
    "fold",
    "dial",
    "ring",
    "door",
    "wall",
    "pill",
    "gate",
    "scope",
    "corpus",
    "fixture",
    "migration",
    "store",
}
"""The fourteen words the plan's intent counted in live titles; the file
may grow, never shrink below these."""


def _live_documents() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for folder in FOLDERS:
        for path in sorted(folder.glob("*.md")):
            if path.name.upper() == "README.MD":
                continue
            first = path.read_text(encoding="utf-8").splitlines()[0]
            title = first.lstrip("#").strip() if first.startswith("#") else stem_of(path.stem)
            found.append((path, title))
    return found


def test_the_vocabulary_carries_at_least_the_words_the_intent_named():
    words = {w.word for w in read_vocabulary()}
    assert NAMED_IN_THE_INTENT <= words, sorted(NAMED_IN_THE_INTENT - words)
    assert VOCABULARY_PATH.name == "vocabulary.md"


def test_no_live_title_uses_a_word_the_board_defines():
    words = read_vocabulary()
    offenders = [
        f"{path.relative_to(REPO)}: {title!r} uses {', '.join(found)}"
        for path, title in _live_documents()
        if (found := jargon_in(title, words))
    ]
    assert not offenders, (
        "a live title uses a word from docs/vocabulary.md; say the outcome in the owner's "
        "words instead:\n" + "\n".join(offenders)
    )


def test_no_live_plan_carries_a_sequence_number():
    offenders = [
        f"{path.relative_to(REPO)}: {why}"
        for path, title in _live_documents()
        if path.parent.name == "plans" and (why := sequence_number_in(title, path.stem))
    ]
    assert not offenders, (
        "a live plan carries a sequence number; the card's number is the one identifier "
        "(owner ruling 2026-09-07, card #74):\n" + "\n".join(offenders)
    )


def test_the_reader_fails_a_fixture_title_with_lane_and_a_numbered_stem():
    words = read_vocabulary()
    assert jargon_in("A lane the machine ended comes back by itself", words) == ["lane"]
    assert jargon_in("Two lanes never share one file", words) == ["lane"]
    assert jargon_in("The board's word on a lane's end is true", words) == ["lane"]
    assert jargon_in("Whatever its make, the strongest colleague drives", words) == ["make"]
    assert jargon_in("Defects fix themselves", words) == []
    assert jargon_in("Every session makes the board true", words) == [], "the verb is his"
    assert sequence_number_in("17 — The plan shape is taught once", "2026-09-07-17-x") is not None
    assert sequence_number_in("The plan shape is taught once", "2026-09-07-17-x") is not None
    assert sequence_number_in("The plan shape is taught once", "2026-09-07-the-plan-shape") is None
