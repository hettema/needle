"""A live document read against the other live documents of its project:
who sits beside it, on what ground, and whether it says so (card #69).

Nothing else in `board/` reads a document against the others —
`collision.py` reads lanes editing now, `sequencing.py` a plan's own word,
`reconcile.py` identity, `triage.py` a mark — so this reader was born
after that search. It is pure over parsed documents and cards: no file is
opened, and the caller runs it once per corpus read.

Two grounds, one rule. *Files*: both documents name a repository path
(`Document.named_paths`, whether or not the file exists today — two plans
naming a file one will create share ground, and the fixture project has no
source tree). *Words*: the rare words of title and intent, a candidate and
never a verdict (ruling 3). On either ground, what a large share of the
project's live documents name is glue, not ground: the challenge before
build measured 199 file pairs on Needle's 63 documents through the few core
files every plan names, and a "two shared words" rule gave a median of 21
neighbours a document. The cut is a share of the live corpus read per
project on every read, never a hand-kept list, so `docs/plans/README.md`
drops out on its own and a live plan three documents cite stays.

Naming is citing (ruling 4), in every form a writer already uses: the
neighbour's card as `#N` anywhere, its Sequencing line, or the neighbour's
document path in the text, backticked or plain. The head counts a document
beside a file neighbour it does not name — but only one born once this
reader existed: fifty of Needle's 63 live documents were born blind before
any brief carried a neighbour, and fifty rows on the owner's pile is the
eight parked decisions §1 was shaped by, sixfold. Older documents show
their neighbours as a quiet fact.
"""

import math
import re
from datetime import date

from domain.card import Card
from domain.document import Document, DocumentKind, SuggestionKind
from domain.neighbour import Beside, Neighbour, NeighbourGround

COUNTED_FROM = date(2026, 9, 13)
"""The day this reader shipped: a document whose card was born on or after
it counts on the head when it names no neighbour, because its writer's
brief carried the neighbour (item 2). Earlier births were blind and are
shown, never counted (the challenge before build, 2026-09-12)."""

GLUE_SHARE = 0.08
"""A path or a word named by more than this share of a project's live
documents is glue, not ground. Measured 2026-09-12 over Needle (63 live
documents), Hello Revenue (224) and Omarchy (27): at this share Needle's
glue is its nine core files and two doctrine documents (`api/loops.py`,
`api/doors.py`, `board/assemble.py`, `docs/plans/README.md` …), a grounded
document has a median of three file neighbours (fifteen at most, from
twenty-five at 0.12), and a live plan three documents cite stays ground;
Hello Revenue's paths are spread so wide that nothing there is glue and
its median is four."""

GLUE_FLOOR = 6
"""The share never turns a path five documents name into glue on a small
board: fewer than this many namers is always ground. On Needle's 63
documents the share alone already asks for six, so this changes nothing
there; on the fixture's 22 it keeps a file four documents name as ground."""

SHOWN = 3
"""How many word candidates a document shows: the nearest, by score then
card number, so the list is the same on every read."""

WORD_FLOOR = 8.0
"""The rarity score a word candidate needs. A shared word scores
ln(N / namers), so on a board of sixty documents one word two share scores
about 3.4 and a word eight share about 2: a candidate needs two or three
rare words in common, or several ordinary ones. Measured 2026-09-12 at
this floor: read by their own words, 13 of Needle's 63 live documents find
a candidate, 141 of Hello Revenue's 224 and 3 of Omarchy's 27, never more
than three; at 3.0 every document found three, which is a list and not a
candidate; at 10.0 Needle found five."""

