"""Reading a plan or a suggestion from its text.

The corpus was written by hundreds of sessions over five months and no two
heads are identical: `## Intent`, `## Intent — what this achieves and why`,
`## 1. Intent`, a `**Status:**` line or none, a gate in either case. The
parser takes what is there and never demands a format of the corpus; a
document with no recognisable head is still a document with a title.
"""

import re
from datetime import date, datetime

from board.triage import fingerprint
from domain.document import (
    ColdRead,
    Disposition,
    Document,
    DocumentKind,
    Fate,
    Fix,
    FixMark,
    HeadField,
    Item,
    Review,
    ReviewPass,
    SequencedCard,
    Stance,
    SuggestionKind,
)
from domain.gate import Gate
from domain.handout import Handout

_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)
_HEAD_FIELD = re.compile(r"^\*\*([^*\n]+?):\*\*\s*(.*)$")
_GATE = re.compile(r"^\W*(low|medium|high|xhigh)\b\W*(.*)$", re.I | re.S)
_CARD_REF = re.compile(r"#(\d+)")
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
_INTENT_HEADING = re.compile(r"^(?:\d+\.\s*)?(?:the\s+)?intent\b", re.I)
_BREAKS_HEADING = re.compile(r"^(?:\d+\.\s*)?(?:the\s+)?intent\s+it\s+breaks\b", re.I)
"""A suggestion's section that names the intent the defect breaks (card
#74, item 4): the essence comes from here when the section exists, so the
line under a defect's title says what it is for and never where the code
is. `docs/plans/README.md` and the filing brief name the section."""
_CODE_MARK = "\x00"
_CODE_SHAPED = re.compile(
    r"\w+::\w+|\b\w+\(\)|(?<![\w/])[\w.-]+/[\w./-]+"
    r"|\b\w+\.(?:py|ts|tsx|md|json|toml|yaml|yml|sh)\b"
)
"""What must not reach the face of a closed card: a backtick, a
`module::function`, a `call()`, a path with a slash, a file name. A
sentence carrying one is the evidence's, not the intent's, and the next
sentence is tried."""
_FENCE = re.compile(r"^(```|~~~)")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_EMPH = re.compile(r"(?<!\w)(\*|_)(.+?)\1(?!\w)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_LIST_MARKER = re.compile(r"^(?:[-*+>]|\d+[.)])\s+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(`*])")
_SUGGESTION_PATH = re.compile(r"docs/slice-suggestions/(?:done/)?([\w.-]+?)\.md")
_KIND = re.compile(r"^\W*(defect|idea)\b", re.I)
_FIX = re.compile(r"^\W*(now|his|when)\b[ \t]*(.*)$", re.I | re.S)
r"""Only whitespace between the mark and its reason: a second `\W*` here ate
the reason's first character, and the character a mark's reason most often
starts with is a backtick around the source it cites — so the best-written
marks were the ones whose source nothing could find (plan 59's review). The
dashes and colons the corpus separates with are stripped below."""
"""The `Fix:` line's vocabulary (plan 11, item 2): the first word is the
mark; after `now` or `his` the rest is the why, after `when` the trigger.
Any other line is prose and the suggestion is unmarked."""
NO_FIX_LINE = "no Fix: line"
FIX_NOT_A_MARK = "Fix: line is not a mark"
TWO_FIX_LINES = "two Fix: lines"
_DEFECT_TITLE = re.compile(
    r"\b(?:does not|doesn'?t|do not|cannot|can'?t|never fires?|no longer|misses|is wrong|"
    r"fails?|escapes?|race|blind\w*|hole|bypass|broken|wrong|regression|crash\w*|bug|defect)\b",
    re.I,
)
"""A defect-shaped title, for a suggestion written before the `Kind:` line
existed (plan 06, item 2): what was built and got wrong, in the words such
titles use. Only read when no `Kind:` line says otherwise."""

_HANDS_OUT = re.compile(
    r"(?:^|(?<=[.!?:]\s)|(?<=\*\*)|(?<=\*\*\s))\*{0,2}hands out:\*{0,2}\s*(.+)$", re.I
)
"""The `Hands out:` sentence, at the head of its own line or beginning a
sentence at the end of an item's paragraph — never a mention of the sentence
in prose ("ends with a Hands out: sentence naming the role", as plan 12
itself says), which is what a match anywhere on the line read as a handout
to the role "sentence" (review pass 1). `machine burn` reads the same words."""
_ROLE = re.compile(r"^\W*([A-Za-z][\w-]*)")
_VERIFIES = re.compile(
    r"[;.]\s*(?:(?:the|and the)\s+(?:lane|session|executing session)\s+)?"
    r"verif(?:y|ies|ied|ying|ication)\s*(?:by|:)?\s*",
    re.I,
)
"""Where the verification starts: `; verifies <what>` as the README writes
it, and `; the lane verifies by <what>` as plan 13 wrote it before the
README fixed the form (review pass 1)."""
_ITEM_HEADING = re.compile(r"^(#{2,4})\s+(\d+)[.)]?\s+(.+?)\s*$")
_ITEM_LIST = re.compile(r"^\s{0,3}(\d+)[.)]\s+(.+?)\s*$")
_ITEM_BOLD_NUMBER = re.compile(r"^\*\*(\d+)[.)]\s+(.+?)\*\*\s*(.*)$")
"""The third shape Hello Revenue's plans use, found on the first live card
after the fold: a paragraph led by `**N. Title.**` with the number inside
the bold, numbered from 0 when a task 0 gates the rest. Read as a list
item whose bold lead is the title."""
_ITEM_BOLD = re.compile(r"^\*\*(.+?)\*\*")
ITEM_LABEL_MAX = 60
_STANCE = re.compile(r"(?:^\s*|(?<=[.!?]\s))\*\*(met|deviated):\*\*\s*(.*)$", re.I)
"""The stance a session writes at an item (plan 13, item 1): `**Met:** <what
shows it>` or `**Deviated:** <pointer>`, at the head of a line or beginning
a sentence, bold as the README writes it — a plain "met:" in prose is
prose. The last one in the item is the item's stance."""
_INLINE_MET = re.compile(r"✅|\[(?:DONE|SHIPPED)[^\]]*\]|\b(?:DONE|SHIPPED)\b")
"""The inline habit five months of archive already have: a tick, `[DONE
<date>]` or a bare DONE/SHIPPED on the item's own line reads as met, so the
archive reads right without a rewrite. Upper case only: "done means" is
the promise, not the stance."""
_DONE_MEANS = re.compile(
    r"(?:^\s*|(?<=[.!?:]\s)|(?<=\*\*)|(?<=\*\*\s))\*{0,2}done means:?\*{0,2}\s*(.+)$", re.I
)
_SENTENCE_MARKERS = re.compile(r"\*{0,2}(?:hands out|met|deviated):\*{0,2}", re.I)
"""Where an item's "done means" sentence stops: at the next sentence the
grammar names — the handout, or the stance."""
_TASK_HEADING = re.compile(r"\b(?:task|tasks|item|items|slice|slices|work|steps|breakdown)\b", re.I)
"""What a plan calls the section its task list sits under, across the
corpora: "Slices", "Items", "The work", "Task breakdown". A bold numbered
list under one of these is the task list even when a decision log or a
ruling list comes first in the file."""
_PLAN_STEM = re.compile(r"docs/plans/(?:done/)?([\w.-]+?)\.md")
_PASSES_HEADING = re.compile(r"^##\s+the passes\b", re.I)
_DISPOSITIONS_HEADING = re.compile(r"^##\s+dispositions\b", re.I)
_CLEAN = re.compile(r"\bnothing new\b|\bclean\b[.!]?\s*$", re.I)
"""A pass that found nothing: the record says "nothing new" or ends the
pass on the word clean, as every record under `docs/reviews/` does."""
_FATE = re.compile(
    r"(?:^|(?<=[—–:.;,(]\s)|(?<=[—–:.;,][\"')]\s)|(?<=\s-\s)|(?<=\())"
    r"(FIXED|NO CHANGE|NOT FIXED|FILED|CORRECTED|[Ff]iled)\b"
)
"""A finding's fate is the token that opens a clause of its line — the
whole line, or a segment after a dash, a colon, a full stop, a semicolon,
a comma or a bracket — and the last such token decides (card #110, ruling
4): "the earlier FIXED claim was wrong — NO CHANGE" is no change, "NOT
FIXED IN THE LANE — filed" is filed, and Needle's "**Title.** FIXED: …" is
fixed. A token inside prose ("the earlier FIXED claim", "PARTLY FIXED")
opens no clause and says nothing. The openers are the ones the three
corpora write (the cold read of the corpus table, 2026-09-10: thirty
all-caps FILED, three after a semicolon, one after a closing quote)."""
_FATES = {
    "FIXED": Fate.FIXED,
    "NO CHANGE": Fate.NO_CHANGE,
    "FILED": Fate.FILED,
    "CORRECTED": Fate.CORRECTED,
}
_CLASS = re.compile(r"^`?\[([\w-]+)\]`?\s*")
"""The class a finding opens with (card #60), plain or in backticks as
Hello Revenue writes it; stripped before the fate and the marks are read."""
_REPAIR_OF = re.compile(r"^\s*\[repair of\s+(\d+(?:\.\d+)?)\]", re.I)
"""The mark on a finding an earlier round's repair caused (card #110, item
3): the address of that repair, after the class and nowhere else — a line
that quotes the mark in its prose (this card's own record did) is not
marked (the author's re-read of pass two's round)."""
_PASS_FINDINGS = re.compile(r"^###\s+pass\s+(\d+)\b", re.I)
"""`### Pass N's findings`: the heading under `## Dispositions` that gives
the findings below it their pass, and so their address (card #110)."""
_VERDICT = re.compile(
    r"^\s*Read cold by\s+(?P<who>.+?)\s+on\s+(?P<commit>[^\s,]+),\s*call\s+(?P<call>\d+):\s*"
    r"(?P<rest>.*)$",
    re.I | re.S,
)
_VERDICT_OPENS = re.compile(r"^\s*Read cold by\b", re.I)
_BROKE = re.compile(
    r"^broke\s+(?P<addresses>[\d.,\s]+?)(?:\s*[—–-]\s*(?P<words>.*))?$", re.I | re.S
)
_COMPLETE = re.compile(r"^complete\b[.:]?\s*[—–-]?\s*(?P<words>.*)$", re.I | re.S)
_ADDRESS = re.compile(r"\d+(?:\.\d+)?")
"""A cold reader's verdict on a round (card #110, item 2), on a line of
its own under the pass whose round it read: `Read cold by <who> on <sha>,
call <n>: complete` or `…: broke <pass.finding>, … — <its words>`. Read
apart from the pass's own text, so a verdict never changes whether the
pass reads clean."""
_INTEGER = re.compile(r"\d+")

ESSENCE_MAX = 280


def stem_of(filename: str) -> str:
    return filename[:-3] if filename.endswith(".md") else filename


def _title_from_stem(stem: str) -> str:
    bare = _DATE.sub("", stem)
    return bare.replace("-", " ").strip().capitalize() or stem


def _date_from_stem(stem: str) -> date | None:
    match = _DATE.match(stem)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def head_fields_of(text: str) -> list[HeadField]:
    """`**Key:** value` lines before the first section, continuation lines
    joined: the one head reader every document the board reads goes
    through, a plan's, a suggestion's and a project's focus (card #87)."""
    fields: list[HeadField] = []
    for line in text.split("\n"):
        if line.startswith("## ") or line.strip() == "---":
            break
        match = _HEAD_FIELD.match(line.strip())
        if match:
            fields.append(HeadField(key=match.group(1).strip(), value=match.group(2).strip()))
        elif fields and line.strip() and not line.startswith("#"):
            fields[-1].value = f"{fields[-1].value} {line.strip()}".strip()
    return fields


def _field(fields: list[HeadField], key: str) -> str | None:
    for field in fields:
        if field.key.lower() == key.lower():
            return field.value
    return None


def _gate(value: str | None) -> tuple[Gate | None, str | None]:
    if value is None:
        return None, None
    match = _GATE.match(value)
    if not match:
        return None, value.strip() or None
    level = Gate(match.group(1).lower())
    why = match.group(2).strip().lstrip("—-–:, ").strip()
    return level, why or None


def _intent(text: str) -> tuple[str | None, str]:
    headings = list(_H2.finditer(text))
    if not headings:
        body = text
        first_h1 = _H1.search(text)
        if first_h1:
            body = text[first_h1.end() :]
        return None, _strip_head(body).strip()
    chosen = next(
        (h for h in headings if _BREAKS_HEADING.match(h.group(1))),
        next((h for h in headings if _INTENT_HEADING.match(h.group(1))), headings[0]),
    )
    start = chosen.end()
    following = [h for h in headings if h.start() > chosen.start()]
    end = following[0].start() if following else len(text)
    return chosen.group(1), text[start:end].strip()


def _strip_head(body: str) -> str:
    """Drop the head fields from a headless document so the body is prose."""
    lines = body.split("\n")
    out: list[str] = []
    in_head = True
    for line in lines:
        if in_head and (_HEAD_FIELD.match(line.strip()) or not line.strip()):
            continue
        in_head = False
        out.append(line)
    return "\n".join(out)


def _plain(markdown: str) -> str:
    text = _INLINE_CODE.sub(lambda m: m.group(1), markdown)
    text = _LINK.sub(lambda m: m.group(1), text)
    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _EMPH.sub(lambda m: m.group(2), text)
    return " ".join(text.split())


def _paragraphs(body: str) -> list[str]:
    """The body's prose paragraphs in order: fences, headings, head fields
    and tables are not prose, and a list item is a paragraph of its own."""
    paragraphs: list[str] = []
    paragraph: list[str] = []
    in_fence = False
    for line in body.split("\n") + [""]:
        if _FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            if paragraph:
                paragraphs.append(" ".join(paragraph))
                paragraph = []
            continue
        if stripped.startswith("#") or _HEAD_FIELD.match(stripped) or stripped.startswith("|"):
            if paragraph:
                paragraphs.append(" ".join(paragraph))
                paragraph = []
            continue
        paragraph.append(_LIST_MARKER.sub("", stripped).strip() or stripped)
    return paragraphs


def _first_paragraph(body: str) -> str | None:
    paragraphs = _paragraphs(body)
    return paragraphs[0] if paragraphs else None


def suggestion_kind_of(
    kind: DocumentKind, kind_line: str | None, title: str, found_by: str | None
) -> SuggestionKind | None:
    """A suggestion's kind: its `Kind:` line when it has one; otherwise a
    guess from its text where the text can tell — a `Found by` naming a
    review (the rings rule files defects from reviews) or a defect-shaped
    title — and idea otherwise. A plan has no kind."""
    if kind != DocumentKind.SUGGESTION:
        return None
    if kind_line:
        match = _KIND.match(kind_line)
        if match:
            return SuggestionKind(match.group(1).lower())
    if found_by and re.search(r"\breview", found_by, re.I):
        return SuggestionKind.DEFECT
    if _DEFECT_TITLE.search(title):
        return SuggestionKind.DEFECT
    return SuggestionKind.IDEA


def fix_of(kind: DocumentKind, fields: list[HeadField]) -> tuple[Fix | None, str | None]:
    """A suggestion's `Fix:` mark from its head, or why it is unmarked (plan
    11, item 2). The head only — a `**Fix:**` line under a section is prose
    that says what was fixed, not a mark. One mark, one document: a head
    carrying two `Fix:` lines is unmarked with both quoted, so the ratchet
    and `needle kinds` can name them. A plan carries no mark."""
    if kind != DocumentKind.SUGGESTION:
        return None, None
    lines = [f.value for f in fields if f.key.lower() == "fix"]
    if not lines:
        return None, NO_FIX_LINE
    if len(lines) > 1:
        return None, f"{TWO_FIX_LINES}: " + " / ".join(f"Fix: {line}" for line in lines)
    match = _FIX.match(lines[0])
    if not match:
        return None, f"{FIX_NOT_A_MARK}: Fix: {lines[0]}"
    mark = FixMark(match.group(1).lower())
    rest = match.group(2).strip().lstrip("—-–:, ").strip() or None
    if mark == FixMark.WHEN:
        return Fix(mark=mark, why=None, trigger=rest), None
    return Fix(mark=mark, why=rest, trigger=None), None


def _item_words(title: str) -> str:
    """An item's title as words: the bold lead when the line has one, the
    inline stance habit stripped, the marks and the trailing stop gone."""
    bold = _ITEM_BOLD.match(title)
    words = _plain(_INLINE_MET.sub("", bold.group(1) if bold else title))
    return words.strip().rstrip(".:—-– ").strip()


def _item_label(number: str, title: str) -> str:
    words = _item_words(title)
    if len(words) > ITEM_LABEL_MAX:
        words = words[: ITEM_LABEL_MAX - 1].rstrip() + "…"
    return f"{number}. {words}" if words else number


def _handout(sentence: str, item: str | None) -> Handout | None:
    text = _plain(sentence).strip()
    role = _ROLE.match(text)
    if not role:
        return None
    rest = text[role.end() :].strip().lstrip("—-–:, ").strip()
    split = _VERIFIES.search(rest)
    what = rest[: split.start()].strip() if split else rest
    verifies = rest[split.end() :].strip().rstrip(".") if split else None
    return Handout(
        item=item, role=role.group(1).lower(), what=what.rstrip("."), verifies=verifies or None
    )


def _paragraph_ends(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or _FENCE.match(stripped) is not None
        or _ITEM_LIST.match(line) is not None
        or _LIST_MARKER.match(stripped) is not None
        or _HEAD_FIELD.match(stripped) is not None
    )


_SEQUENCING_FILLER = re.compile(
    r"^(?:\s*(?:(?:after|behind|once|waits?\s+on|depends?\s+on|follows?|cards?|then|and|also|"
    r"both|the)\b|[,;&]))*\s*",
    re.I,
)
"""What may stand between the card names on a Sequencing line without being
prose: the words that say "after" and the separators between names."""
_SEQUENCING_CARD = re.compile(
    r"^((?:[A-Za-z][\w'’-]*\s+){0,2})#(\d+)\b\s*(?:\((?:[^()]|\([^()]*\))*\))?\s*"
)
"""One name: up to two words (a project's), the `#N`, and a parenthesis the
plan may hang on it — "Needle #20 (Needle's plan 08, whose item 2 …)"."""


def sequenced_cards_of(line: str | None) -> list[SequencedCard]:
    """The cards a `Sequencing:` line names first, in order, each with the
    words before its `#` as written (the plan "as many lanes as the machine
    can hold", item 2). The names lead and the prose follows: the reading
    stops at the first thing that is neither a name, a filler word nor a
    separator, so "after #222 (shipped), and after #235 folds — it fixes …"
    names two cards, and "the lane's migration … the live plan for #384 …"
    names none. Whether the words before a `#` are a project's is the
    board's to say (`board/sequencing.py`)."""
    if not line:
        return []
    rest = line
    found: list[SequencedCard] = []
    while True:
        rest = _SEQUENCING_FILLER.sub("", rest, count=1)
        match = _SEQUENCING_CARD.match(rest)
        if match is None:
            return found
        words = match.group(1).strip() or None
        found.append(SequencedCard(words=words, number=int(match.group(2))))
        rest = rest[match.end() :]


def handouts_of(text: str) -> list[Handout]:
    """Every `Hands out:` sentence in the body, each attributed to the item
    it ends: the last numbered heading or numbered list line before it
    (plan 12, item 2). The corpus numbers items as `### 1. Title`, `## 1.`
    and `1. **Title.**`, so all three are items; a sentence runs to the end
    of its paragraph, since plans wrap at eighty columns; fenced code is
    not read."""
    found: list[Handout] = []
    item: str | None = None
    in_fence = False
    lines = text.split("\n")
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if _FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _ITEM_HEADING.match(line)
        listed = _ITEM_LIST.match(line) if heading is None else None
        if heading:
            item = _item_label(heading.group(2), heading.group(3))
        elif listed:
            item = _item_label(listed.group(1), listed.group(2))
        match = _HANDS_OUT.search(line)
        if not match:
            continue
        sentence = [match.group(1)]
        while index < len(lines) and not _paragraph_ends(lines[index]):
            sentence.append(lines[index].strip())
            index += 1
        handout = _handout(" ".join(sentence), item)
        if handout is not None:
            found.append(handout)
    return found


def _unfenced(text: str) -> list[str | None]:
    """The document's lines with every fenced line replaced by None, so a
    reader can keep line numbers while never reading an example."""
    out: list[str | None] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE.match(line.strip()):
            in_fence = not in_fence
            out.append(None)
            continue
        out.append(None if in_fence else line)
    return out


def _sentence_to_paragraph_end(lines: list[str | None], index: int, first: str) -> str:
    """A sentence that begins on `lines[index]` and runs to the end of its
    paragraph, as `handouts_of` reads a handout: plans wrap at eighty."""
    parts = [first]
    index += 1
    while index < len(lines):
        line = lines[index]
        if line is None or _paragraph_ends(line):
            break
        parts.append(line.strip())
        index += 1
    return " ".join(parts)


def _item(number: int, title_line: str, rest_of_line: str, body: list[str | None]) -> Item:
    """One item from its title line and the lines under it: its words, its
    "done means" sentence, and its stance — the last `**Met:**` or
    `**Deviated:**` written in it, else the inline habit on its own line."""
    title = _item_words(title_line)
    stance: Stance | None = None
    text: str | None = None
    if _INLINE_MET.search(title_line):
        stance = Stance.MET
        tail = _plain(_INLINE_MET.sub("", rest_of_line)).strip().lstrip("—-–:, ").strip()
        # A stop left standing alone where the word was: "keywords? ." is "keywords?".
        tail = re.sub(r"\s+(?=[.,;:!?])", "", tail).strip(".").strip()
        text = tail or None
    done_means: str | None = None
    # A list item's line carries its sentences after the bold lead — "5.
    # **Reporting.** Done means: …" — so the rest of that line is read with
    # the lines under it.
    lines: list[str | None] = [rest_of_line, *body]
    for offset, line in enumerate(lines):
        if line is None:
            continue
        marked = _STANCE.search(line)
        if marked:
            stance = Stance(marked.group(1).lower())
            said = _sentence_to_paragraph_end(lines, offset, marked.group(2))
            text = _plain(said).strip() or None
            continue
        promised = _DONE_MEANS.search(line)
        if promised and done_means is None:
            sentence = _sentence_to_paragraph_end(lines, offset, promised.group(1))
            cut = _SENTENCE_MARKERS.search(sentence)
            done_means = _plain(sentence[: cut.start()] if cut else sentence).strip() or None
    return Item(number=number, title=title, done_means=done_means, stance=stance, text=text)


def _heading_items(lines: list[str | None]) -> list[Item]:
    """Items as `### N. Title` sections: the numbered headings at the deepest
    level the document numbers, so `## 1. Intent` — a corpus variant of the
    intent heading — is a section and not an item when `### 1.` items exist
    under it. An item runs to the next heading of any level."""
    numbered = [
        (index, m)
        for index, line in enumerate(lines)
        if line is not None and (m := _ITEM_HEADING.match(line))
    ]
    if not numbered:
        return []
    deepest = max(len(m.group(1)) for _, m in numbered)
    starts = [(index, m) for index, m in numbered if len(m.group(1)) == deepest]
    items: list[Item] = []
    for index, m in starts:
        end = index + 1
        while end < len(lines) and not (lines[end] is not None and lines[end].startswith("#")):
            end += 1
        rest = m.group(3)
        bold = _ITEM_BOLD.match(rest)
        after = rest[bold.end() :] if bold else ""
        items.append(_item(int(m.group(2)), rest, after, lines[index + 1 : end]))
    return items


_TOP_ENTRY = re.compile(r"^(\d+)[.)]\s+(.+?)\s*$")
"""A record's entry — a pass, a finding — opens at the margin. An entry
indented under another is that entry's own list (a pass's findings
written under it, as Hello Revenue's campaign record of 2026-09-08 does),
and reading it as a pass counted 157 passes on a record with 22 (card
#110, ruling 4)."""


def _numbered_entries(
    lines: list[str | None], *, start: int = 0
) -> list[tuple[int, int, str, list[str | None]]]:
    """Top-level `N. text` entries with the lines under each, up to the next
    entry or heading: the shape of a record's passes and of its
    dispositions. Each is (line index in the document, number, first
    line's text, body); `start` is where `lines` begins in the document."""
    entries: list[tuple[int, int, str, list[str | None]]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        listed = _TOP_ENTRY.match(line) if line is not None else None
        if listed is None:
            index += 1
            continue
        end = index + 1
        while end < len(lines):
            nxt = lines[end]
            if nxt is not None and (_TOP_ENTRY.match(nxt) or nxt.startswith("#")):
                break
            end += 1
        entries.append(
            (start + index, int(listed.group(1)), listed.group(2), lines[index + 1 : end])
        )
        index = end
    return entries


def _listed(line: str) -> tuple[int, str, re.Match[str] | None] | None:
    """A line that opens a list item, in either list shape: `N. **Title.**`
    or `**N. Title.**`. The number, the rest of the line, and the bold lead
    within it when there is one."""
    plain = _ITEM_LIST.match(line)
    if plain:
        return int(plain.group(1)), plain.group(2), _ITEM_BOLD.match(plain.group(2))
    bold_number = _ITEM_BOLD_NUMBER.match(line)
    if bold_number:
        rest = f"**{bold_number.group(2)}**{bold_number.group(3)}"
        return int(bold_number.group(1)), rest, _ITEM_BOLD.match(rest)
    return None


def _opens_entry(line: str) -> bool:
    return line.startswith("#") or _listed(line) is not None


def _list_runs(lines: list[str | None]) -> list[tuple[str, list[Item]]]:
    """Every run of consecutive top-level numbers that starts at a bold 0 or
    1, each with the heading it sits under. A heading or a break in the
    numbering ends a run. A plain numbered list — acceptance criteria, a
    ruling's reasons — starts no run, which is what the bold lead decides."""
    runs: list[tuple[str, list[Item]]] = []
    heading = ""
    items: list[Item] = []
    expected = 0
    for index, line in enumerate(lines):
        if line is None:
            continue
        if line.startswith("#"):
            if items:
                runs.append((heading, items))
                items = []
            heading = line.lstrip("#").strip()
            expected = 0
            continue
        listed = _listed(line)
        if listed is None:
            continue
        number, rest, bold = listed
        opens = number in (0, 1) and bold is not None
        if not items and not opens:
            continue
        if items and number != expected:
            runs.append((heading, items))
            items = []
            if not opens:
                continue
        end = index + 1
        while end < len(lines):
            nxt = lines[end]
            if nxt is not None and _opens_entry(nxt):
                break
            end += 1
        after = rest[bold.end() :] if bold else ""
        items.append(_item(number, rest, after, lines[index + 1 : end]))
        expected = number + 1
    if items:
        runs.append((heading, items))
    return runs


def _list_items(lines: list[str | None]) -> list[Item]:
    """Items as a top-level `1. **Title.**` list or a `**1. Title.**`
    paragraph, Hello Revenue's shapes: the bold run under the section a
    plan calls its tasks, slices, items or work when it has one — a
    decision log or a ruling list can come first in the file — else the
    first bold run."""
    runs = _list_runs(lines)
    named = next((items for heading, items in runs if _TASK_HEADING.search(heading)), None)
    return named if named is not None else (runs[0][1] if runs else [])


def items_of(text: str) -> list[Item]:
    """A plan's task list with each item's stance (plan 13, item 1), in
    either shape the corpora use: `### N. Title` sections as Needle's plans,
    else a top-level `N. **Title.**` list as Hello Revenue's. Headings win
    when a document has both, since Needle's rulings are a bold numbered
    list under a plan whose items are headings. Fenced code is not read."""
    lines = _unfenced(text)
    return _heading_items(lines) or _list_items(lines)


def _section_span(lines: list[str | None], heading: re.Pattern[str]) -> tuple[int, int] | None:
    """Where the first `## ` heading matching sits: the index of its first
    body line and the index of the next `## ` (or the end); None when the
    document has no such section."""
    start = next(
        (i for i, line in enumerate(lines) if line is not None and heading.match(line)), None
    )
    if start is None:
        return None
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line is not None and line.startswith("## "):
            break
        end += 1
    return start + 1, end


def _section(lines: list[str | None], heading: re.Pattern[str]) -> list[str | None]:
    """The lines under the first `## ` heading matching, up to the next `## `."""
    span = _section_span(lines, heading)
    return [] if span is None else lines[span[0] : span[1]]


def _lead_and_rest(first: str, body: list[str | None]) -> tuple[str, str]:
    """An entry's bold lead as its name, and everything else as its text."""
    bold = _ITEM_BOLD.match(first)
    lead = bold.group(1) if bold else _SENTENCE_END.split(first, maxsplit=1)[0]
    rest = first[bold.end() :] if bold else first[len(lead) :]
    tail = " ".join(line.strip() for line in body if line is not None and line.strip())
    return _plain(lead).strip().rstrip(".:—-– "), _plain(f"{rest} {tail}").strip().lstrip("—-–:, ")


def plan_stem_of(record_text: str) -> str | None:
    """The stem of the plan a review record's `**Plan:**` line names, from
    the head alone: how a lane's record is told from the others before any
    of them is parsed whole (thirteen records cost 7 ms parsed, under 1 ms
    matched by head)."""
    match = _PLAN_STEM.search(_field(head_fields_of(record_text), "Plan") or "")
    return match.group(1) if match else None


def review_of(text: str, path: str) -> Review:
    """A review record's counts (plan 13, item 5), in the shape
    `docs/reviews/README.md` prescribes: the plan its head names, the
    findings count from `**Findings:**`, one pass per numbered entry under
    `## The passes` — clean when it says nothing new — and each entry under
    `## Dispositions` as FIXED, NO CHANGE or filed. A record without a
    section simply has none of that section's counts."""
    fields = head_fields_of(text)
    plan_stem = plan_stem_of(text)
    findings_line = _field(fields, "Findings") or ""
    count = _INTEGER.search(findings_line)
    lines = _unfenced(text)
    passes: list[ReviewPass] = []
    verdicts: list[ColdRead] = []
    span = _section_span(lines, _PASSES_HEADING)
    if span is not None:
        for index, number, first, body in _numbered_entries(
            lines[span[0] : span[1]], start=span[0]
        ):
            own, read = _verdicts_apart(body, start=index + 1)
            lens, rest = _lead_and_rest(first, own)
            passes.append(
                ReviewPass(
                    number=number, lens=lens, text=rest, clean=_CLEAN.search(rest) is not None
                )
            )
            verdicts.extend(_verdict(number, line, words) for line, words in read)
    dispositions = _dispositions(lines)
    fixed = sum(1 for d in dispositions if d.fate == Fate.FIXED)
    no_change = sum(1 for d in dispositions if d.fate == Fate.NO_CHANGE)
    filed_names = [d.name for d in dispositions if d.fate == Fate.FILED]
    # The loop's unit (card #110, ruling 8, as pass two's reader refined
    # it): caught is every address a cold reader broke, once; escaped is
    # every marked finding a full pass made whose repair no reader had
    # broken by then — a finding, not an address, so two findings on one
    # repair are two escapes, as the baseline counted them.
    caught = {address for v in verdicts for address in v.broke}
    broken_by = {}
    for v in verdicts:
        for address in v.broke:
            broken_by[address] = min(broken_by.get(address, v.pass_number), v.pass_number)
    escaped = sum(
        1
        for d in dispositions
        if d.repair_of is not None
        and (
            d.repair_of not in broken_by
            or (d.pass_number is not None and broken_by[d.repair_of] > d.pass_number)
        )
    )
    return Review(
        path=path,
        plan_stem=plan_stem,
        passes=passes,
        clean=bool(passes) and passes[-1].clean,
        found=int(count.group(0)) if count else 0,
        fixed=fixed,
        no_change=no_change,
        filed=len(filed_names),
        filed_names=filed_names,
        dispositions=dispositions,
        verdicts=verdicts,
        caught=len(caught),
        escaped=escaped,
    )


def _verdicts_apart(
    body: list[str | None], *, start: int
) -> tuple[list[str | None], list[tuple[int, str]]]:
    """A pass's body split into its own lines and its verdict lines (card
    #110, item 2): a verdict opens with `Read cold by` and runs to the next
    blank line, another verdict or the body's end, so a wrapped one is read
    whole. Each verdict is (line number, its text joined)."""
    own: list[str | None] = []
    read: list[tuple[int, str]] = []
    index = 0
    while index < len(body):
        line = body[index]
        if line is None or not _VERDICT_OPENS.match(line):
            own.append(line)
            index += 1
            continue
        parts = [line.strip()]
        end = index + 1
        while end < len(body):
            nxt = body[end]
            if nxt is None or not nxt.strip() or _VERDICT_OPENS.match(nxt):
                break
            parts.append(nxt.strip())
            end += 1
        read.append((start + index + 1, " ".join(parts)))
        index = end
    return own, read


def _verdict(pass_number: int, line: int, words: str) -> ColdRead:
    """One verdict line as `docs/reviews/README.md` writes it. A line that
    opens as a verdict but is not in the form is kept with no call and no
    commit, so the door can name it rather than miss it."""
    match = _VERDICT.match(words)
    if match is None:
        return ColdRead(
            pass_number=pass_number,
            line=line,
            who="",
            commit="",
            call=0,
            complete=False,
            broke=[],
            words=_plain(words),
        )
    rest = match.group("rest").strip()
    complete = _COMPLETE.match(rest)
    broke = _BROKE.match(rest)
    if complete is not None:
        return ColdRead(
            pass_number=pass_number,
            line=line,
            who=match.group("who").strip(),
            commit=match.group("commit"),
            call=int(match.group("call")),
            complete=True,
            broke=[],
            words=_plain(complete.group("words") or ""),
        )
    if broke is not None:
        return ColdRead(
            pass_number=pass_number,
            line=line,
            who=match.group("who").strip(),
            commit=match.group("commit"),
            call=int(match.group("call")),
            complete=False,
            broke=_ADDRESS.findall(broke.group("addresses")),
            words=_plain(broke.group("words") or ""),
        )
    return ColdRead(
        pass_number=pass_number,
        line=line,
        who=match.group("who").strip(),
        commit=match.group("commit"),
        call=int(match.group("call")),
        complete=False,
        broke=[],
        words=_plain(rest),
    )


def _dispositions(lines: list[str | None]) -> list[Disposition]:
    """Every finding under `## Dispositions` with its pass — from the `###
    Pass N` heading above it — its fate, its two halves and its repair
    mark (card #110). The fate is the last clause-opening token of the
    line; the halves are read after it."""
    span = _section_span(lines, _DISPOSITIONS_HEADING)
    if span is None:
        return []
    found: list[Disposition] = []
    pass_number: int | None = None
    index = span[0]
    section = lines[span[0] : span[1]]
    entries = {i: (n, f, b) for i, n, f, b in _numbered_entries(section, start=span[0])}
    while index < span[1]:
        line = lines[index]
        if line is not None and line.startswith("###"):
            heading = _PASS_FINDINGS.match(line)
            pass_number = int(heading.group(1)) if heading else None
        if index in entries:
            number, first, body = entries[index]
            found.append(_disposition(index + 1, pass_number, number, first, body))
        index += 1
    return found


def _disposition(
    line: int, pass_number: int | None, number: int, first: str, body: list[str | None]
) -> Disposition:
    tail = " ".join(line.strip() for line in body if line is not None and line.strip())
    classed = _CLASS.match(first)
    unclassed = _CLASS.sub("", first)
    name, _ = _lead_and_rest(_REPAIR_OF.sub("", unclassed).strip(), [])
    text = _plain(f"{unclassed} {tail}".strip())
    repair = _REPAIR_OF.search(text)
    fate: Fate | None = None
    after = ""
    for match in _FATE.finditer(text):
        fate = _FATES.get(match.group(1).upper())
        after = text[match.end() :]
    # The halves are clauses after the fate, split at the semicolons the
    # README writes between them, each read by its first word; a clause
    # with a head and no words is an empty half, never the next clause's
    # words (pass three's reader: `reaches ; assumes …` read the assumes
    # clause as the reach).
    reaches: str | None = None
    assumes: str | None = None
    if fate is Fate.FIXED:
        for clause in after.split(";"):
            head, _, body = clause.strip().partition(" ")
            body = body.strip().rstrip(".")
            if head.lower() == "reaches" and reaches is None:
                reaches = body or None
            elif head.lower() == "assumes" and assumes is None:
                assumes = body or None
    return Disposition(
        number=number,
        pass_number=pass_number,
        address=f"{pass_number}.{number}" if pass_number is not None else str(number),
        line=line,
        name=name,
        text=text,
        fate=fate,
        reaches=reaches,
        assumes=assumes,
        repair_of=repair.group(1) if repair else None,
        finding_class=classed.group(1).lower() if classed else None,
    )


def cites_of(fields: list[HeadField]) -> list[str]:
    """The suggestion stems a document's head names, in order, each once:
    what a plan carries (plan 06, item 5). The head only — a plan's body
    names neighbouring suggestions in prose without carrying them."""
    seen: list[str] = []
    for field in fields:
        for stem in _SUGGESTION_PATH.findall(field.value):
            if stem not in seen:
                seen.append(stem)
    return seen


def essence_of(intent: str) -> str | None:
    """The first sentence of a document's intent that says what it is for,
    as plain text: the first sentence with no path, function name or
    backticked term in it (card #74, item 4). The line under a defect's
    title was the first sentence of its evidence — a path and a function
    name — because that is where a defect's body starts; a sentence about
    where the code is is skipped and the next one tried, through every
    paragraph, and a body with no such sentence has no essence rather than
    a wrong one."""
    for paragraph in _paragraphs(intent):
        # Backticks are kept as a marker through the plain rendering, so a
        # backticked word that is not path-shaped (`now`) still counts as code.
        marked = _INLINE_CODE.sub(lambda m: f"{_CODE_MARK}{m.group(1)}{_CODE_MARK}", paragraph)
        for raw in _SENTENCE_END.split(_plain(marked)):
            if _CODE_MARK in raw or _CODE_SHAPED.search(raw):
                continue
            sentence = raw.strip()
            if not sentence:
                continue
            if len(sentence) > ESSENCE_MAX:
                sentence = sentence[: ESSENCE_MAX - 1].rstrip() + "…"
            return sentence
    return None


def parse_document(
    text: str, *, kind: DocumentKind, path: str, archived: bool, read_at: datetime
) -> Document:
    stem = stem_of(path.rsplit("/", 1)[-1])
    h1 = _H1.search(text)
    title = " ".join(h1.group(1).split()) if h1 else _title_from_stem(stem)
    fields = head_fields_of(text)
    status = _field(fields, "Status")
    status_word = None
    if status:
        first = status.split()[0] if status.split() else ""
        status_word = first.strip("—-–:,.*").upper() or None
    gate, gate_why = _gate(_field(fields, "Effort gate"))
    card_value = _field(fields, "Card")
    card_match = _CARD_REF.search(card_value) if card_value else None
    heading, intent = _intent(text)
    found_by = _field(fields, "Found by")
    fix, fix_note = fix_of(kind, fields)
    sequencing = _field(fields, "Sequencing")
    return Document(
        kind=kind,
        stem=stem,
        path=path,
        archived=archived,
        title=title,
        date=_date_from_stem(stem),
        status=status,
        status_word=status_word,
        gate=gate,
        gate_why=gate_why,
        sequencing=sequencing,
        sequenced=sequenced_cards_of(sequencing) if kind == DocumentKind.PLAN else [],
        found_by=found_by,
        card_ref=int(card_match.group(1)) if card_match else None,
        suggestion_kind=suggestion_kind_of(kind, _field(fields, "Kind"), title, found_by),
        fix=fix,
        fix_note=fix_note,
        cites=cites_of(fields),
        handouts=handouts_of(text),
        items=items_of(text) if kind == DocumentKind.PLAN else [],
        head_fields=fields,
        fingerprint=fingerprint(text),
        intent_heading=heading,
        intent=intent,
        essence=essence_of(intent),
        read_at=read_at,
    )
