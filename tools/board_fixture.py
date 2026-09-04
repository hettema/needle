"""Writes `frontend/tests/fixture.json`: the Harbourmaster board exactly as the
API serves it, with every card's detail, at a fixed clock.

The frontend tests need a board in the page's own types. Writing one by hand
drifts from what the backend actually serves and, before this tool, it carried
a real project's card titles into a public repository. So the fixture is
generated: the synthetic project under `tests/fixtures/harbourmaster/` goes
through the real registration, import and sweep, and the result is dumped from
the Pydantic models. A ratchet regenerates and compares, so the snapshot can
never lag the domain.

One arrival is staged: the storm-warning plan is held back from the
founding sweep and swept in afterwards, so the snapshot carries one card born
while the board was watching — the NEW mark and the "arrived today" count the
page has to render.

    uv run python tools/board_fixture.py
"""

import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from board.import_01 import read_01  # noqa: E402
from domain.card import CardOrigin  # noqa: E402
from domain.project import Project  # noqa: E402
from infrastructure.corpus import scan  # noqa: E402
from infrastructure.live import Live, sweep  # noqa: E402
from infrastructure.store import Store  # noqa: E402

HARBOURMASTER = REPO / "tests" / "fixtures" / "harbourmaster"
FIXTURE = REPO / "frontend" / "tests" / "fixture.json"
ARRIVAL = "docs/plans/2026-09-04-a-storm-warning-reaches-every-skipper.md"
NOW = datetime(2026, 9, 4, 8, 30, tzinfo=UTC)
SHOWN_PATH = "/srv/harbourmaster"
"""The path the snapshot shows for the project: the real one is a temporary
directory and would differ on every run."""


def snapshot() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "harbourmaster"
        shutil.copytree(HARBOURMASTER, root)
        arrival = root / ARRIVAL
        held_back = arrival.read_text(encoding="utf-8")
        arrival.unlink()

        store = Store(Path(tmp) / "needle.db")
        project = Project(
            slug="harbourmaster", name="Harbourmaster", path=str(root), registered_at=NOW
        )
        store.add_project(project)
        card_file = json.loads((root / "docs/board/needle-board.json").read_text(encoding="utf-8"))
        store.import_01(project.slug, read_01(card_file, scan(root, NOW)), NOW)
        sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)

        arrival.write_text(held_back, encoding="utf-8")
        live = Live(store, now=lambda: NOW)
        live.load()
        # The snapshot is the board as served: the watcher is on. Without a
        # running loop there is no watcher task, so its two facts are set here.
        live.projects[project.slug].watching = True
        live.projects[project.slug].watch_note = None

        board = live.board(project.slug)
        board.project = board.project.model_copy(update={"path": SHOWN_PATH})
        numbers = [c.number for col in board.columns for g in col.groups for c in g.cards]
        details = {str(n): live.detail(project.slug, n).model_dump(mode="json") for n in numbers}
        store.close()
        return {"board": board.model_dump(mode="json"), "details": details}


def render() -> str:
    return json.dumps(snapshot(), indent=2, ensure_ascii=False) + "\n"


def write() -> bool:
    """True when the file changed."""
    content = render()
    if FIXTURE.is_file() and FIXTURE.read_text(encoding="utf-8") == content:
        return False
    FIXTURE.write_text(content, encoding="utf-8")
    return True


if __name__ == "__main__":
    print(f"wrote {FIXTURE}" if write() else f"{FIXTURE} is current")