STOP_WORDS: frozenset[str] = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "is",
        "are",
        "it",
        "its",
        "that",
        "this",
        "when",
        "with",
        "by",
        "at",
        "as",
        "be",
        "not",
        "no",
        "one",
        "he",
        "his",
        "him",
        "you",
        "your",
        "we",
        "our",
        "from",
        "into",
        "than",
        "so",
        "what",
        "which",
        "who",
        "was",
        "were",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "about",
        "after",
        "before",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "because",
        "until",
        "while",
        "if",
        "but",
        "nor",
        "up",
        "down",
        "out",
        "off",
        "through",
        "between",
        "during",
        "without",
        "within",
        "along",
        "across",
        "behind",
        "toward",
        "towards",
        "every",
        "never",
        "nothing",
        "something",
        "anything",
        "someone",
        "everything",
    ]
)
"""English function words: never a ground. The project's own nouns — board,
card, session — are not listed; the frequency cut drops them per project,
because a hand-written list of a project's vocabulary drifts."""

_WORD = re.compile(r"[a-z][a-z'’-]{2,}")


def words_of(*texts: str | None) -> set[str]:
    """The distinctive words of a text: lower-cased, three letters or more,
    function words dropped, a light plural strip so "cards" and "card" are
    one word. Apostrophes are cut at the possessive."""
    found: set[str] = set()
    for text in texts:
        if not text:
            continue
        for word in _WORD.findall(text.lower()):
            word = word.split("'")[0].split("’")[0].strip("-")
            if len(word) < 3 or word in STOP_WORDS:
                continue
            if word.endswith("ies") and len(word) > 4:
                word = word[:-3] + "y"
            elif (
                word.endswith("es")
                and len(word) > 4
                and (word[-3] in "sxzo" or word[-4:-2] in ("ch", "sh"))
            ):
                word = word[:-2]
            elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
                word = word[:-1]
            found.add(word)
    return found


def _document_words(document: Document) -> set[str]:
    return words_of(document.title, document.essence)


def _glue(count: int, total: int) -> bool:
    return count >= GLUE_FLOOR and count > GLUE_SHARE * total


def _names(document: Document, other: Document, other_number: int) -> bool:
    """Whether `document` names `other` in any form a writer uses."""
    if other_number in document.named_cards:
        return True
    if any(s.number == other_number and s.words is None for s in document.sequenced):
        return True
    return other.stem in document.named_documents


def _neighbour(
    number: int,
    document: Document,
    *,
    ground: NeighbourGround,
    files: list[str],
    words: list[str],
    named: bool,
) -> Neighbour:
    return Neighbour(
        number=number,
        title=document.title,
        essence=document.essence,
        kind=document.kind,
        path=document.path,
        ground=ground,
        files=files,
        words=words,
        named=named,
        rulings=document.rulings,
    )


class Corpus:
    """One project's live documents with cards, indexed once per read: the
    ground each names after the glue is cut, and the weight of each word."""

    def __init__(self, pairs: list[tuple[Card, Document]]):
        self.pairs = [(card, document) for card, document in pairs if not document.archived]
        total = len(self.pairs)
        path_count: dict[str, int] = {}
        word_count: dict[str, int] = {}
        self.words: dict[int, set[str]] = {}
        for card, document in self.pairs:
            for path in set(document.named_paths):
                path_count[path] = path_count.get(path, 0) + 1
            words = _document_words(document)
            self.words[card.number] = words
            for word in words:
                word_count[word] = word_count.get(word, 0) + 1
        self.ground: dict[int, set[str]] = {
            card.number: {p for p in document.named_paths if not _glue(path_count[p], total)}
            for card, document in self.pairs
        }
        self.weight: dict[str, float] = {
            word: math.log(total / count)
            for word, count in word_count.items()
            if count > 1 and not _glue(count, total)
        }

    def by_words(self, words: set[str], *, but: int | None = None) -> list[Neighbour]:
        """The nearest documents to a set of words, as candidates: the
        rarity score of the words shared, above the floor, the top few in a
        fixed order. `but` leaves one card out — the document's own."""
        scored: list[tuple[float, int, Card, Document, list[str]]] = []
        for card, document in self.pairs:
            if card.number == but:
                continue
            shared = sorted(w for w in words & self.words[card.number] if w in self.weight)
            score = sum(self.weight[w] for w in shared)
            if shared and score >= WORD_FLOOR:
                scored.append((score, card.number, card, document, shared))
        scored.sort(key=lambda entry: (-entry[0], entry[1]))
        return [
            _neighbour(
                number, document, ground=NeighbourGround.WORDS, files=[], words=shared, named=False
            )
            for _, number, _, document, shared in scored[:SHOWN]
        ]

    def beside(self, card: Card, document: Document) -> Beside:
        """One document's neighbours: every other live document on its
        ground, with the files; when it names no ground, the nearest by
        words. The count only ever comes from files (ruling 3)."""
        mine = self.ground.get(card.number, set())
        neighbours: list[Neighbour] = []
        if mine:
            for other, theirs in self.pairs:
                if other.number == card.number:
                    continue
                shared = sorted(mine & self.ground[other.number])
                if shared:
                    neighbours.append(
                        _neighbour(
                            other.number,
                            theirs,
                            ground=NeighbourGround.FILES,
                            files=shared,
                            words=[],
                            named=_names(document, theirs, other.number),
                        )
                    )
            neighbours.sort(key=lambda n: n.number)
        else:
            for candidate in self.by_words(self.words.get(card.number, set()), but=card.number):
                other = next(d for c, d in self.pairs if c.number == candidate.number)
                neighbours.append(
                    candidate.model_copy(
                        update={"named": _names(document, other, candidate.number)}
                    )
                )
        unnamed = [
            n.number for n in neighbours if n.ground == NeighbourGround.FILES and not n.named
        ]
        born = card.born_at.date()
        counted = bool(unnamed) and born >= COUNTED_FROM
        return Beside(
            neighbours=neighbours,
            unnamed=unnamed,
            counted=counted,
            born=born,
            sentence=sentence_of(neighbours),
            clears=clears_of(document, unnamed) if counted else None,
        )


