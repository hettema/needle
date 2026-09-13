"""What a board says cannot be undone, matched against what a release would
carry, and the one sentence that says so (card #139)."""

from board.release import carried, sentence, under

MIGRATIONS = ["alembic/versions"]


def test_a_declared_folder_matches_what_sits_under_it_and_nothing_beside_it():
    files = [
        "alembic/versions/210_rewrite.py",
        "alembic/versions_old/9_old.py",
        "alembic/env.py",
        "api/main.py",
    ]
    assert carried(files, MIGRATIONS) == ["alembic/versions"]
    assert under(files, ["alembic/versions"]) == ["alembic/versions/210_rewrite.py"]
    # A sibling whose name merely starts the same way is not under it.
    assert carried(["alembic/versions_old/9_old.py"], MIGRATIONS) == []
    assert carried(["api/main.py"], MIGRATIONS) == []


def test_a_declared_file_matches_itself():
    assert carried(["infra/terraform.tfstate"], ["infra/terraform.tfstate"]) == [
        "infra/terraform.tfstate"
    ]


def test_a_board_that_declares_nothing_carries_nothing():
    assert carried(["alembic/versions/210_rewrite.py"], []) == []


def test_the_paths_come_back_in_the_owners_own_order_and_spelling():
    declared = ["alembic/versions/", "/infra/state"]
    files = ["infra/state/a.tf", "alembic/versions/b.py"]
    assert carried(files, declared) == ["alembic/versions/", "/infra/state"]


def test_the_sentence_says_the_work_the_waiting_and_whose_move():
    said = sentence(
        "hellorevenue",
        files=["alembic/versions/210_rewrite.py"],
        hold="docs/board/MAIN-HOLD.md",
        hold_stands=True,
    )
    assert said.startswith("the work is on the shared branch")
    assert "alembic/versions/210_rewrite.py" in said
    assert "cannot be undone" in said
    assert "promoting it is yours" in said
    assert "docs/board/MAIN-HOLD.md" in said


def test_the_sentence_says_when_nothing_holds_the_work_behind_it():
    missing = sentence("hellorevenue", files=["a/b.py"], hold="HOLD.md", hold_stands=False)
    assert "HOLD.md is not there" in missing and "will stall" in missing
    none = sentence("hellorevenue", files=["a/b.py"], hold=None, hold_stands=False)
    assert "names nothing that holds the work finishing behind it" in none


def test_an_unreadable_range_says_so_rather_than_naming_files():
    said = sentence(
        "hellorevenue", files=[], hold=None, hold_stands=False, unreadable="git could not read"
    )
    assert "could not be read" in said and "promoting it is yours" in said


def test_a_long_list_names_the_first_few_and_counts_the_rest():
    said = sentence(
        "p",
        files=[f"alembic/versions/{n}.py" for n in range(6)],
        hold=None,
        hold_stands=False,
    )
    assert "alembic/versions/0.py" in said and "and 3 more" in said


# ── what a plan names (card #139, item 4) ──────────────────────────────

PLAN = """# A plan

**Terrain:** `alembic/versions/0026_the_next_one.py` and the code beside it.

It adds a migration under `alembic/versions`, and touches `api/main.py`.
"""


def test_a_plan_names_a_declared_folder_and_a_file_that_does_not_exist_yet():
    """The two shapes a plan that changes stored data actually has, and the
    two the board's ground reader cannot see (the independent read of
    2026-09-13, finding 1): the folder has no extension, and the file it
    adds does not exist until the lane writes it."""
    from board.release import names

    assert names(PLAN, ["alembic/versions"]) == ["alembic/versions"]
    assert names("it adds `alembic/versions/0026_x.py`", ["alembic/versions"]) == [
        "alembic/versions"
    ]
    assert names("`alembic/versions`", ["alembic/versions"]) == ["alembic/versions"]


def test_a_plan_beside_the_declared_path_does_not_name_it():
    from board.release import names

    assert names("it touches `alembic/versions_old/9.py`", ["alembic/versions"]) == []
    assert names("it touches `old/alembic/versions/9.py`", ["alembic/versions"]) == []
    assert names("it touches `api/main.py`", ["alembic/versions"]) == []
    assert names(PLAN, ["office/pricing.py"]) == []


def test_a_declared_file_is_named_exactly():
    from board.release import names

    assert names("`office/pricing.py` changes", ["office/pricing.py"]) == ["office/pricing.py"]
    assert names("`office/pricing.py.bak`", ["office/pricing.py"]) == []


def test_the_sentence_says_when_nothing_says_which_work_left_it():
    """A release that waits with no card claiming it is the board's own fact
    and no card's (the independent read of 2026-09-13, finding 2)."""
    said = sentence(
        "hellorevenue",
        files=["alembic/versions/210.py"],
        hold="HOLD.md",
        hold_stands=True,
        unclaimed=True,
    )
    assert "nothing on this board says which work left it for you" in said
    assert "promoting it is yours" not in said
