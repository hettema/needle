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


def test_a_verdict_row_is_read_before_it_is_written(corpus: Path, database: Path, capsys):
    main(["add", str(corpus)])
    capsys.readouterr()
    assert main(["row", "harbourmaster", "253", "VERDICT", "probably done → Done"]) == 1
    err = capsys.readouterr().err
    assert "not written: the VERDICT row names no class the board knows" in err
    assert (
        main(["row", "harbourmaster", "253", "VERDICT", "live and open — waits on #241 → stays"])
        == 0
    )
    assert "#253: VERDICT written" in capsys.readouterr().out
    store = Store(database)
    card = store.card("harbourmaster", 253)
    assert card is not None and [r.text for r in card.rows if r.kind.value == "VERDICT"] == [
        "live and open — waits on #241 → stays"
    ]
    store.close()


def test_verdicts_proposes_what_the_boards_facts_settle_and_writes_them_on_request(
    corpus: Path, database: Path, capsys
):
    main(["add", str(corpus)])
    capsys.readouterr()
    assert main(["verdicts", "harbourmaster"]) == 0
    out = capsys.readouterr().out
    # 0.1's file put #259 and #223 in Executing with no lane: doubted on the first read.
    # #259's plan is archived, so the read itself moved it (plan 06, item 1); #223's
    # suggestion is live, so it stays and the verdict says why.
    assert "#223  Executing        doubted — no lane exists for it" in out
    assert "#259  Decision moment" in out
    assert "→ Decision moment" in out
    assert "(the corpus decides)" in out
    assert "proposed (doubted: " in out
    store = Store(database)
    assert not any(r.kind.value == "VERDICT" for c in store.cards("harbourmaster") for r in c.rows)
    store.close()
    assert main(["verdicts", "harbourmaster", "--write"]) == 0
    out = capsys.readouterr().out
    assert "written (doubted: " in out
    store = Store(database)
    written = {
        c.number
        for c in store.cards("harbourmaster")
        if any(r.kind.value == "VERDICT" for r in c.rows)
    }
    assert 223 in written
    store.close()
    # A card carrying a verdict is not proposed again.
    assert main(["verdicts", "harbourmaster"]) == 0
    assert "#223 " not in capsys.readouterr().out
