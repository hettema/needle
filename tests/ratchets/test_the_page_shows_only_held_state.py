"""The page never shows a state the store does not hold (plan item 4).

Board state on the page is set from one place: the response of a read or of
the move that was just persisted. No component may set it, and the word
"optimistic" may not appear — there is no optimistic rendering in Needle.
"""

import re

from tests.ratchets.paths import FRONTEND_SRC, frontend_files

STATE = FRONTEND_SRC / "state"


def test_board_state_is_set_only_from_the_stores_answers():
    offenders: list[str] = []
    for path in frontend_files():
        if STATE in path.parents:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bsetBoard\(|\boptimistic", line, re.I):
                offenders.append(f"{path.relative_to(FRONTEND_SRC)}:{number}: {line.strip()}")
    assert not offenders, "\n".join(offenders)
