"""The command line's verbs, run in-process against a store on a temporary path."""

import json
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
    assert "Cards: born 7." in out
    store = Store(database)
    assert [p.slug for p in store.projects()] == ["harbourmaster"]
    assert len(store.cards("harbourmaster")) == 28
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


def test_kinds_prints_every_live_suggestions_kind_and_why(corpus: Path, database: Path, capsys):
    """Plan 06, item 2: the table of guesses is printed, never tracked — a
    project's titles stay in its own repository."""
    main(["add", str(corpus)])
    capsys.readouterr()
    assert main(["kinds", "harbourmaster"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == (
        "9 live suggestions; 1 with a Kind line; 8 read from their text, 1 of them as "
        "defects; 1 with a Fix: mark, 8 unmarked"
    )
    assert "defect  docs/slice-suggestions/" in out and "(its title or Found-by;" in out
    assert "idea    docs/slice-suggestions/" in out and "(no sign of a defect;" in out
    # The mark (plan 11, item 2) is read from the head only: a `Fix:` line of
    # prose under a section says what was fixed and is not a mark.
    assert "(Kind: defect; Fix: now)" in out
    assert "two-meters-on-one-pontoon-disagree.md" in out
    two_meters = next(line for line in out.splitlines() if "two-meters" in line)
    assert two_meters.endswith("(no sign of a defect; Fix: unmarked (no Fix: line))")
    assert main(["kinds", "nowhere"]) == 1


@pytest.fixture
def main_checkout(monkeypatch: pytest.MonkeyPatch) -> Path:
    """The installer runs from Needle's main checkout and refuses a lane
    (card #73); the suite runs in lanes, so the tests stand it where the
    main checkout is."""
    root = Path("/srv/needle")
    monkeypatch.setattr("api.board_cli.REPO_ROOT", root)
    return root


def test_hook_install_refuses_to_run_from_a_lane(tmp_path: Path, capsys, monkeypatch):
    """Card #73: the command the installer registers names its own checkout's
    script by absolute path; from a lane that path dies with the lane, and
    on 2026-09-07 one lane wrote it into three projects before reading the
    line. The installer refuses, and writes nothing."""
    monkeypatch.setattr(
        "api.board_cli.REPO_ROOT", Path("/srv/needle/.claude/worktrees/card-1-a-lane")
    )
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    assert main(["hook", "install", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "never a lane" in err and "dies with the lane" in err
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".agents").exists()


def test_hook_install_registers_every_event_once_and_names_the_word_hooks_ceiling(
    tmp_path: Path, capsys, main_checkout: Path
):
    """Plan 10, item 2, and card #60: `needle hook install` adds PostToolUse and
    UserPromptSubmit to a project that has the four session events, keeps
    what is there — a project's own hook on the same event stays beside ours,
    which is how Hello Revenue's backbrief hook and Needle's re-anchor would
    both fire on the word until that project's card retires one — and is
    idempotent."""
    import json

    from api.board_cli import HOOK_EVENTS, READ_EVENTS, hook_command

    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir()
    ours = {"type": "command", "command": hook_command()}
    theirs = {"type": "command", "command": "echo theirs"}
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [{"matcher": "", "hooks": [ours]}],
                    "UserPromptSubmit": [{"matcher": "", "hooks": [theirs]}],
                }
            }
        )
    )
    assert main(["hook", "install", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.strip().endswith(
        "for SessionStart, SessionEnd, StopFailure, PostToolUse, UserPromptSubmit"
    )
    blob = json.loads(settings.read_text())
    for event in HOOK_EVENTS:
        hooks = [h for entry in blob["hooks"][event] for h in entry["hooks"]]
        assert [h["command"] for h in hooks].count(hook_command()) == 1, event
    for event in READ_EVENTS:
        read = [
            h
            for entry in blob["hooks"][event]
            for h in entry["hooks"]
            if h["command"] == hook_command()
        ]
        assert read[0]["timeout"] == 5, f"the {event} entry names its own ceiling"
    assert "timeout" not in blob["hooks"]["Stop"][0]["hooks"][0]
    prompt_hooks = [h for entry in blob["hooks"]["UserPromptSubmit"] for h in entry["hooks"]]
    assert prompt_hooks[0] == theirs, "a project's own hook on the event is kept, first"
    assert prompt_hooks[1]["command"] == hook_command()

    assert main(["hook", "install", str(tmp_path)]) == 0
    assert "already registered" in capsys.readouterr().out
    assert json.loads(settings.read_text()) == blob, "idempotent"


def test_hook_install_lays_the_codex_skills_link_once_and_leaves_a_projects_own_alone(
    tmp_path: Path, capsys, main_checkout: Path
):
    """Card #73, item 1: `needle hook install` lays `.agents/skills` as a
    relative link at `../.claude/skills` when that folder exists, so a Codex
    session sees the project's skills; says so and asks for the commit; a
    second run changes nothing; a project without a skills folder gets
    nothing and hears nothing about it; a real directory or a link pointing
    elsewhere is the project's own, named and never replaced."""
    import os

    repo = tmp_path / "with-skills"
    (repo / ".claude" / "skills" / "hr-plan-write").mkdir(parents=True)
    assert main(["hook", "install", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "laid .agents/skills -> ../.claude/skills in with-skills" in out and "commit it" in out
    link = repo / ".agents" / "skills"
    assert link.is_symlink() and os.readlink(link) == "../.claude/skills", (
        "relative, so a clone keeps it"
    )
    assert (link / "hr-plan-write").is_dir()

    assert main(["hook", "install", str(repo)]) == 0
    assert "already sees with-skills's skills" in capsys.readouterr().out
    assert os.readlink(link) == "../.claude/skills", "a second run is a no-op"

    bare = tmp_path / "bare"
    bare.mkdir()
    assert main(["hook", "install", str(bare)]) == 0
    out = capsys.readouterr().out
    assert "skills" not in out and not (bare / ".agents").exists(), "nothing laid, nothing said"

    own = tmp_path / "own"
    (own / ".claude" / "skills").mkdir(parents=True)
    (own / ".agents" / "skills" / "theirs").mkdir(parents=True)
    assert main(["hook", "install", str(own)]) == 0
    assert "keeps its own .agents/skills" in capsys.readouterr().out
    assert (own / ".agents" / "skills" / "theirs").is_dir()
    assert not (own / ".agents" / "skills").is_symlink()

    elsewhere = tmp_path / "elsewhere"
    (elsewhere / ".claude" / "skills").mkdir(parents=True)
    (elsewhere / ".agents").mkdir()
    (elsewhere / ".agents" / "skills").symlink_to("/nowhere/skills")
    assert main(["hook", "install", str(elsewhere)]) == 0
    said = capsys.readouterr().out
    assert "links to /nowhere/skills, not ../.claude/skills; left as it is" in said
    assert os.readlink(elsewhere / ".agents" / "skills") == "/nowhere/skills"


def test_rows_prints_the_record_as_json_with_time_and_writer(corpus: Path, database: Path, capsys):
    """Plan 08, item 3: the verb a project's tooling calls for what sessions
    wrote on its cards — Hello Revenue's morning note reads DELIVERED."""
    main(["add", str(corpus)])
    assert main(["row", "harbourmaster", "253", "DELIVERED", "the meter bills"]) == 0
    capsys.readouterr()
    assert main(["rows", "harbourmaster", "--kind", "delivered"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[-1]["card"] == 253 and rows[-1]["text"] == "the meter bills"
    assert rows[-1]["by"] == "session" and rows[-1]["at"] > "2026-09-03"
    assert all(r["kind"] == "DELIVERED" for r in rows) and len(rows) > 1
    assert main(["rows", "harbourmaster", "--since", "2100-01-01"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["rows", "harbourmaster", "--since", "yesterday"]) == 1
    assert "ISO" in capsys.readouterr().err
    assert main(["rows", "nope"]) == 1
