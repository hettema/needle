"""A record that skipped the read cannot close a card (card #110), on the floor:
every record a close names is read where the lane stands and held to the
forms `docs/reviews/README.md` sets — a fix line with both halves, a verdict
per round whose call is a row of the other make that landed, a disposition
for every claim the reader broke — while a record dated on or before the
fold's day closes as it did before; the lane's opening brief says so in one
sentence."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from api.cli import main
from domain.machine import Machine
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, archive_plan, column_of, git
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

PLAN = "docs/plans/done/2026-09-03-every-metered-kilowatt-is-billed.md"
NOW = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)
CODEX_SESSION = "01a08a3a-0000-7000-8000-000000000000"

HELD = """# Review — the meter

**Plan:** {plan}
**Reviewer:** the build session
**Findings:** 2

## The passes

1. **The feature.** The meter billed a berth twice on a retry; findings 1 to 2.
Read cold by Codex (01a08a3a) on abc1234, call {call}: {verdict}

## Dispositions

### Pass 1's findings

1. [feature] The berth was billed twice — FIXED in abc1234; reaches the retry path and the
   invoice mailer; assumes the sweep runs after the bill is written.
2. [seam] The sweep read the bill early — FIXED in abc1234{second}
"""

BOTH = "; reaches the sweep alone; assumes nobody else reads the table."


def record(
    *, plan: str = PLAN, call: int = 1, verdict: str = "complete", second: str = BOTH
) -> str:
    return HELD.format(plan=plan, call=call, verdict=verdict, second=second)


def a_code_lane(client: TestClient, machine_floor: Floor, repo: Path) -> Path:
    """A lane that folded code, its plan archived: the close then needs a
    record, as card #75's test on the dial lays it."""
    doors.start(client)
    started = machine_floor.state()["launch_log"][0]
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    (worktree / "engine").mkdir(exist_ok=True)
    (worktree / "engine" / "meter.py").write_text("bill = True\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "the meter")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    archive_plan(repo)
    return worktree


def a_landed_codex_call(client: TestClient, machine_floor: Floor, repo: Path) -> int:
    """A call row of the other make whose answer landed: what a verdict
    line names."""
    store = client.app.state.loops.live.store
    answer = machine_floor.discussion / "from-01a08a3a-re-round-one.md"
    row = store.record_call(
        session_id=CODEX_SESSION,
        slot="codex",
        name="codex-01a08a3a",
        note=str(machine_floor.discussion / "round-one.md"),
        answer=str(answer),
        brief="read the round",
        caller=str(repo),
        at=NOW,
    )
    store.end_call(row.id, NOW, f"{answer} landed at 2026-09-11T09:01:00+00:00: complete")
    return row.id


def close(review: str | None, capsys) -> tuple[int, str, str]:
    watch = f"the plan is archived — file {PLAN} by 2026-12-31 every 1h"
    argv = ["close", "proj", str(CARD), "--delivered", "bills", "--watch", watch]
    if review is not None:
        argv += ["--review", review]
    capsys.readouterr()
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


def write(repo: Path, name: str, text: str) -> str:
    (repo / "docs" / "reviews").mkdir(exist_ok=True)
    (repo / "docs" / "reviews" / name).write_text(text, encoding="utf-8")
    return f"docs/reviews/{name}"


def test_a_dated_record_with_a_bare_fix_line_refuses_and_with_both_halves_closes(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    path = write(repo, "2026-09-11-the-meter.md", record(call=call, second="."))
    code, _, err = close(path, capsys)
    assert code == 1
    assert "skipped the read HOW-WE-WORK §13 asks for" in err
    assert f"{path}:18 FIXED says no reaches or assumes" in err, err
    assert column_of(client, CARD) == "Executing", "nothing was written"

    write(repo, "2026-09-11-the-meter.md", record(call=call))
    code, out, _ = close(path, capsys)
    assert code == 0, out
    assert "DELIVERED, WATCH, REVIEW" in out


def test_a_record_dated_on_or_before_the_fold_closes_as_before(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    # Hello Revenue's template headed a record with `**Card:**` and no plan
    # line until this card: a record written under the old form is history,
    # its stem included (ruling 3; the author's first pass).
    bare = "# Review\n\n**Card:** #253\n\n## Dispositions\n\n1. The meter — FIXED in abc1234.\n"
    path = write(repo, "2026-09-10-the-meter.md", bare)
    code, out, _ = close(path, capsys)
    assert code == 0, out


def test_a_record_outside_the_project_without_a_date_or_naming_another_plan_is_refused(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    outside = repo.parent / "2026-09-11-elsewhere.md"
    outside.write_text(record(call=call), encoding="utf-8")
    code, _, err = close(str(outside), capsys)
    assert code == 1 and "is not a path inside the project's tree" in err
    code, _, err = close("../2026-09-11-elsewhere.md", capsys)
    assert code == 1 and "is not a path inside the project's tree" in err

    undated = write(repo, "the-meter.md", record(call=call))
    code, _, err = close(undated, capsys)
    assert code == 1 and "carries no date in its name" in err

    other = write(
        repo,
        "2026-09-11-the-meter.md",
        record(call=call, plan="docs/plans/done/2026-09-01-another-card.md"),
    )
    code, _, err = close(other, capsys)
    assert code == 1
    assert "names the plan 2026-09-01-another-card" in err
    assert "2026-09-03-every-metered-kilowatt-is-billed" in err


def test_a_docs_only_lane_that_names_a_record_has_it_validated(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    doors.start(client)
    started = machine_floor.state()["launch_log"][0]
    worktree = (
        repo / ".claude" / "worktrees" / started["argv"][started["argv"].index("--worktree") + 1]
    )
    (worktree / "docs" / "note.md").write_text("words\n", encoding="utf-8")
    git(worktree, "add", "-A")
    git(worktree, "commit", "-q", "-m", "a note")
    assert main(["fold", "--worktree", str(worktree)]) == 0
    archive_plan(repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    path = write(repo, "2026-09-11-the-meter.md", record(call=call, second="."))
    code, _, err = close(path, capsys)
    assert code == 1 and "FIXED says no reaches or assumes" in err
    write(repo, "2026-09-11-the-meter.md", record(call=call))
    code, out, _ = close(path, capsys)
    assert code == 0, out


def test_a_round_without_a_verdict_a_verdict_without_its_row_and_a_broken_claim_unanswered_refuse(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    no_verdict = record(call=call).replace(
        f"Read cold by Codex (01a08a3a) on abc1234, call {call}: complete\n", ""
    )
    path = write(repo, "2026-09-11-the-meter.md", no_verdict)
    code, _, err = close(path, capsys)
    assert code == 1 and "pass 1's round has FIXED lines and no verdict under it" in err

    write(repo, "2026-09-11-the-meter.md", record(call=call + 7))
    code, _, err = close(path, capsys)
    assert code == 1 and f"names call {call + 7}, which the board has no row for" in err

    write(repo, "2026-09-11-the-meter.md", record(call=call, verdict="broke 1.2 — the nightly job"))
    code, _, err = close(path, capsys)
    assert code == 1
    assert "broke 1.2 and no disposition marked `[repair of 1.2]` says what became of it" in err

    # A fix that answers a break is a new repair, and a new repair is read
    # (pass two's reader): the round ends on a verdict that says complete.
    fixed = record(call=call, verdict="broke 1.2 — the nightly job") + (
        "3. [seam] [repair of 1.2] The nightly job reads the table too — FIXED in bcd2345; "
        "reaches the nightly job and the sweep; assumes the two never run at once.\n"
    )
    write(repo, "2026-09-11-the-meter.md", fixed)
    code, _, err = close(path, capsys)
    assert code == 1 and "the fix that answers it was never read cold" in err

    read_again = fixed.replace(
        "\n## Dispositions",
        f"Read cold by Codex (01a08a3a) on bcd2345, call {call}: complete\n\n## Dispositions",
    )
    write(repo, "2026-09-11-the-meter.md", read_again)
    code, out, _ = close(path, capsys)
    assert code == 0, out


def test_a_verdict_from_a_colleague_of_the_lanes_own_kind_or_that_never_landed_refuses(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    store = client.app.state.loops.live.store
    answer = machine_floor.discussion / "from-claude-re-round-one.md"
    own = store.record_call(
        session_id="claude-0000",
        slot="alpha",
        name="colleague-x",
        note=str(machine_floor.discussion / "round-one.md"),
        answer=str(answer),
        brief="read the round",
        caller=str(repo),
        at=NOW,
    )
    store.end_call(own.id, NOW, f"{answer} landed at 2026-09-11T09:01:00+00:00: complete")
    path = write(repo, "2026-09-11-the-meter.md", record(call=own.id))
    code, _, err = close(path, capsys)
    assert code == 1 and "a colleague of the lane's own kind" in err

    never = store.record_call(
        session_id=CODEX_SESSION,
        slot="codex",
        name="codex-01a08a3a",
        note=str(machine_floor.discussion / "round-one.md"),
        answer=str(machine_floor.discussion / "from-01a08a3a-re-round-one.md"),
        brief="read the round",
        caller=str(repo),
        at=NOW,
    )
    write(repo, "2026-09-11-the-meter.md", record(call=never.id))
    code, _, err = close(path, capsys)
    assert code == 1 and f"call {never.id}'s answer never landed after the call" in err


def test_a_lane_on_the_second_machine_has_its_record_read_there(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, tmp_path: Path
):
    """The second floor shares this one's disk, so every read of the lane's
    worktree would find it here; the proof is the routing — the door asks
    the runtime which machine holds the lane and reads the record through
    the lane-document path, which goes over the wire for a lane placed on
    the rented machine (as `tests/runtime/test_machines.py` proves the
    path itself)."""
    worktree = a_code_lane(client, machine_floor, repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    store = client.app.state.loops.live.store
    other = machine_floor.lay_host("rented", available_gb=24.0)
    store.add_machine(
        Machine(
            name="laptop",
            machine_id=machine_floor.machine_id,
            host=None,
            desktop=True,
            ground=str(tmp_path),
            command="needle",
            added_at=NOW,
        )
    )
    store.add_machine(
        Machine(
            name="rented",
            machine_id=other.machine_id,
            host="rented",
            desktop=False,
            ground=None,
            command="needle",
            added_at=NOW,
        )
    )
    doors.reconcile(client)
    # The board's own record says where the lane was last seen; the close
    # runs in its own process and reads that record to route the read.
    known = store.lane("proj", CARD)
    assert known is not None and known.path == str(worktree)
    store.record_lane(known.model_copy(update={"machine": "rented"}))
    (worktree / "docs" / "reviews").mkdir(exist_ok=True)
    (worktree / "docs" / "reviews" / "2026-09-11-the-meter.md").write_text(
        record(call=call), encoding="utf-8"
    )
    before = len(machine_floor.state().get("ssh_calls", []))
    code, out, _ = close("docs/reviews/2026-09-11-the-meter.md", capsys)
    assert code == 0, out
    asked = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])[before:]]
    assert any("lane-docs" in a for a in asked), asked


def test_a_lane_whose_worktree_is_only_on_the_second_machine_is_asked_there(
    client: TestClient, machine_floor: Floor, repo: Path, capsys, tmp_path: Path
):
    """Pass two's reader: a local `is_dir` on a path that exists only on
    the rented machine read every remote lane as gone, so the record was
    never asked for over the wire. The lane's record is moved to a path
    this disk does not hold; the close asks the rented machine for the
    lane's files and its record, and falls to the project's own copy."""
    worktree = a_code_lane(client, machine_floor, repo)
    call = a_landed_codex_call(client, machine_floor, repo)
    store = client.app.state.loops.live.store
    other = machine_floor.lay_host("rented", available_gb=24.0)
    store.add_machine(
        Machine(
            name="laptop",
            machine_id=machine_floor.machine_id,
            host=None,
            desktop=True,
            ground=str(tmp_path),
            command="needle",
            added_at=NOW,
        )
    )
    store.add_machine(
        Machine(
            name="rented",
            machine_id=other.machine_id,
            host="rented",
            desktop=False,
            ground=None,
            command="needle",
            added_at=NOW,
        )
    )
    doors.reconcile(client)
    known = store.lane("proj", CARD)
    assert known is not None and known.path == str(worktree)
    elsewhere = "/srv/rented/worktrees/" + Path(known.path).name
    store.record_lane(known.model_copy(update={"machine": "rented", "path": elsewhere}))
    write(repo, "2026-09-11-the-meter.md", record(call=call))
    before = len(machine_floor.state().get("ssh_calls", []))
    code, out, _ = close("docs/reviews/2026-09-11-the-meter.md", capsys)
    assert code == 0, out
    asked = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])[before:]]
    assert any("lane-docs" in a and elsewhere in a for a in asked), asked


def test_the_lanes_brief_says_what_the_cold_read_of_a_round_is(
    client: TestClient, machine_floor: Floor
):
    doors.start(client)
    brief = machine_floor.state()["launch_log"][0]["argv"][-1]
    assert "Every round of repairs — a pass and the fixes it caused — is read cold" in brief
    assert "call codex --fresh <note>" in brief and "wait <n>" in brief
    for question in (
        "who else calls this",
        "what is the sibling case",
        "what list was written by hand",
        "what does the fix assume, and what drove it",
    ):
        assert question in brief, question
    assert "`Read cold by <who> on <sha>, call <n>: complete`" in brief
    assert "[repair of <pass.finding>]" in brief
