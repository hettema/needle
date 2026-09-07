"""How many titles a cold reading could not place since a day, across every
project on the board: the reader behind card #74's WATCH signal.

The sweep of 2026-09-07 rewrote every live title to the bar; the loop the
plan wrote says a title the owner has to open a card for is the finding.
The cold reading applies his test on every board while the dial is on, and
its failing verdicts are the count a machine can read. Prints `none` when
no reading since the day failed, else the count and the cards, so a WATCH
row can expect `none`.

    uv run python tools/titles_unplaced.py --since 2026-09-08

Reads the store read-only and changes nothing.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from infrastructure.paths import db_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--since", required=True, help="YYYY-MM-DD; readings on or after this day")
    args = parser.parse_args()
    db = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
    rows = db.execute(
        "select project_slug, card_number, words from title_readings "
        "where verdict = 'unplaceable' and at >= ? order by at",
        (args.since,),
    ).fetchall()
    if not rows:
        print("none")
        return 0
    print(f"{len(rows)} unplaceable:")
    for slug, number, words in rows:
        print(f"  {slug} #{number}: {words}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
