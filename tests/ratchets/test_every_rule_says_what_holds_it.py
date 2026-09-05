"""Every rule says what holds it, in three words and no fourth — and debt is called debt.

`docs/HOW-WE-WORK.md` is the one text every project reads. `docs/HOW-WE-HOLD-IT.md`
says, per rule section, what holds it: *Held by* a check that refuses, *Traced by*
evidence someone reads, or a *Convention because* its failure is loud. Hello
Revenue's register learned the fourth form the hard way: a marker for "nothing
holds this yet" was honest and closed nothing, because an implicit set of prose
strings shrinks by a tidying pass and looks like progress. So here a rule held by
nothing carries a debt line instead of a stance — *Undefended until* a card the
corpus has, by a date — and three things stop debt becoming a resting place: the
card must be live in the corpus, the date must not have passed, and the print
never adds debt into the held count (plan 18, item 4; ruling 7).

Two-way, so nothing can be tidied away: every rule section of HOW-WE-WORK has
exactly one line here, and every entry here names a section HOW-WE-WORK has. A
debt line names a corpus *path* rather than a card number because the ratchet
reads the repository and cannot read the store; the board maps the path to its
card. Kept beside the doctrine rather than inside it (owner ruling 2026-09-05):
the constitution's commit hook demands a card per edit, and stance lines change
every time a ratchet lands.
"""

import re
from datetime import date
from pathlib import Path

import pytest

from tests.ratchets.paths import REPO

DOCTRINE = REPO / "docs" / "HOW-WE-WORK.md"
REGISTER = REPO / "docs" / "HOW-WE-HOLD-IT.md"

SECTION = re.compile(r"^## (?!Part\b)(.+?)\s*$", re.MULTILINE)
"""A rule section: every `## ` heading that is not a Part label."""

STANCES = {
    "Held by": re.compile(r"^\*Held by:\*\s+(?P<target>\S+)"),
    "Traced by": re.compile(r"^\*Traced by:\*\s+\S"),
    "Convention because": re.compile(r"^\*Convention because:\*\s+\S"),
}
DEBT = re.compile(
    r"^\*Undefended until:\*\s+(?P<card>docs/(?:plans|slice-suggestions)/[^\s]+\.md)"
    r"(?:\s+by\s+(?P<date>\d{4}-\d{2}-\d{2}))?\s*(?:—|-)?\s*(?P<what>.*)$"
)
ANY_LINE = re.compile(r"^\*[A-Z][^*\n]*:\*")
"""Any italic label line under a section is read as its stance, so a fourth word
is refused by name rather than read as an absent line."""

CORPUS_LIVE = ("docs/plans/", "docs/slice-suggestions/")


def sections_of(text: str) -> list[str]:
    return [m.group(1) for m in SECTION.finditer(text)]


def entries_of(text: str) -> dict[str, list[str]]:
    """Section title → the stance/debt lines under it, in order."""
    found: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = SECTION.match(line)
        if heading:
            current = heading.group(1)
            found[current] = []
            continue
        if current is not None and ANY_LINE.match(line):
            found[current].append(line.rstrip())
    return found


def held_target_exists(target: str, repo: Path) -> bool:
    """`tests/ratchets/<file>.py`, or `<path>::<name>` where `def name(` is in the file."""
    if "::" in target:
        path, name = target.split("::", 1)
        file = repo / path
        return file.is_file() and re.search(rf"^\s*(async\s+)?def\s+{re.escape(name)}\(", file.read_text(), re.M) is not None
    if target.startswith("tests/ratchets/"):
        return (repo / target).is_file()
    return False


def debt_card_is_live(card: str, repo: Path) -> bool:
    return card.startswith(CORPUS_LIVE) and "/done/" not in card and (repo / card).is_file()


def read(doctrine: Path, register: Path, repo: Path, today: date) -> tuple[list[str], dict[str, int], date | None]:
    """Every fault, the counts per stance, and the earliest debt date."""
    faults: list[str] = []
    counts = {"held": 0, "traced": 0, "convention": 0, "undefended": 0}
    earliest: date | None = None

    rules = sections_of(doctrine.read_text(encoding="utf-8"))
    entries = entries_of(register.read_text(encoding="utf-8"))

    for title in rules:
        if title not in entries:
            faults.append(f"§{title!r} has no line in {register.name}")
    for title in entries:
        if title not in rules:
            faults.append(f"{register.name} names §{title!r}, which {doctrine.name} does not have")

    for title, lines in entries.items():
        if title not in rules:
            continue
        if len(lines) != 1:
            faults.append(f"§{title!r}: {len(lines)} stance lines; exactly one")
            continue
        line = lines[0]
        held = STANCES["Held by"].match(line)
        if held:
            counts["held"] += 1
            if not held_target_exists(held.group("target"), repo):
                faults.append(f"§{title!r}: held by {held.group('target')}, which does not exist")
            continue
        if STANCES["Traced by"].match(line):
            counts["traced"] += 1
            continue
        if STANCES["Convention because"].match(line):
            counts["convention"] += 1
            continue
        debt = DEBT.match(line)
        if debt:
            counts["undefended"] += 1
            if not debt_card_is_live(debt.group("card"), repo):
                faults.append(f"§{title!r}: undefended until {debt.group('card')}, which the corpus does not have live")
            if not debt.group("date"):
                faults.append(f"§{title!r}: a debt line needs a date")
            else:
                due = date.fromisoformat(debt.group("date"))
                if due < today:
                    faults.append(f"§{title!r}: undefended until {due}, which has passed")
                earliest = due if earliest is None or due < earliest else earliest
            continue
        if line.startswith("*Undefended until:*"):
            faults.append(f"§{title!r}: a debt line names a live plan or suggestion path, then a date")
            continue
        faults.append(f"§{title!r}: {line[:50]!r} is not one of the three stances or a debt line")

    return faults, counts, earliest


