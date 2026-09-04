"""Turning the light HTML Needle 0.1 kept in card text into plain text.

0.1 rendered rows with innerHTML, so its card file carries `<b>`, `<code>`,
`<li>` and `<span class="file">`. Needle stores plain text with two marks —
backticks for code and double asterisks for bold — and one inline renderer on
the page draws them. Storing HTML would have meant a second renderer and an
injection surface on a board that sessions write to.
"""

import html
import re

_FILE_SPAN = re.compile(r'<span class="file">(.*?)</span>', re.S)
_BOLD = re.compile(r"<(?:b|strong)>(.*?)</(?:b|strong)>", re.S)
_CODE = re.compile(r"<code>(.*?)</code>", re.S)
_EM = re.compile(r"<(?:em|i)>(.*?)</(?:em|i)>", re.S)
_LINK = re.compile(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S)
_LI = re.compile(r"<li[^>]*>", re.I)
_BLOCK_END = re.compile(r"</(?:li|ul|ol|p|div)>|<br\s*/?>|<(?:ul|ol|p|div)[^>]*>", re.I)
_ANY_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


def file_citations(text: str) -> list[str]:
    """The paths a 0.1 `deep` field cites, in order."""
    return [m.strip() for m in _FILE_SPAN.findall(text)]


def html_to_text(text: str) -> str:
    text = _FILE_SPAN.sub(lambda m: m.group(1).strip(), text)
    text = _BOLD.sub(lambda m: f"**{m.group(1).strip()}**", text)
    text = _CODE.sub(lambda m: f"`{m.group(1).strip()}`", text)
    text = _EM.sub(lambda m: f"_{m.group(1).strip()}_", text)
    text = _LINK.sub(lambda m: f"{m.group(2).strip()} ({m.group(1).strip()})", text)
    text = _LI.sub("\n- ", text)
    text = _BLOCK_END.sub("\n", text)
    text = _ANY_TAG.sub("", text)
    text = html.unescape(text)
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANK_LINES.sub("\n", text)
    return text.strip()


def prose_without_citations(deep: str) -> str:
    """A 0.1 `deep` field minus its file spans: the card's own longer note."""
    return html_to_text(_FILE_SPAN.sub("", deep))
