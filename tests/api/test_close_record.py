"""Finite review evidence and identity protections at the real close door."""

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

HELD = """# Review — the meter

**Plan:** {plan}
**Reviewer:** independent Codex reader
**Verification:** Retry and sweep tests passed after fixes.
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


def test_one_review_and_verified_repairs_close_without_call_rows(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    text = record(second=".").replace(
        "Read cold by Codex (01a08a3a) on abc1234, call 1: complete\n", ""
    )
    path = write(repo, "2026-09-11-the-meter.md", text)
    code, out, err = close(path, capsys)
    assert code == 0, err
    assert "DELIVERED, WATCH, REVIEW" in out


def test_old_record_with_evidence_can_close_without_new_plan_head(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    text = (
        record()
        .replace(f"**Plan:** {PLAN}\n", "")
        .replace("**Verification:** Retry and sweep tests passed after fixes.\n", "")
        + "\n## What was checked\nRetry tests passed after repairs.\n"
    )
    path = write(repo, "2026-09-10-the-meter.md", text)
    code, out, err = close(path, capsys)
    assert code == 0, err


def test_a_record_outside_the_project_without_a_date_or_naming_another_plan_is_refused(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    call = 1
    outside = repo.parent / "2026-09-11-elsewhere.md"
    outside.write_text(record(call=call), encoding="utf-8")
    code, _, err = close(str(outside), capsys)
    assert code == 1 and "is not a path inside the project's tree" in err
    code, _, err = close("../2026-09-11-elsewhere.md", capsys)
    assert code == 1 and "is not a path inside the project's tree" in err

    code, _, err = close("docs/reviews/2026-09-11-missing.md", capsys)
    assert code == 1 and "is not in the project's tree" in err

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

    # An explicit plan identity remains meaningful even in a legacy record.
    other_old = write(
        repo,
        "2026-09-10-the-meter.md",
        record(plan="docs/plans/done/2026-09-01-another-card.md"),
    )
    code, _, err = close(other_old, capsys)
    assert code == 1 and "names the plan 2026-09-01-another-card" in err


def test_docs_only_close_still_validates_a_supplied_record(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    doors.start(client)
    archive_plan(repo)
    path = write(repo, "2026-09-11-the-meter.md", f"**Plan:** {PLAN}\n")
    code, _, err = close(path, capsys)
    assert code == 1 and "Reviewer" in err
    write(repo, "2026-09-11-the-meter.md", record())
    code, _, err = close(path, capsys)
    assert code == 0, err


def test_blank_evidence_refuses_without_moving_the_card(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    for date in ("2026-09-10", "2026-09-11"):
        path = write(
            repo, f"{date}-the-meter.md", f"**Plan:** {PLAN}\n**Reviewer:** \n**Verification:** \n"
        )
        code, _, err = close(path, capsys)
        assert code == 1 and "Reviewer" in err and "verification evidence" in err
        assert column_of(client, CARD) == "Executing"


def test_disproved_and_outside_findings_do_not_require_another_cold_read(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    a_code_lane(client, machine_floor, repo)
    text = record(verdict="broke 1.2 — alleged race") + (
        "3. [seam] [repair of 1.2] Alleged race is serialized by the transaction, "
        "verified by the retry regression — NO CHANGE.\n"
        "4. [boundary] Unrelated export issue — filed as docs/slice-suggestions/export.md.\n"
    )
    path = write(repo, "2026-09-11-the-meter.md", text)
    code, _, err = close(path, capsys)
    assert code == 0, err


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
    call = 1
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
    # The lane's session ran where the lane is: the rented floor's registry names
    # it on the worktree, which is where the close reads the lane's make from.
    other.write_job("alpha", "far00002", state="done", cwd=str(worktree), worktree=str(worktree))
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
    call = 1
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
    # The lane's own session ran there: the rented floor's registry names it
    # on that worktree, which is where the close reads the lane's make from.
    other.write_job("alpha", "far00001", state="done", cwd=elsewhere, worktree=elsewhere)
    # The tree there is gone too: the machine answers empty, and the project's
    # own checkout says what the lane folded (the cold read of pass two's
    # round), so a close without a record is still a code lane's, refused.
    code, _, err = close(None, capsys)
    assert code == 1 and "folded code (engine/meter.py)" in err, err
    # With neither a birth nor a tip on record, the board cannot tell what
    # the lane folded, and says so (the cold read of round nine).
    store.record_lane(
        known.model_copy(
            update={"machine": "rented", "path": elsewhere, "birth": None, "tip": None}
        )
    )
    code, _, err = close(None, capsys)
    assert code == 1 and "--review" in err, (
        err
    )  # gone, unrecorded: a record is asked for either way
    store.record_lane(known.model_copy(update={"machine": "rented", "path": elsewhere}))
    write(repo, "2026-09-11-the-meter.md", record(call=call))
    before = len(machine_floor.state().get("ssh_calls", []))
    code, out, _ = close("docs/reviews/2026-09-11-the-meter.md", capsys)
    assert code == 0, out
    asked = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])[before:]]
    assert any("lane-docs" in a and elsewhere in a for a in asked), asked


def test_the_lane_brief_points_to_the_canonical_review_contract(
    client: TestClient, machine_floor: Floor
):
    doors.start(client)
    brief = machine_floor.state()["launch_log"][0]["argv"][-1]
    assert "/home/dennis/Work/needle/docs/HOW-WE-WORK.md §13" in brief
    assert "/home/dennis/Work/needle/docs/reviews/README.md" in brief
    assert "Every round of repairs" not in brief
    assert "the next pass re-reads" not in brief
