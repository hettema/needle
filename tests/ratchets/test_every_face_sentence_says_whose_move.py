"""Every sentence the board writes on a card opens with whose move it is and
uses no word the owner does not (card #75).

The card is his surface for two things: what this is, and whether it needs
him. The colour answered the second from plan 27 on, and on 2026-09-07 he
read a held card's sentence — "Start waits on the plan's own word: its
Sequencing names #20 …" — and asked whether there was something he had to
do. The sentences were literals with no reader but him, each written by a
session that had read the steering, and nothing held them.

Two things hold them now. The opening is bound to the meaning in code:
`domain.meaning.say` builds every sentence from its meaning and its parts,
and the models that carry a sentence refuse one whose opening is not the
meaning's (`CardState`) or not an opening at all (`Door`, `Lane`). That
construction cannot see the words, so this ratchet reads them: every string
literal the sentence-building modules hand to a sentence, and every sentence
the test board actually builds — a state's detail, a door's reason, a lane's
sentence, the column notes and the page's own two sentences — is read
against `docs/vocabulary.md`, and every amber face is read for "Your move".
The ratchet reads the intent, not the wording: a better sentence is free to
arrive as long as it opens with his part and says it in his words.
"""

import ast
import json
import re
from pathlib import Path

from board.title import jargon_in, read_vocabulary
from domain.column import COLUMN_DEFINITIONS
from domain.meaning import OPENING, Meaning, opening_of, say
from tests.ratchets.paths import FRONTEND_SRC, REPO

SENTENCE_MODULES = [
    REPO / "board" / "assemble.py",
    REPO / "board" / "lane.py",
    REPO / "board" / "collision.py",
]
"""Where the board builds what a card says: the state line and its door
(`assemble`), the doors and the lane's sentence (`lane`), and the shared
ground a face wraps as its reason (`collision`). `api/loops.py` builds
history rows and machine readings, never a face sentence — the plan named
it and the sweep found nothing there to read."""

BUILDERS = {"say", "_state", "_door", "_closed", "_open"}
"""The calls whose string arguments become a face sentence or its word."""

OWNERS_WORDS = {
    Meaning.YOURS: "Your move",
    Meaning.QUIET: "Nothing for you",
    Meaning.LIVE: "Happening now",
    Meaning.BROKEN: "Something is wrong",
    Meaning.PROVEN: "Proven",
}
"""The openings the plan settled (card #75, item 1); the map may reword an
opening only with a ruling, never grow a sixth."""

_UI = FRONTEND_SRC / "components" / "ui" / "index.tsx"
_HELD_TOOLTIP = re.compile(r'className="dial-held"\s+title=\{`([^`]*)`\}')


def _literals_handed_to_builders(path: Path) -> list[tuple[int, str]]:
    """Every string literal, and every constant part of an f-string, inside
    a call to one of the builders — including literals nested in a
    conditional expression or a concatenation among the call's arguments."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name not in BUILDERS:
            continue
        for arg in [*node.args, *(kw.value for kw in node.keywords)]:
            for inner in ast.walk(arg):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    found.append((inner.lineno, inner.value))
    return found


def _fixture_sentences(tmp_path: Path) -> list[tuple[str, Meaning | None, str]]:
    """Every sentence the test board builds, as (where, meaning, text): the
    meaning is the state's for a detail, None for a door's reason and a
    lane's sentence, whose opening only has to be one of the five."""
    from tools.board_fixture import snapshot

    shot = snapshot(tmp_path)
    out: list[tuple[str, Meaning | None, str]] = []
    board = shot["board"]
    assert isinstance(board, dict)
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                state = card["state"]
                where = f"#{card['number']} ({state['word']})"
                if state["detail"] is not None:
                    out.append((f"{where} detail", Meaning(state["meaning"]), state["detail"]))
                if state["door"] is not None:
                    out.append(
                        (f"{where} door {state['door']['label']}", None, state["door"]["why"])
                    )
    details = shot["details"]
    assert isinstance(details, dict)
    for number, detail in details.items():
        for name, door in detail["doors"].items():
            if isinstance(door, dict) and "why" in door and "offered" in door:
                out.append((f"#{number} door {name}", None, door["why"]))
        lane = detail["lane"]
        if lane is not None and lane["sentence"]:
            out.append((f"#{number} lane", None, lane["sentence"]))
    language = shot["language"]
    assert isinstance(language, list)
    for case in language:
        state = case["card"]["state"]
        assert isinstance(state, dict)
        where = f"language case {case['case']} ({state['word']})"
        if state["detail"] is not None:
            out.append((f"{where} detail", Meaning(state["meaning"]), state["detail"]))
        if state["door"] is not None:
            out.append((f"{where} door", None, state["door"]["why"]))
    return out


