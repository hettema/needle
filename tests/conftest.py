"""Shared fixtures: the Harbourmaster project — a synthetic corpus in the shape
the board reads, with a Needle 0.1 card file over it — copied to a temporary
path so a test may write into it, and a store on a temporary path.

Harbourmaster is a berth booking and billing product for small marinas. It is
invented: the repository is public, and the fixtures, the frontend snapshot and
the signed comps all draw on this one project instead of on a real one
(plan 01b, item 4). A ratchet under tests/ratchets/ holds that no real
project's card titles are in the tree.
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from domain.project import Project
from infrastructure.store import Store

FIXTURES = Path(__file__).parent / "fixtures"
HARBOURMASTER = FIXTURES / "harbourmaster"
CARD_FILE_01 = HARBOURMASTER / "docs" / "board" / "needle-board.json"

PLAN = """# {title}

**Status:** {status}
**Effort gate:** {gate} — {why}
**Sequencing:** independent of every open card.
{extra}
## Intent

{intent}

## Terrain

Some terrain.
"""

SUGGESTION = """# {title}

**Found by:** the review of card #249
(`docs/reviews/2026-09-03-x.md`, finding 1), carried out.

## Observation

{intent}
"""


def write_plan(
    root: Path,
    stem: str,
    *,
    title: str,
    status: str = "PENDING",
    gate: str = "high",
    why: str = "because",
    intent: str = "The first sentence. The second sentence.",
    extra: str = "",
    archived: bool = False,
) -> Path:
    folder = root / "docs" / "plans" / ("done" if archived else "")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}.md"
    path.write_text(
        PLAN.format(title=title, status=status, gate=gate, why=why, intent=intent, extra=extra),
        encoding="utf-8",
    )
    return path


def write_suggestion(
    root: Path,
    stem: str,
    *,
    title: str,
    intent: str = "Something was seen.",
    archived: bool = False,
) -> Path:
    folder = root / "docs" / "slice-suggestions" / ("done" if archived else "")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}.md"
    path.write_text(SUGGESTION.format(title=title, intent=intent), encoding="utf-8")
    return path


def copy_harbourmaster(into: Path) -> Path:
    """The synthetic project, on a path a test may write into."""
    root = into / "harbourmaster"
    shutil.copytree(HARBOURMASTER, root)
    return root


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    return copy_harbourmaster(tmp_path)


@pytest.fixture
def card_file_01() -> dict[str, object]:
    return json.loads(CARD_FILE_01.read_text(encoding="utf-8"))


@pytest.fixture
def store(tmp_path: Path):
    store = Store(tmp_path / "needle.db")
    yield store
    store.close()


NOW = datetime(2026, 9, 3, 21, 40, tzinfo=UTC)


@pytest.fixture
def project(corpus: Path) -> Project:
    return Project(slug="proj", name="Harbourmaster", path=str(corpus), registered_at=NOW)
