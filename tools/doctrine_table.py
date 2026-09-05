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

The same reader serves the tables that came after (card #60): a project's own
file read against the one text, whose rows take one of six stances, and the
one text's own paragraphs before a rewrite, whose rows say where each intent
went. `--stances` names the vocabulary a table is held to, and `--file-at`
reads the ruled file from a git revision, because the paragraphs a rewrite
departed from exist only in history once it lands:

    uv run python -m tools.doctrine_table --stances project-file \
        --file ~/Work/hellorevenue/CLAUDE.md --table docs/design/…md
    uv run python -m tools.doctrine_table --stances departed \
        --file-at d9a8eca:docs/HOW-WE-WORK.md --table docs/design/…md
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROW = re.compile(r"^#### (\d+)([a-z]?) · (.+?)\s*$", re.MULTILINE)
"""A row heading: `#### 12 · drop` or `#### 27b · machine fact`."""

EXTRA_ROW = re.compile(r"^#### ([A-Z]) · (.+?)\s*$", re.MULTILINE)
"""A lettered row: the plan's named extras, which rule on no paragraph."""

STANCE_SETS: dict[str, tuple[str, ...]] = {
    "two-texts": ("drop", "owner preference", "machine fact", "missing portable doctrine"),
    "project-file": (
        "the project's own",
        "global wins",
        "missing portable doctrine",
        "portable intent, project mechanism",
        "unproved claim",
        "contested",
    ),
    "departed": ("kept", "tightened", "moved", "dropped"),
}
"""The stance vocabularies, one per kind of table. `two-texts` is card #54's
(the former global file against the one text). `project-file` is the six
stances the suggestion on card #60 names for a project's own file. `departed`
is for a rewrite: every paragraph of the text before it is kept verbatim,
tightened in place, moved to a named section, or dropped with the reason —
so that brevity is never a deletion nobody saw."""

DEFAULT_FILE_AT = "7894dfc:home/.claude/CLAUDE.md"
"""Card #54's table ruled on the former global file as it stood on 2026-09-05
(287 lines, 60 paragraphs — the machine repository's commit 7894dfc, the last
before card 23 made the file a link to the one text), so a bare run reads it
from that history, never from the live path, which now counts the one text's
paragraphs and faults every row past its count."""
DEFAULT_TABLE = Path("docs/design/2026-09-05-the-two-texts-of-one-doctrine.md")
MACHINE_REPO = Path("~/Work/omarchy-machine").expanduser()


def paragraphs(text: str) -> list[str]:
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def text_at(revision_and_path: str, repo: Path | None = None) -> str:
    """`<rev>:<path>` read through git, so a table can be held to the file as
    it stood before the rewrite it accounts for; `repo` names another
    repository's history when the file is not this one's."""
    return subprocess.run(
        ["git", *(["-C", str(repo)] if repo else []), "show", revision_and_path],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def report(
    file: Path | None,
    table: Path,
    stances: tuple[str, ...],
    file_at: str | None = None,
    repo: Path | None = None,
) -> int:
    source = text_at(file_at, repo) if file_at else file.read_text(encoding="utf-8")
    blocks = paragraphs(source)
    file = Path(file_at) if file_at else file
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
            if stance not in stances:
                faults.append(
                    f"paragraph {number}: \"{stance}\" is not one of the {len(stances)} stances"
                )
    # A lettered row rules on no paragraph, so its stance is free text (card
    # #54's placements are "his ruling — …"); it is counted when it takes one
    # of the table's stances and left alone when it does not.
    counts = {stance: 0 for stance in stances}
    for entries in rows.values():
        for _, stance in entries:
            if stance in counts:
                counts[stance] += 1
    for _, stance in extras:
        if stance in counts:
            counts[stance] += 1
    print("  " + "; ".join(f"{stance} {counts[stance]}" for stance in stances))

    if faults:
        for fault in faults:
            print(f"  ✗ {fault}", file=sys.stderr)
        return 1
    print(f"  ✓ every one of the {len(blocks)} paragraphs is ruled on by a row")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="the ruled file, live")
    parser.add_argument("--file-at", help="read the ruled file as `<rev>:<path>` through git")
    parser.add_argument("--repo", type=Path, help="the repository `--file-at` reads from (default: this one)")
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--stances", choices=sorted(STANCE_SETS), default="two-texts")
    args = parser.parse_args(argv)
    file_at, repo = args.file_at, args.repo
    if args.file is None and file_at is None:
        file_at, repo = DEFAULT_FILE_AT, MACHINE_REPO
    return report(
        None if file_at else args.file.expanduser().resolve(),
        args.table.expanduser().resolve(),
        STANCE_SETS[args.stances],
        file_at,
        repo.expanduser() if repo else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