def test_the_openings_are_the_owners_words_one_per_meaning():
    assert OPENING == OWNERS_WORDS
    assert opening_of(say(Meaning.QUIET, "this starts by itself once #20 ships")) == Meaning.QUIET
    assert opening_of("Start waits on the plan's own word: its Sequencing names #20") is None


def test_no_literal_handed_to_a_sentence_uses_a_word_the_board_defines():
    words = read_vocabulary()
    offenders: list[str] = []
    count = 0
    for path in SENTENCE_MODULES:
        for line, text in _literals_handed_to_builders(path):
            count += 1
            if found := jargon_in(text, words):
                offenders.append(
                    f"{path.relative_to(REPO)}:{line}: {text!r} uses {', '.join(found)}"
                )
    assert count > 100, f"the reader found {count} literals; the modules moved under it"
    assert not offenders, (
        "a sentence the board can say uses a word from docs/vocabulary.md; say it in the "
        "owner's words instead:\n" + "\n".join(offenders)
    )


def test_every_sentence_the_test_board_builds_opens_with_whose_move_and_says_it_plainly(tmp_path):
    words = read_vocabulary()
    sentences = _fixture_sentences(tmp_path)
    assert len(sentences) > 100, f"the test board built {len(sentences)} sentences"
    wrong_opening = [
        f"{where}: {text!r}"
        for where, meaning, text in sentences
        if opening_of(text) is None or (meaning is not None and opening_of(text) != meaning)
    ]
    assert not wrong_opening, "a sentence does not open with its meaning's words:\n" + "\n".join(
        wrong_opening
    )
    jargon = [
        f"{where}: {text!r} uses {', '.join(found)}"
        for where, _, text in sentences
        if (found := jargon_in(text, words))
    ]
    assert not jargon, "a sentence on the test board uses a word from docs/vocabulary.md:\n" + (
        "\n".join(jargon)
    )


def test_an_amber_face_always_says_your_move_and_no_other_face_does():
    from tools.board_fixture import language_cases

    seen: set[Meaning] = set()
    for case in language_cases():
        card = case["card"]
        assert isinstance(card, dict)
        state = card["state"]
        meaning = Meaning(state["meaning"])
        seen.add(meaning)
        detail = state["detail"]
        if meaning in {Meaning.YOURS, Meaning.BROKEN}:
            assert detail is not None, f"{case['case']}: a {meaning.value} face says what"
        if detail is None:
            continue
        opens_yours = detail.startswith("Your move:")
        assert opens_yours == (meaning == Meaning.YOURS), f"{case['case']}: {detail!r}"
    assert seen == set(Meaning), f"the language cases cover {sorted(seen)}"


def test_the_column_notes_and_the_pages_own_sentences_take_the_shape():
    words = read_vocabulary()
    for column in COLUMN_DEFINITIONS:
        assert not jargon_in(column.note, words), f"{column.column}: {column.note!r}"
        for paragraph in column.definition:
            assert not jargon_in(paragraph, words), f"{column.column}: {paragraph!r}"
        if column.yours:
            assert opening_of(column.note) == Meaning.YOURS, column.note
    tooltip = _HELD_TOOLTIP.search(_UI.read_text(encoding="utf-8"))
    assert tooltip is not None, "the head's held count carries no tooltip"
    held = tooltip.group(1).replace("${OPENING.quiet}", OPENING[Meaning.QUIET])
    assert opening_of(held) == Meaning.QUIET, held
    assert not jargon_in(held, words), held
    # The page reads the same map the board builds with, never a copy.
    generated = json.loads(
        re.search(
            r"export const OPENING: Record<Meaning, string> = (\{[^}]*\});",
            (FRONTEND_SRC / "types" / "meaning.ts").read_text(encoding="utf-8"),
        )
        .group(1)  # type: ignore[union-attr]
        .replace(",\n}", "\n}")
    )
    assert generated == {m.value: o for m, o in OPENING.items()}
