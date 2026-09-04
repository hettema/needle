"""The command line's verbs, run in-process against a store on a temporary path."""

from pathlib import Path

import pytest

from api.cli import main
from infrastructure.store import Store
from tests.conftest import write_plan


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "needle.db"
    monkeypatch.setenv("NEEDLE_DB", str(path))
    return path


def test_add_registers_imports_and_reads(corpus: Path, database: Path, capsys):
    assert main(["add", str(corpus), "--name", "Harbourmaster"]) == 0
    out = capsys.readouterr().out
    assert "Registered Harbourmaster as harbourmaster" in out
    assert "Imported Needle 0.1's card file: 21 cards" in out
    assert "Cards: born 6." in out
    store = Store(database)
    assert [p.slug for p in store.projects()] == ["harbourmaster"]
    assert len(store.cards("harbourmaster")) == 27
    store.close()


def test_add_on_a_registered_path_re_reads_the_corpus_and_says_what_changed(
    corpus: Path, database: Path, capsys
):
    assert main(["add", str(corpus)]) == 0
    capsys.readouterr()
    assert main(["add", str(corpus), "--name", "Renamed"]) == 0
    out = capsys.readouterr().out
    assert "is already on the board as harbourmaster (harbourmaster)" in out
    assert "--name and --slug do not change a project already on the board." in out
    assert "not read again" in out
    assert "Cards: nothing changed." in out

    write_plan(corpus, "2026-09-05-a-plan-written-offline", title="A plan written offline")
    assert main(["add", str(corpus)]) == 0
    out = capsys.readouterr().out
    assert "Cards: born 1." in out
    store = Store(database)
    born = next(c for c in store.cards("harbourmaster") if c.title == "A plan written offline")
    assert born.origin.value == "arrived"
    store.close()


def test_add_refuses_a_path_that_is_not_a_corpus(tmp_path: Path, database: Path, capsys):
    assert main(["add", str(tmp_path)]) == 1
    assert "not a corpus" in capsys.readouterr().err


def test_projects_lists_what_is_on_the_board(corpus: Path, database: Path, capsys):
    main(["add", str(corpus)])
    capsys.readouterr()
    assert main(["projects"]) == 0
    assert capsys.readouterr().out.startswith("harbourmaster\tharbourmaster\t")
