"""No deferral markers anywhere in the code (CLAUDE.md: nothing ships half-done).

A marker in code is read by the next session as a pattern and extended. The
plans and the intent may sequence work across slices; the code may not defer.
CLAUDE.md names the markers it forbids, so it is the one file not scanned.
"""

import re

from tests.ratchets.paths import REPO, frontend_files, python_files

_MARKERS = [
    "TO" + "DO",
    "FIX" + "ME",
    "XX" + "X",
    "HA" + "CK",
    "TB" + "D",
    "later " + "slice",
    "for " + "now",
    "not " + "yet " + "implemented",
    "NotImplemented" + "Error",
    "place" + "holder",
    "temporary " + "fix",
    "quick " + "fix",
]
_PATTERN = re.compile("|".join(re.escape(m) for m in _MARKERS), re.I)


def _files() -> list:
    files = python_files("domain", "board", "infrastructure", "runtime", "api", "tests")
    files += frontend_files()
    files += [REPO / "README.md"]
    files += sorted((REPO / "frontend" / "tests").rglob("*.ts*"))
    return [f for f in files if f.is_file()]


def test_no_deferral_marker_in_code_or_working_rules():
    offenders: list[str] = []
    for path in _files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _PATTERN.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert not offenders, "deferral markers found:\n" + "\n".join(offenders)
