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
import os
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from domain.project import Project
from infrastructure.store import Store
from tests import floor as floor_mod

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def machine_floor(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Iterator[floor_mod.Floor]:
    """Every test stands on the fixture floor (`tests/floor.py`): no path the
    runtime reads is on this machine and no command it runs is real, so no
    test can open a window, touch a subscription or reach a daemon (plan 02,
    criterion 6). A ratchet holds that this is so."""
    floor = floor_mod.lay(tmp_path_factory.mktemp("machine"))
    for variable, attribute in floor_mod.ENVIRONMENT.items():
        monkeypatch.setenv(variable, str(getattr(floor, attribute)))
    monkeypatch.setenv("PATH", f"{floor_mod.FAKE_BIN}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_ACCOUNT", raising=False)
    yield floor
    floor.kill_everything()


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
