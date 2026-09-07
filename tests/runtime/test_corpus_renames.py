"""Git's record of a corpus rename, read the way the board asks for it (plan
08, item 1): committed renames newest first, a staged one, and nothing for a
file that was deleted and written anew below git's similarity bar."""

from pathlib import Path

from runtime import git
from tests.runtime.test_git import repos, sh  # noqa: F401 — the fixture

BODY = "# {title}\n\n**Found by:** the owner.\n\n## Observation\n\n" + "The same words. " * 40


def test_committed_and_staged_renames_are_read_and_a_rewrite_is_not(repos: tuple[Path, Path]):
    _, checkout = repos
    folder = checkout / "docs" / "slice-suggestions"
    folder.mkdir(parents=True)
    (folder / "the-closed-card.md").write_text(BODY.format(title="The closed card"))
    (folder / "other.md").write_text(BODY.format(title="Other"))
    sh(checkout, "add", "docs")
    sh(checkout, "commit", "-q", "-m", "two suggestions")
    assert git.corpus_renames(checkout) == {}
    # A rename that changes stem and title, committed: git sees it as a rename.
    sh(
        checkout,
        "mv",
        "docs/slice-suggestions/the-closed-card.md",
        "docs/slice-suggestions/the-collapsed-card.md",
    )
    (folder / "the-collapsed-card.md").write_text(BODY.format(title="The collapsed card"))
    sh(checkout, "add", "docs")
    sh(checkout, "commit", "-q", "-m", "renamed")
    assert git.corpus_renames(checkout) == {
        "docs/slice-suggestions/the-closed-card.md": "docs/slice-suggestions/the-collapsed-card.md"
    }
    # Renamed again: the newest rename wins for the middle name, and the chain is whole.
    sh(
        checkout,
        "mv",
        "docs/slice-suggestions/the-collapsed-card.md",
        "docs/slice-suggestions/the-folded-card.md",
    )
    sh(checkout, "commit", "-q", "-m", "renamed again")
    moves = git.corpus_renames(checkout)
    assert moves["docs/slice-suggestions/the-collapsed-card.md"] == (
        "docs/slice-suggestions/the-folded-card.md"
    )
    assert moves["docs/slice-suggestions/the-closed-card.md"] == (
        "docs/slice-suggestions/the-collapsed-card.md"
    )
    # A rename staged and not yet committed is read too.
    sh(checkout, "mv", "docs/slice-suggestions/other.md", "docs/slice-suggestions/another.md")
    assert git.corpus_renames(checkout)["docs/slice-suggestions/other.md"] == (
        "docs/slice-suggestions/another.md"
    )
    sh(checkout, "commit", "-q", "-m", "staged rename")
    # A file deleted and another written with a different body is no rename to git.
    (folder / "the-folded-card.md").unlink()
    (folder / "new.md").write_text("# New\n\nNothing alike.\n")
    sh(checkout, "add", "-A", "docs")
    sh(checkout, "commit", "-q", "-m", "not a rename")
    assert "docs/slice-suggestions/the-folded-card.md" not in git.corpus_renames(checkout)
    # Outside the corpus, git is not asked.
    assert git.corpus_renames(checkout / "nowhere") == {}