def the_map(counts: dict[str, int], earliest: date | None) -> str:
    due = f", due {earliest}" if earliest else ""
    return (
        f"held {counts['held']}, traced {counts['traced']}, convention {counts['convention']}; "
        f"undefended {counts['undefended']}{due}"
    )


def test_every_rule_says_what_holds_it(capsys):
    faults, counts, earliest = read(DOCTRINE, REGISTER, REPO, date.today())
    print(the_map(counts, earliest))
    assert not faults, "\n".join(faults)


# ── the refusals, rehearsed on fixtures ────────────────────────────────

DOCTRINE_FIXTURE = """# How we work

## Part I — The doctrine

## 1. First rule

words

## 2. Second rule

words
"""


def _fixture(tmp_path: Path, register: str) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    (repo / "docs" / "plans").mkdir(parents=True)
    (repo / "docs" / "slice-suggestions").mkdir(parents=True)
    (repo / "tests" / "ratchets").mkdir(parents=True)
    (repo / "tests" / "ratchets" / "test_real.py").write_text("def test_x(): pass\n")
    (repo / "docs" / "plans" / "2026-09-05-a-live-plan.md").write_text("# A live plan\n")
    (repo / "api").mkdir()
    (repo / "api" / "doors.py").write_text("class Doors:\n    def close(self):\n        pass\n")
    doctrine = repo / "docs" / "HOW-WE-WORK.md"
    doctrine.write_text(DOCTRINE_FIXTURE)
    reg = repo / "docs" / "HOW-WE-HOLD-IT.md"
    reg.write_text(register)
    return repo, doctrine, reg


TODAY = date(2026, 9, 5)
GOOD = """# How we hold it

## 1. First rule
*Held by:* tests/ratchets/test_real.py — it refuses.

## 2. Second rule
*Undefended until:* docs/plans/2026-09-05-a-live-plan.md by 2026-09-19 — a reader.
"""


def test_the_fixture_register_passes_and_prints_debt_apart(tmp_path):
    repo, doctrine, reg = _fixture(tmp_path, GOOD)
    faults, counts, earliest = read(doctrine, reg, repo, TODAY)
    assert faults == []
    assert the_map(counts, earliest) == "held 1, traced 0, convention 0; undefended 1, due 2026-09-19"


def test_a_door_in_api_counts_as_held(tmp_path):
    repo, doctrine, reg = _fixture(tmp_path, GOOD.replace("tests/ratchets/test_real.py", "api/doors.py::close"))
    faults, counts, _ = read(doctrine, reg, repo, TODAY)
    assert faults == [] and counts["held"] == 1


@pytest.mark.parametrize(
    ("register", "fault"),
    [
        (GOOD.replace("## 2. Second rule\n*Undefended until:* docs/plans/2026-09-05-a-live-plan.md by 2026-09-19 — a reader.\n", ""),
         "has no line"),
        (GOOD + "*Traced by:* something else too.\n", "2 stance lines"),
        (GOOD.replace("test_real.py", "test_imaginary.py"), "does not exist"),
        (GOOD.replace("docs/plans/2026-09-05-a-live-plan.md by 2026-09-19", "nothing by 2026-09-19"),
         "names a live plan or suggestion path"),
        (GOOD.replace("2026-09-05-a-live-plan.md", "2026-09-05-a-gone-plan.md"), "does not have live"),
        (GOOD.replace(" by 2026-09-19", ""), "needs a date"),
        (GOOD.replace("2026-09-19", "2026-09-01"), "has passed"),
        (GOOD + "\n## 3. A rule the doctrine lacks\n*Traced by:* nothing.\n", "does not have"),
        (GOOD.replace("*Held by:*", "*Guarded by:*"), "not one of the three stances"),
    ],
    ids=["missing", "doubled", "dangling-held", "cardless-debt", "card-not-live", "undated-debt",
         "overdue-debt", "orphan-entry", "fourth-word"],
)
def test_the_register_refuses(tmp_path, register, fault):
    repo, doctrine, reg = _fixture(tmp_path, register)
    faults, _, _ = read(doctrine, reg, repo, TODAY)
    assert any(fault in f for f in faults), faults


def test_debt_is_never_counted_as_held(tmp_path):
    repo, doctrine, reg = _fixture(tmp_path, GOOD)
    _, counts, _ = read(doctrine, reg, repo, TODAY)
    assert counts["held"] == 1 and counts["undefended"] == 1
    assert counts["held"] + counts["traced"] + counts["convention"] == 1
