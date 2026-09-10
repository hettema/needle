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

TEMP_ROOT_VARIABLE = "PYTEST_DEBUG_TEMPROOT"


def floors_root() -> Path:
    """Where this suite's floors go when nothing on the command line or in the
    environment says otherwise: a directory on disk under the user's cache.

    Why not pytest's default: the system temp folder is memory on this
    laptop (`/tmp` is a tmpfs of 7.7 GB), so every floor laid there was RAM
    the board's 5 GB floor could not see and the memory killer answered —
    2.9 GB of floors at the moment card #83's whole group was killed,
    2026-09-09 (card #109). Why the cache and not a per-run `--basetemp`:
    pytest wipes a given base and uses it bare, so two suites given one
    collide; a root keeps pytest's own numbering, lock and pruning."""
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache) / "needle" / "floors"


def pytest_configure(config: pytest.Config) -> None:
    """Move the temp root onto disk by pytest's own knob, and only when neither
    `--basetemp` nor the variable already names one — an explicit choice
    wins, as it always did, and the laptop-wide setting the machine's board
    carries (card #109, item 3) is that same variable."""
    # An empty variable is absent to pytest too (`from_env or gettempdir()`),
    # so it is absent here, or an empty setting would re-open the memory default.
    if config.option.basetemp is None and not os.environ.get(TEMP_ROOT_VARIABLE):
        root = floors_root()
        root.mkdir(parents=True, exist_ok=True)
        os.environ[TEMP_ROOT_VARIABLE] = str(root)


def floor_runs_ledger() -> Path:
    """Where every run of this suite writes one line — when, the root its
    floors were laid under, and the kernel's word for that root's filesystem
    — so the plan's loop reads a trace the suite leaves instead of scanning
    the temp folder, which three review reads showed can hide a floor
    (another user's shared directory, an unreadable one, a bind). Beside
    the floors' root, never under it: pytest prunes under the root."""
    return floors_root().parent / "floor-runs.log"


@pytest.fixture(autouse=True, scope="session")
def floors_recorded(tmp_path_factory: pytest.TempPathFactory) -> None:
    root = tmp_path_factory.getbasetemp()
    ledger = floor_runs_ledger()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with ledger.open("a", encoding="utf-8") as out:
        out.write(f"{stamp} {floor_mod.filesystem_of(root)} {root}\n")


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
