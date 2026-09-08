"""The board never names a model, a make or a tier it was not told.

**The boundary:** CLAUDE.md, "the board reads what runs; it never is the
thing that runs", and §8 of the one text — a claim stands on something the
board did, and a plausible shape is not knowledge. The ladder is the
machine's data, not Needle's (card #63): which models exist, which is
strongest and which the owner ruled into which tier is `claude-acct`'s
answer, read and shown. The board's job is to say what it was told and to
say plainly when it was told nothing.

**What it caught:** the board said `fable` for any row that recorded no
model — a guess for a terminal of the owner's, and a false claim for a
session of another make, which has no Claude rung at all. It said it in
three places (`board/lane.py` twice, `api/loops.py`, and the page's own
`model ?? "fable"`), each written separately, which is why a fourth was
always one reader away.

**Why a ratchet and not a convention:** the failure is silent. A guessed
rung reads exactly like a known one on the card, and the owner acts on it —
he ranks a card believing he knows who will drive it. Nothing else would
have caught the page's copy, which no Python test reads.
"""

import re

from tests.ratchets.paths import BACKEND_PACKAGES, REPO, frontend_files, python_files

CLAUDE_MODEL_NAMES = ("fable", "opus", "sonnet", "haiku")
"""Claude's model names. Needle names none of them: the one place a model's
word may appear is the answer the rule gave, which arrives as a string."""

# No file is exempt. The three readers that turn the machine's words into a
# rung — `runtime/rule.py`, `runtime/registry.py`, `runtime/handoffs.py` —
# pass the word through as a string and name none of them, so an exemption
# list would only be a place for the guess to come back.

_WORD = re.compile(r"[\"'](?:" + "|".join(CLAUDE_MODEL_NAMES) + r")[\"']")


def test_no_python_file_writes_a_claude_model_name_of_its_own():
    named: list[str] = []
    for path in python_files(*BACKEND_PACKAGES):
        relative = path.relative_to(REPO).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#") or '"""' in line:
                continue
            if _WORD.search(line):
                named.append(f"{relative}:{number}: {line.strip()}")
    assert not named, (
        "the runtime and the board name no Claude model of their own — the ladder is the "
        "machine's data and arrives in the rule's answer (card #63):\n" + "\n".join(named)
    )


def test_the_page_never_falls_back_to_a_model_for_a_row_that_recorded_none():
    named: list[str] = []
    for path in frontend_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "rung.ts" in path.as_posix():
                continue
            if _WORD.search(line) and ("??" in line or "||" in line or "model" in line):
                named.append(f"{path.name}:{number}: {line.strip()}")
    assert not named, (
        "the page says the slot alone for a row with no model; it never falls back to a "
        "model name (card #63):\n" + "\n".join(named)
    )
