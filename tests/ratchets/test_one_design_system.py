"""One design system, in frontend/src/components/ui/, and every surface built from it.

Outside that folder no file may name a raw colour, a class name, an inline
style, a bare form element, or a stylesheet of its own: a surface is composed
from the primitives and nothing else. Inside it, colour literals live in
tokens.css only. The comp seeded the tokens once; from then on this folder is
the single living source (docs/design/README.md).
"""

import re

from tests.ratchets.paths import FRONTEND_SRC, UI, frontend_files

RAW_COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|color-mix)\(")
PALETTE_CLASS = re.compile(
    r"\b(?:bg|text|border|ring|from|via|to|fill|stroke|outline|decoration|shadow|accent|caret|divide|place"
    r"holder)"
    r"-(?:red|blue|green|gray|grey|slate|zinc|neutral|stone|orange|amber|yellow|lime|emerald|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose|white|black)(?:-\d+)?\b"
)
ARBITRARY_COLOUR = re.compile(r"-\[(?:#|rgb|hsl)")
BARE_ELEMENT = re.compile(r"<(?:button|select|input|textarea)\b")
OWN_STYLING = re.compile(r"\bclassName\s*=|\bstyle\s*=\s*\{")


def _outside_ui() -> list:
    return [p for p in frontend_files() if UI not in p.parents]


def test_the_frontend_exists_with_its_design_system():
    assert (UI / "tokens.css").is_file(), "the design system's tokens are missing"


def test_no_raw_colour_outside_the_tokens():
    offenders: list[str] = []
    for path in frontend_files():
        if path == UI / "tokens.css":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if (
                RAW_COLOUR.search(line)
                or PALETTE_CLASS.search(line)
                or ARBITRARY_COLOUR.search(line)
            ):
                offenders.append(f"{path.relative_to(FRONTEND_SRC)}:{number}: {line.strip()}")
    assert not offenders, "raw colours outside components/ui/tokens.css:\n" + "\n".join(offenders)


def test_no_bespoke_primitive_outside_the_design_system():
    offenders: list[str] = []
    for path in _outside_ui():
        if path.suffix == ".css":
            offenders.append(
                f"{path.relative_to(FRONTEND_SRC)}: a stylesheet outside components/ui/"
            )
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if BARE_ELEMENT.search(line) or OWN_STYLING.search(line):
                offenders.append(f"{path.relative_to(FRONTEND_SRC)}:{number}: {line.strip()}")
    assert not offenders, "bespoke primitives or own styling outside components/ui/:\n" + "\n".join(
        offenders
    )
