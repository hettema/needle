"""Reading a plan or a suggestion from its text.

The corpus was written by hundreds of sessions over five months and no two
heads are identical: `## Intent`, `## Intent — what this achieves and why`,
`## 1. Intent`, a `**Status:**` line or none, a gate in either case. The
parser takes what is there and never demands a format of the corpus; a
document with no recognisable head is still a document with a title.
"""

import re
from datetime import date, datetime

from domain.document import Document, DocumentKind, HeadField, SuggestionKind
from domain.gate import Gate

_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)
_HEAD_FIELD = re.compile(r"^\*\*([^*\n]+?):\*\*\s*(.*)$")
_GATE = re.compile(r"^\W*(low|medium|high|xhigh)\b\W*(.*)$", re.I | re.S)
_CARD_REF = re.compile(r"#(\d+)")
_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
_INTENT_HEADING = re.compile(r"^(?:\d+\.\s*)?(?:the\s+)?intent\b", re.I)
_FENCE = re.compile(r"^(```|~~~)")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_EMPH = re.compile(r"(?<!\w)(\*|_)(.+?)\1(?!\w)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_LIST_MARKER = re.compile(r"^(?:[-*+>]|\d+[.)])\s+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(`*])")
_SUGGESTION_PATH = re.compile(r"docs/slice-suggestions/(?:done/)?([\w.-]+?)\.md")
_KIND = re.compile(r"^\W*(defect|idea)\b", re.I)
_DEFECT_TITLE = re.compile(
    r"\b(?:does not|doesn'?t|do not|cannot|can'?t|never fires?|no longer|misses|is wrong|"
    r"fails?|escapes?|race|blind\w*|hole|bypass|broken|wrong|regression|crash\w*|bug|defect)\b",
    re.I,
)
"""A defect-shaped title, for a suggestion written before the `Kind:` line
existed (plan 06, item 2): what was built and got wrong, in the words such
titles use. Only read when no `Kind:` line says otherwise."""

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


def _head_fields(text: str) -> list[HeadField]:
    """`**Key:** value` lines before the first section, continuation lines joined."""
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
    chosen = next((h for h in headings if _INTENT_HEADING.match(h.group(1))), headings[0])
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


def _first_paragraph(body: str) -> str | None:
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
                return " ".join(paragraph)
            continue
        if stripped.startswith("#") or _HEAD_FIELD.match(stripped) or stripped.startswith("|"):
            if paragraph:
                return " ".join(paragraph)
            continue
        paragraph.append(_LIST_MARKER.sub("", stripped).strip() or stripped)
    return None


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
    """The first sentence of a document's intent, as plain text."""
    paragraph = _first_paragraph(intent)
    if not paragraph:
        return None
    sentence = _SENTENCE_END.split(_plain(paragraph), maxsplit=1)[0].strip()
    if len(sentence) > ESSENCE_MAX:
        sentence = sentence[: ESSENCE_MAX - 1].rstrip() + "…"
    return sentence or None


def parse_document(
    text: str, *, kind: DocumentKind, path: str, archived: bool, read_at: datetime
) -> Document:
    stem = stem_of(path.rsplit("/", 1)[-1])
    h1 = _H1.search(text)
    title = " ".join(h1.group(1).split()) if h1 else _title_from_stem(stem)
    fields = _head_fields(text)
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
        sequencing=_field(fields, "Sequencing"),
        found_by=found_by,
        card_ref=int(card_match.group(1)) if card_match else None,
        suggestion_kind=suggestion_kind_of(kind, _field(fields, "Kind"), title, found_by),
        cites=cites_of(fields),
        head_fields=fields,
        intent_heading=heading,
        intent=intent,
        essence=essence_of(intent),
        read_at=read_at,
    )
