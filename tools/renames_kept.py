"""Did every corpus rename keep its card? The reader behind card #20's WATCH
signal (plan 08, item 1).

For every project on the board, git's own record of renames under docs/plans
and docs/slice-suggestions since a day is read; for each, the card that
cites the new path is looked up. A rename the board followed leaves one card
citing both paths — the store appends the new path to the card's citations
on a rename — and a rename that birthed a second card leaves a card citing
the new path and none of the old. Archives (a live path moved under done/,
same stem) are renames git reports too and are not renames of identity, so
they are skipped: a card linked at the close cites the done/ path alone. Prints one number, the
renames that lost their card, so a WATCH row can expect 0.

    uv run python tools/renames_kept.py --since 2026-09-07

Reads the store read-only and runs one git command per project; changes
nothing.
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from infrastructure.paths import db_path  # noqa: E402
from runtime.git import CORPUS_FOLDERS  # noqa: E402


def renames_since(root: str, since: str) -> list[tuple[str, str]]:
    done = subprocess.run(
        [
            "git",
            "log",
            "-M",
            "--diff-filter=R",
            "--name-status",
            "--format=",
            f"--since={since}",
            "--",
            *CORPUS_FOLDERS,
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    pairs: list[tuple[str, str]] = []
    for line in done.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith("R"):
            pairs.append((parts[1], parts[2]))
    return pairs


def archived_path(path: str) -> str:
    """The same document under its folder's done/: docs/plans/x.md is
    docs/plans/done/x.md."""
    folder, name = path.rsplit("/", 1)
    return f"{folder}/done/{name}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--since", required=True, help="a day, YYYY-MM-DD")
    args = parser.parse_args(argv)
    con = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
    lost = 0
    for slug, root in con.execute("SELECT slug, path FROM projects"):
        if not Path(root).is_dir():
            continue
        cards = [
            (number, list(json.loads(citations)))
            for number, citations in con.execute(
                "SELECT number, citations FROM cards WHERE project_slug = ?", (slug,)
            )
        ]
        for old, new in renames_since(root, args.since):
            if new == archived_path(old):
                continue
            citing_new = [n for n, cited in cards if new in cited]
            citing_old = [n for n, cited in cards if old in cited]
            for number in citing_new:
                if number not in citing_old:
                    lost += 1
                    print(f"{slug} #{number} cites {new} and never {old}", file=sys.stderr)
    print(lost)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
