"""A card's lane driven by a colleague of the other make (card #63, item 1).

The rule answers `codex`, and the same click that gives a Claude lane its
worktree, its effort and its brief gives one to Codex: laid in the same
place, sandboxed to it, put in the card's own space on the machine, and read
by the board as a row of the one list. What it never gets is a walk down the
ladder — a wall, a handoff and a rung below are Claude's, and this make has
none of the three — so a launch that dies is a death with the log's words
and leaves the card as it found it.

The fake `codex` records the argv whole, so the sandbox, the writable roots
and the reasoning level the runtime asked for are read here rather than
believed; what the real sandbox does with them was probed on 2026-09-08 and
is written up in the machine's `docs/codex-on-this-machine.md`.
"""

import json
from pathlib import Path

import pytest

from domain.gate import Gate
from domain.launch import LaunchVerdict, Start, WindowlessStart
from domain.session import SessionKind
from runtime import launch
from runtime.service import Runtime
from tests.floor import Floor

BRIEF = "Read the plan and build item 1."
CARD = "card-63-the-strongest-model"


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launch, "CODEX_LANE_SECONDS", 1.0)
    monkeypatch.setattr(launch, "SCOPE_SETTLE_SECONDS", 0.3)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real repository, because a Codex lane's worktree is laid by git and
    not by the launcher's own flag."""
    import subprocess

    root = tmp_path / "repo"
    root.mkdir()
    for args in (
        ["init", "-q", "-b", "develop"],
        ["config", "user.email", "floor@example.com"],
        ["config", "user.name", "The Floor"],
        ["commit", "-q", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


@pytest.fixture
def runtime(store) -> Runtime:
    return Runtime(store)


def a_start(repo: Path) -> Start:
    return Start(repo=str(repo), card=CARD, brief=BRIEF, effort=Gate.HIGH, from_slot=None)


def lane_call(machine_floor: Floor) -> dict:
    calls = machine_floor.state().get("codex_lanes") or []
    assert calls, "the runtime never ran `codex exec` for the lane"
    return calls[-1]


def test_the_rule_naming_codex_gives_the_card_a_lane_of_the_other_make(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    machine_floor.answer_best(
        "codex", "gpt-6-astra", "no Fable left anywhere; codex has the top rung", make="codex"
    )
    machine_floor.script_codex(
        {"then": "linger", "session_id": "01a08000-0000-7000-8000-0000000000aa"}
    )

    result = runtime.start(a_start(repo))

    assert result.verdict == LaunchVerdict.ALIVE, result.reason
    assert result.session is not None
    # The board reads it as a Codex row, in the card's own worktree, in the
    # card's own space on the machine.
    assert result.session.slot == "codex" and result.session.kind == SessionKind.BACKGROUND
    assert result.session.model == "gpt-6-astra"
    assert result.session.worktree == str(repo / ".claude" / "worktrees" / CARD)
    # The floor can ask for a scope but cannot move a real process into one,
    # so the launch says so rather than claiming it — the same shape a Claude
    # lane's start has here.
    assert result.scope is None
    assert result.reason is not None and "not in its own space on the machine" in result.reason
    record = store.session_slot(result.session.session_id)
    assert record is not None and record.card == CARD and record.slot == "codex"
    assert record.scope == f"needle-{CARD}.scope"


def test_the_lane_gets_the_worktree_the_brief_and_the_effort_a_claude_lane_gets(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    machine_floor.answer_best("codex", "gpt-6-astra", make="codex")
    machine_floor.script_codex({"then": "linger"})

    runtime.start(a_start(repo))

    call = lane_call(machine_floor)
    worktree = repo / ".claude" / "worktrees" / CARD
    assert worktree.is_dir(), "the lane's own copy of the code was never laid"
    assert call["cwd"] == str(worktree)
    assert call["prompt"] == BRIEF
    assert call["model"] == "gpt-6-astra"
    argv = call["argv"]
    assert argv[:2] == ["-s", "workspace-write"]
    assert "-c" in argv and "model_reasoning_effort=high" in argv


def test_the_lane_may_write_its_own_branch_and_nothing_of_the_main_checkouts(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    """The writable roots are the boundary, so they are read here by name.
    What each one buys was proved against the real sandbox on 2026-09-08: with
    these four the lane commits on its branch, and without them a commit dies
    on `.git/index.lock`; with them the main checkout's index and working
    tree stay refused."""
    machine_floor.answer_best("codex", "gpt-6-astra", make="codex")
    machine_floor.script_codex({"then": "linger"})

    runtime.start(a_start(repo))

    argv = lane_call(machine_floor)["argv"]
    roots = next(a for a in argv if a.startswith("sandbox_workspace_write.writable_roots="))
    named = json.loads(roots.split("=", 1)[1])
    git = repo / ".git"
    assert str(git / "worktrees" / CARD) in named
    assert {str(git / part) for part in ("objects", "refs", "logs")} <= set(named)
    # Never the main checkout, its index or its working tree.
    assert str(repo) not in named and str(git) not in named
    assert "sandbox_workspace_write.network_access=true" in argv


def test_a_lane_that_never_came_alive_leaves_no_worktree_and_says_why(
    machine_floor: Floor, runtime: Runtime, repo: Path, store
):
    machine_floor.answer_best("codex", "gpt-6-astra", make="codex")
    machine_floor.script_codex({"then": "fail", "stderr": "error: stream disconnected"})

    result = runtime.start(a_start(repo))

    assert result.verdict == LaunchVerdict.DEAD
    assert result.reason is not None and "stream disconnected" in result.reason
    assert result.session is None
    assert not (repo / ".claude" / "worktrees" / CARD).exists()
    assert [a.verdict for a in result.attempts] == [LaunchVerdict.DEAD]


def test_a_failed_launch_never_takes_back_a_copy_of_the_code_it_did_not_make(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    """A worktree already there is a previous life's, with its commits in it.
    A fresh launch that dies takes back only what it laid; removing the other
    would destroy work no launch of ours wrote."""
    import subprocess

    path = repo / ".claude" / "worktrees" / CARD
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-b", CARD, str(path)],
        check=True,
        capture_output=True,
    )
    (path / "the-work.txt").write_text("a previous life's commit", encoding="utf-8")
    machine_floor.answer_best("codex", "gpt-6-astra", make="codex")
    machine_floor.script_codex({"then": "fail", "stderr": "error: stream disconnected"})

    result = runtime.start(a_start(repo))

    assert result.verdict == LaunchVerdict.DEAD
    assert path.is_dir() and (path / "the-work.txt").is_file()


def test_a_reading_is_asked_of_the_rule_with_the_other_makes_rung_spent(
    machine_floor: Floor, runtime: Runtime, repo: Path
):
    """A session with no window works in the project's own checkout, and the
    lane this card gave the other make is sandboxed to a worktree. So the
    rule is asked with that rung already spent rather than answered around:
    the one rule stays the one rule."""
    machine_floor.answer_best("alpha", None, "Fable headroom on alpha")
    machine_floor.script_launches({"then": "register", "state": "working"})

    runtime.start_windowless(
        WindowlessStart(repo=str(repo), card="a-reading", brief=BRIEF, effort=Gate.LOW)
    )

    asked = machine_floor.state()["best_calls"][-1]
    assert "--tried" in asked and "codex" in asked[asked.index("--tried") + 1]