def beside_all(pairs: list[tuple[Card, Document]]) -> dict[int, Beside]:
    """Every live document's neighbours, by card number, in one read."""
    corpus = Corpus(pairs)
    return {card.number: corpus.beside(card, document) for card, document in corpus.pairs}


def _cards(numbers: list[int]) -> str:
    return ", ".join(f"#{n}" for n in numbers)


def _shown(files: list[str]) -> str:
    return ", ".join(files[:3]) + ("…" if len(files) > 3 else "")


def sentence_of(neighbours: list[Neighbour]) -> str | None:
    """The neighbours in one plain sentence for the face: the file
    neighbours with their ground and whether they are named, then the word
    candidates said as candidates; None when there are none."""
    if not neighbours:
        return None
    clauses: list[str] = []
    files = [n for n in neighbours if n.ground == NeighbourGround.FILES]
    unnamed = [n for n in files if not n.named]
    named = [n for n in files if n.named]
    if unnamed:
        ground = sorted({f for n in unnamed for f in n.files})
        clauses.append(
            f"sits beside {_cards([n.number for n in unnamed])} on {_shown(ground)} and does "
            f"not name {'it' if len(unnamed) == 1 else 'them'}"
        )
    if named:
        ground = sorted({f for n in named for f in n.files})
        clauses.append(f"names {_cards([n.number for n in named])} beside it on {_shown(ground)}")
    words = [n for n in neighbours if n.ground == NeighbourGround.WORDS]
    if words:
        clauses.append(
            f"near {_cards([n.number for n in words])} by its words — "
            f"{'a candidate' if len(words) == 1 else 'candidates'}, not a verdict"
        )
    return "; ".join(clauses) + "."


def clears_of(document: Document, unnamed: list[int]) -> str:
    """Who clears the count, by an act the board can see: the document
    comes to name the neighbour, carry it, or fold into it. For a defect
    that is the reading that verifies its mark; for anything else, the
    session Discuss or Plan puts on it (the challenge's correction: ranking
    edits nothing, so it cleared nothing)."""
    who = _cards(unnamed)
    if (
        document.kind == DocumentKind.SUGGESTION
        and document.suggestion_kind == SuggestionKind.DEFECT
    ):
        return f"the reading that verifies its mark folds it into {who} or cites {who} in the file"
    return (
        f"a session on it cites {who}, carries {who}, or folds this card into {who} — "
        "Discuss it and it can"
    )
