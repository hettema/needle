"""Work that starts without the owner never goes live without him (card
#139), on the floor.

Turning a board's auto-fix on declares what cannot be taken back there
(item 2); a session the board started is refused the promotion of the
stable branch when the release would carry one of those paths, whoever put
it there, and writes the project's standing hold in the same push (item 3);
the beat does not start a second card of the same shape while one waits
(item 4); the card says the work is finished and the release is his, and a
session that died before its hold leaves the card saying so rather than
reading as done (item 5).

The test project has no code of its own, so the files its plans name are
written here: `office/pricing.py` stands in for Hello Revenue's migrations
folder — the thing whose change cannot be taken back — and `office/tides.py`
for an ordinary file beside it.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from domain.dial import FixStage
from domain.lane import LaneRecord
from tests.api import test_doors as doors
from tests.api.test_dial import board, number_of, tick, turn
from tests.api.test_doors import git, reconcile
from tests.conftest import NOW

client = doors.client
repo = doors.repo
quick = doors.quick

CANNOT_UNDO = "office/pricing.py"
BESIDE_IT = "office/tides.py"
HOLD = "docs/board/MAIN-HOLD.md"
SLUG = "proj"
PRICING = "The pricing rule, judged against a real season"
TIDES = "The tide table is the harbour's own"


@pytest.fixture
def code(repo: Path) -> Path:
    """The files the test project's plans name, so a plan has real ground."""
    office = repo / "office"
    office.mkdir(exist_ok=True)
    (office / "pricing.py").write_text("RATE = 1\n")
    (office / "tides.py").write_text("TIDE = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "the office's own code")
    git(repo, "push", "-q", "origin", "develop", "develop:main")
    git(repo, "fetch", "-q", "origin")
    return repo


def declare(client: TestClient, *paths: str, hold: str | None = HOLD) -> dict:
    response = client.post(
        "/api/dial",
        json={"project": SLUG, "on": True, "cannot_undo": list(paths), "hold": hold},
    )
    assert response.status_code == 200, response.text
    return response.json()


def lane_for(client: TestClient, repo: Path, number: int, slug_words: str) -> Path:
    """A worktree on a card's branch, recorded as a lane the board started
    itself — a fix lane, which is what the rule turns on."""
    name = f"card-{number}-{slug_words}"
    path = repo / ".claude" / "worktrees" / name
    git(repo, "worktree", "add", "-q", "-b", name, str(path))
    store = client.app.state.live.store
    store.record_lane(
        LaneRecord(
            project=SLUG,
            card_number=number,
            name=name,
            path=str(path),
            branch=name,
            birth=git(path, "rev-parse", "HEAD"),
            tip=None,
            first_seen=NOW,
            last_seen=NOW,
            gone_at=None,
            folded_at=None,
            trunk_synced_at=None,
            main_synced_at=None,
        )
    )
    fix = store.open_fix_lane(SLUG, number, NOW)
    store.stage_fix_lane(fix.id, FixStage.STARTED, NOW)
    return path


def touch(path: Path, name: str, text: str) -> None:
    file = path / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", f"change {name}")


def fold(path: Path, *, main_too: bool = True) -> int:
    return main(["fold", "--worktree", str(path), *(["--main"] if main_too else [])])


def a_card(client: TestClient) -> int:
    return number_of(client, PRICING)


# ── item 2: each board says what cannot be undone there ────────────────


def test_a_board_turned_on_naming_nothing_reads_as_declaring_nothing(client: TestClient):
    head = turn(client, on=True)
    assert head["dial"]["undoable"]["paths"] == []
    assert head["dial"]["undoable"]["hold"] is None
    assert head["release"] is None


def test_a_board_never_turned_since_the_question_existed_reads_as_undeclared(client: TestClient):
    store = client.app.state.live.store
    assert store.dial(SLUG).undoable is None and store.dial(SLUG).on is False


def test_the_declaration_rides_with_the_turn_and_is_audited(client: TestClient):
    head = declare(client, CANNOT_UNDO)
    assert head["dial"]["undoable"]["paths"] == [CANNOT_UNDO]
    assert head["dial"]["undoable"]["hold"] == HOLD
    store = client.app.state.live.store
    assert [c.declared for c in store.dial_changes() if c.declared] == [
        f"{CANNOT_UNDO}; hold {HOLD}"
    ]


def test_turning_it_on_again_saying_nothing_keeps_what_it_declared(client: TestClient):
    declare(client, CANNOT_UNDO)
    turn(client, on=False)
    head = turn(client, on=True)
    assert head["dial"]["undoable"]["paths"] == [CANNOT_UNDO]
    assert head["dial"]["undoable"]["hold"] == HOLD


def test_the_declaration_is_cleared_only_by_saying_nothing_in_so_many_words(client: TestClient):
    declare(client, CANNOT_UNDO)
    head = declare(client, hold=None)  # `--cannot-undo nothing` reaches here as []
    assert head["dial"]["undoable"]["paths"] == []


def test_what_cannot_be_undone_cannot_be_declared_without_the_switch(client: TestClient):
    response = client.post(
        "/api/dial", json={"project": SLUG, "cannot_undo": [CANNOT_UNDO], "hold": HOLD}
    )
    assert response.status_code == 409
    assert "at the turn that bounds it" in response.json()["detail"]


# ── item 3: the release refuses itself ─────────────────────────────────


def test_a_session_the_board_started_folds_and_is_refused_the_promotion(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    stable = git(code, "rev-parse", "origin/main")
    number = a_card(client)
    path = lane_for(client, code, number, "the-pricing-rule")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    said = capsys.readouterr().out

    assert git(code, "rev-parse", "origin/main") == stable  # it moved nothing
    assert git(code, "rev-parse", "origin/develop") == git(path, "rev-parse", "HEAD")
    assert "main not promoted" in said and "promoting it is yours" in said
    assert CANNOT_UNDO in said
    # The hold rode along in the same push, so the closes behind it archive.
    assert (path / HOLD).is_file()
    assert HOLD in git(code, "diff", "--name-only", "origin/main...origin/develop")


def test_the_next_ordinary_fix_does_not_promote_what_is_waiting(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    """The leak this card closed: the second session changed nothing of that
    shape, and its own release would still have carried the first one's."""
    declare(client, CANNOT_UNDO)
    stable = git(code, "rev-parse", "origin/main")
    first = lane_for(client, code, number_of(client, PRICING), "the-pricing-rule")
    touch(first, CANNOT_UNDO, "RATE = 2\n")
    assert fold(first) == 0
    capsys.readouterr()

    second = lane_for(client, code, number_of(client, TIDES), "the-tide-table")
    git(second, "merge", "-q", "--ff-only", "origin/develop")
    touch(second, "README.md", "spelled right\n")
    assert fold(second) == 0
    said = capsys.readouterr().out
    assert "main not promoted" in said
    assert git(code, "rev-parse", "origin/main") == stable


def test_a_release_carrying_nothing_declared_promotes_as_it_always_did(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    path = lane_for(client, code, a_card(client), "the-pricing-rule")
    touch(path, "README.md", "spelled right\n")
    assert fold(path) == 0
    assert "main promoted" in capsys.readouterr().out
    assert git(code, "rev-parse", "origin/main") == git(path, "rev-parse", "HEAD")


def test_a_board_that_declares_nothing_promotes_exactly_as_before(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    turn(client, on=True)
    path = lane_for(client, code, a_card(client), "the-pricing-rule")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    assert "main promoted" in capsys.readouterr().out
    assert git(code, "rev-parse", "origin/main") == git(path, "rev-parse", "HEAD")


def test_a_session_the_owner_started_himself_is_untouched(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    number = a_card(client)
    name = f"card-{number}-his-own"
    path = code / ".claude" / "worktrees" / name
    git(code, "worktree", "add", "-q", "-b", name, str(path))
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    assert "main promoted" in capsys.readouterr().out
    assert git(code, "rev-parse", "origin/main") == git(path, "rev-parse", "HEAD")


# ── item 5: the card says the work is finished and the release is his ──


def test_the_card_says_the_work_landed_and_the_release_is_his(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    number = a_card(client)
    path = lane_for(client, code, number, "the-pricing-rule")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    refusal = next(
        line for line in capsys.readouterr().out.splitlines() if line.startswith("main not promoted")
    )
    said = refusal[len("main not promoted: ") :]

    card = client.get(f"/api/projects/{SLUG}/cards/{number}").json()
    waits = [row["text"] for row in card["card"]["rows"] if row["kind"] == "WAITS"]
    assert waits == [said]  # one wording, never a second

    tick(client)
    shown = _summary(board(client, SLUG), number)
    assert said in shown["state"]["detail"]
    assert shown["state"]["meaning"] == "yours"
    assert "release yours" in shown["claims"]


def test_a_session_that_died_before_its_hold_leaves_the_card_saying_so(
    client: TestClient, code: Path
):
    """The push landed and nothing wrote it down. The release still waits,
    and the card must say it is unheld and unclaimed rather than read as
    done."""
    declare(client, CANNOT_UNDO)
    number = a_card(client)
    path = lane_for(client, code, number, "the-pricing-rule")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    git(path, "push", "-q", "origin", "HEAD:develop")  # the fold, and then nothing
    git(code, "fetch", "-q", "origin")
    store = client.app.state.live.store
    record = store.lane(SLUG, number)
    assert record is not None
    store.record_lane(
        record.model_copy(update={"folded_at": NOW, "tip": git(path, "rev-parse", "HEAD")})
    )

    tick(client)
    shown = _summary(board(client, SLUG), number)
    assert shown["state"]["meaning"] == "broken"
    assert "release unheld" in shown["claims"]
    assert "promoting it is yours" in shown["state"]["detail"]


# ── item 4: a second one does not pile onto the first ──────────────────


def test_a_planned_card_of_the_same_shape_waits_and_one_beside_it_does_not(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    reconcile(client)
    holder = number_of(client, TIDES)
    path = lane_for(client, code, holder, "the-tide-table")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    capsys.readouterr()
    tick(client)

    live = client.app.state.live
    held = live.release_held(SLUG)
    assert held is not None and held.carries == [CANNOT_UNDO] and held.claimed

    # The pricing plan names the declared file; the storm plan does not.
    pricing = number_of(client, PRICING)
    waits = live.held_by_release(SLUG, pricing)
    assert waits is not None and "starts by itself" in waits and CANNOT_UNDO in waits
    beside = number_of(client, "A gate code arrives before the boat does")
    assert live.held_by_release(SLUG, beside) is None


def test_the_hold_lifts_by_itself_when_the_owner_promotes(
    client: TestClient, code: Path, capsys: pytest.CaptureFixture[str]
):
    declare(client, CANNOT_UNDO)
    path = lane_for(client, code, a_card(client), "the-pricing-rule")
    touch(path, CANNOT_UNDO, "RATE = 2\n")
    assert fold(path) == 0
    capsys.readouterr()
    tick(client)
    assert client.app.state.live.release_held(SLUG) is not None

    git(path, "push", "-q", "origin", "HEAD:main")  # his act
    git(code, "fetch", "-q", "origin")
    tick(client)
    assert client.app.state.live.release_held(SLUG) is None


def _summary(face: dict, number: int) -> dict:
    for column in face["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return card
    raise AssertionError(f"no card #{number} on the board")
