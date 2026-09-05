"""Counts the paragraphs of an injected doctrine file against the rows of the
table that rules on them, and refuses to agree unless every paragraph is covered.

The table (`docs/design/2026-09-05-the-two-texts-of-one-doctrine.md`) exists so
that no sentence of the owner's constitution moves, merges or is dropped without
him seeing it. A table that quietly skipped a paragraph would look exactly like
a table that ruled on it, which is the failure this script exists to make
impossible: it reads the paragraphs from the file itself, the row ids from the
table, and says which paragraphs no row names.

A paragraph is a blank-line-separated block, headings included — the same count
the plan's evidence took (60 for the global file on 2026-09-05). Headings count
because a section title is content too: it either restates a HOW-WE-WORK title
or it does not, and a table that skipped titles would leave a section's name
unaccounted while claiming completeness.

A block may carry more than one row when its sentences take different stances
(a bullet list whose first bullet is this laptop's and whose third is doctrine).
Those rows are `27a`, `27b`, …; the script requires the letters of one block to
run from `a` with no gaps, so a dropped middle row cannot hide.

    uv run python -m tools.doctrine_table
    uv run python -m tools.doctrine_table --file ~/.claude/CLAUDE.md --table docs/design/…md
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROW = re.compile(r"^#### (\d+)([a-z]?) · (.+?)\s*$", re.MULTILINE)
"""A row heading: `#### 12 · drop` or `#### 27b · machine fact`."""

EXTRA_ROW = re.compile(r"^#### ([A-Z]) · (.+?)\s*$", re.MULTILINE)
"""A lettered row: the plan's named extras, which rule on no paragraph."""

STANCES = ("drop", "owner preference", "machine fact", "missing portable doctrine")

DEFAULT_FILE = Path("~/.claude/CLAUDE.md")
DEFAULT_TABLE = Path("docs/design/2026-09-05-the-two-texts-of-one-doctrine.md")


def paragraphs(text: str) -> list[str]:
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def report(file: Path, table: Path) -> int:
    blocks = paragraphs(file.read_text(encoding="utf-8"))
    text = table.read_text(encoding="utf-8")

    rows: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for number, letter, stance in ROW.findall(text):
        rows[int(number)].append((letter, stance))
    extras = EXTRA_ROW.findall(text)

    total_rows = sum(len(r) for r in rows.values())
    print(f"{file}: {len(blocks)} paragraphs")
    print(f"{table}: {total_rows} paragraph rows over {len(rows)} paragraphs, {len(extras)} extra rows")

    faults: list[str] = []

    missed = [n for n in range(1, len(blocks) + 1) if n not in rows]
    if missed:
        faults.append(f"paragraphs no row names: {missed}")
    beyond = sorted(n for n in rows if n > len(blocks))
    if beyond:
        faults.append(f"rows naming a paragraph the file does not have: {beyond}")

    for number, entries in sorted(rows.items()):
        letters = sorted(letter for letter, _ in entries)
        if len(entries) == 1:
            if letters != [""]:
                faults.append(f"paragraph {number}: a single row must carry no letter")
        else:
            expected = [chr(ord("a") + i) for i in range(len(entries))]
            if letters != expected:
                faults.append(
                    f"paragraph {number}: rows {letters} should run {expected} with no gaps"
                )
        for _, stance in entries:
            if stance not in STANCES:
                faults.append(f"paragraph {number}: \"{stance}\" is not one of the four stances")

    counts = {stance: 0 for stance in STANCES}
    for entries in rows.values():
        for _, stance in entries:
            if stance in counts:
                counts[stance] += 1
    print("  " + "; ".join(f"{stance} {counts[stance]}" for stance in STANCES))

    if faults:
        for fault in faults:
            print(f"  ✗ {fault}", file=sys.stderr)
        return 1
    print(f"  ✓ every one of the {len(blocks)} paragraphs is ruled on by a row")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    args = parser.parse_args(argv)
    return report(args.file.expanduser().resolve(), args.table.expanduser().resolve())


if __name__ == "__main__":
    raise SystemExit(main())
