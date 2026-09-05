"""The board's reading of whether a machine delivers the doctrine.

Three shapes and no fourth: the injected files resolve to this project's
HOW-WE-WORK (`one-text`), one resolves somewhere else (`two-texts`), or one is
not there (`none`). Every case runs against a fixture HOME, so the test says the
same thing on a laptop that has never had Claude Code installed.
"""

from datetime import UTC, datetime
from pathlib import Path

from domain.entrance import EntranceWord
from infrastructure.entrance import project_of, read_entrance

AT = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def _home(tmp_path: Path) -> tuple[Path, Path]:
    """A fixture HOME and the one text a `needle` installed beside it would ship."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".codex").mkdir(parents=True)
    doctrine = tmp_path / "needle" / "docs" / "HOW-WE-WORK.md"
    doctrine.parent.mkdir(parents=True)
    doctrine.write_text("# How we work\n")
    return home, doctrine


def test_one_text_when_both_injected_files_resolve_to_the_doctrine(tmp_path):
    home, doctrine = _home(tmp_path)
    (home / ".claude" / "CLAUDE.md").symlink_to(doctrine)
    (home / ".codex" / "AGENTS.md").symlink_to(home / ".claude" / "CLAUDE.md")

    entrance = read_entrance(home, AT, doctrine=doctrine, has_codex=True)

    assert entrance.word is EntranceWord.ONE_TEXT
    assert entrance.line.startswith("entrance: one-text")
    assert [f.is_the_one_text for f in entrance.files] == [True, True]


def test_two_texts_names_what_the_injected_file_resolves_to_instead(tmp_path):
    home, doctrine = _home(tmp_path)
    second = tmp_path / "machine" / "CLAUDE.md"
    second.parent.mkdir(parents=True)
    second.write_text("a second doctrine\n")
    (home / ".claude" / "CLAUDE.md").symlink_to(second)
    (home / ".codex" / "AGENTS.md").symlink_to(second)

    entrance = read_entrance(home, AT, doctrine=doctrine, has_codex=True)

    assert entrance.word is EntranceWord.TWO_TEXTS
    assert entrance.line.startswith(f"entrance: two-texts {second}")
    assert entrance.files[0].resolves_to == str(second)


def test_none_when_an_injected_file_is_missing(tmp_path):
    home, doctrine = _home(tmp_path)

    entrance = read_entrance(home, AT, doctrine=doctrine, has_codex=False)

    assert entrance.word is EntranceWord.NONE
    assert entrance.line.startswith("entrance: none")
    assert "~/.claude/CLAUDE.md" in entrance.line
    assert entrance.files[0].resolves_to is None


def test_a_dangling_link_reads_as_none_not_as_a_second_text(tmp_path):
    """A link whose target was deleted delivers nothing, which is `none`; reading
    it as `two-texts` would name a path no session can open."""
    home, doctrine = _home(tmp_path)
    (home / ".claude" / "CLAUDE.md").symlink_to(tmp_path / "gone.md")

    entrance = read_entrance(home, AT, doctrine=doctrine, has_codex=False)

    assert entrance.word is EntranceWord.NONE


def test_codex_is_only_asked_about_when_it_is_installed(tmp_path):
    """A machine without Codex is not `none` because `~/.codex/AGENTS.md` is
    absent — no session of that make will ever start there."""
    home, doctrine = _home(tmp_path)
    (home / ".claude" / "CLAUDE.md").symlink_to(doctrine)

    assert read_entrance(home, AT, doctrine=doctrine, has_codex=False).word is EntranceWord.ONE_TEXT
    assert read_entrance(home, AT, doctrine=doctrine, has_codex=True).word is EntranceWord.NONE


def test_a_missing_file_outranks_a_second_text(tmp_path):
    """`none` is the worse finding and is the one said: a session of that make
    enters with nothing at all, which the person fixes before the other."""
    home, doctrine = _home(tmp_path)
    second = tmp_path / "machine" / "CLAUDE.md"
    second.parent.mkdir(parents=True)
    second.write_text("a second doctrine\n")
    (home / ".claude" / "CLAUDE.md").symlink_to(second)

    entrance = read_entrance(home, AT, doctrine=doctrine, has_codex=True)

    assert entrance.word is EntranceWord.NONE
    assert "~/.codex/AGENTS.md" in entrance.line


def test_a_lane_reads_the_project_it_is_a_copy_of(tmp_path):
    """`needle` run from a lane's worktree must not call the main checkout's
    HOW-WE-WORK a second text: a lane is the same project at another revision,
    and reading it literally would say `two-texts` from every lane forever."""
    project = tmp_path / "needle"
    lane = project / ".claude" / "worktrees" / "card-54-a-lane"
    lane.mkdir(parents=True)

    assert project_of(lane / "infrastructure") == project
    assert project_of(project) == project
