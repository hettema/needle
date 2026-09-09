"""Why a session ended is read at the end from the evidence that held the
process, never from the registry's word (plan 68, item 1): a kill inside
this life names the space it took, a kill older than the life is not this
death's cause, a boot under a live process is the boot's, and an ending
nothing names is written as not established."""

from datetime import UTC, datetime, timedelta

from domain.ending import Cause, Sighting
from domain.session import Session, SessionKind, SessionState
from domain.slot import Handoff, Limits
from runtime import handoffs, limits, reasons
from tests.floor import Floor

NOW = datetime(2026, 9, 5, 20, 40, tzinfo=UTC)
LANE_UNIT = "needle-card-435-x.scope"
DAEMON_UNIT = "claude-daemon-hrme.scope"


def session(recorded: str = "working", *, created: datetime = NOW - timedelta(hours=2)) -> Session:
    return Session(
        slot="hrme",
        config_dir="/srv/hrme",
        short_id="aaaa0001",
        session_id="aaaa0001-0000-4000-8000-000000000000",
        kind=SessionKind.BACKGROUND,
        name="card-435-x",
        cwd="/srv/p",
        worktree=None,
        state=SessionState.ENDED,
        recorded=recorded,
        detail="pass 2 fixes committed; pass 3 running",
        pid=None,
        scope=None,
        model=None,
        effort=None,
        stale=False,
        wall=None,
        intent="",
        created_at=created,
        updated_at=NOW,
        resumed_from=None,
        doing=None,
    )


def sighting(first: datetime, last: datetime, *, boot: str = "boot-0") -> Sighting:
    return Sighting(
        session_id="aaaa0001-0000-4000-8000-000000000000",
        project="proj",
        card_number=435,
        pid=4242,
        scope=DAEMON_UNIT,
        boot_id=boot,
        first_seen=first,
        last_seen=last,
    )


def name(machine_floor: Floor, **kw) -> reasons.Named:
    base = dict(
        units=[LANE_UNIT, DAEMON_UNIT],
        sighting=None,
        boots_seen=reasons.boots(),
        last_activity=None,
        now=NOW,
    )
    given = kw.pop("session", session())
    base.update(kw)
    return reasons.cause_of(given, **base)


def test_a_kill_inside_this_life_names_the_space_it_took(machine_floor: Floor):
    machine_floor.write_journal(
        LANE_UNIT,
        "2026-09-05T20:37:02+0200 DH systemd[1288]: Started needle-card-435-x.scope.",
        f"2026-09-05T20:29:10+0200 DH systemd[1288]: {LANE_UNIT}: systemd-oomd killed 12 "
        "process(es) in this unit.",
        f"2026-09-05T20:29:10+0200 DH systemd[1288]: {LANE_UNIT}: Failed with result 'oom-kill'.",
        f"2026-09-05T20:29:11+0200 DH systemd[1288]: {LANE_UNIT}: Consumed 2min CPU time.",
    )
    last_seen = datetime(2026, 9, 5, 18, 28, 50, tzinfo=UTC)
    in_lane_space = sighting(NOW - timedelta(hours=3), last_seen).model_copy(
        update={"scope": LANE_UNIT}
    )
    named = name(machine_floor, sighting=in_lane_space)
    assert named.cause == Cause.LANE_KILLED and named.settled
    assert named.words == (
        "the machine took back its memory at 2026-09-05 18:29Z (needle-card-435-x.scope: "
        "needle-card-435-x.scope: Failed with result 'oom-kill'.)"
    )
    assert named.last_alive_at == last_seen
    # A kill the process outlived is not its cause: seen alive after it,
    # the death is something later, and nothing else names it.
    outlived = name(
        machine_floor,
        sighting=in_lane_space.model_copy(update={"last_seen": NOW - timedelta(minutes=1)}),
    )
    assert outlived.cause == Cause.UNKNOWN, "seen alive after the kill: not the kill"
    survived = name(machine_floor, last_activity=datetime(2026, 9, 5, 18, 40, tzinfo=UTC))
    assert survived.cause == Cause.UNKNOWN, "active after the kill: not the kill"
    # A stale sighting with later transcript activity: the latest evidence
    # of life wins, and the outlived kill is not named.
    stale = name(
        machine_floor,
        sighting=in_lane_space,
        last_activity=datetime(2026, 9, 5, 18, 40, tzinfo=UTC),
    )
    assert stale.cause == Cause.UNKNOWN
    # A sighting names the space the process ran in: a kill in the other
    # space is not read for it.
    machine_floor.write_journal(
        DAEMON_UNIT,
        f"2026-09-05T20:29:30+0200 DH systemd[1288]: {DAEMON_UNIT}: systemd-oomd killed 9 "
        "process(es) in this unit.",
    )
    in_lane = name(
        machine_floor,
        sighting=sighting(NOW - timedelta(hours=3), last_seen).model_copy(
            update={"scope": LANE_UNIT}
        ),
    )
    assert in_lane.cause == Cause.LANE_KILLED
    # A unit that failed for a reason that is not the memory's is an ending
    # of another kind, never resumed as an oom death.
    machine_floor.write_journal(
        LANE_UNIT,
        f"2026-09-05T20:29:10+0200 DH systemd[1288]: {LANE_UNIT}: Failed with result 'signal'.",
    )
    crashed = name(
        machine_floor,
        sighting=sighting(NOW - timedelta(hours=3), last_seen).model_copy(
            update={"scope": LANE_UNIT}
        ),
    )
    assert crashed.cause == Cause.KILLED and "signal" in crashed.words


def test_a_kill_older_than_this_life_is_not_its_cause_and_the_daemons_kill_is(
    machine_floor: Floor,
):
    """#435 on 2026-09-05: its second life (from 18:38Z, in the daemon's
    space) ended at 20:29Z, and the board cited the lane space's 18:37Z
    kill, which took its first life."""
    machine_floor.write_journal(
        LANE_UNIT,
        f"2026-09-05T20:37:40+0200 DH systemd[1288]: {LANE_UNIT}: systemd-oomd killed 40 "
        "process(es) in this unit.",
    )
    machine_floor.write_journal(
        DAEMON_UNIT,
        f"2026-09-05T22:29:32+0200 DH systemd[1288]: {DAEMON_UNIT}: systemd-oomd killed 115 "
        "process(es) in this unit.",
    )
    second_life = datetime(2026, 9, 5, 18, 38, tzinfo=UTC)
    named = name(
        machine_floor,
        session=session(created=second_life),
        sighting=sighting(second_life, datetime(2026, 9, 5, 20, 29, tzinfo=UTC)),
        now=datetime(2026, 9, 5, 20, 40, tzinfo=UTC),
    )
    assert named.cause == Cause.DAEMON_KILLED
    assert "2026-09-05 20:29Z" in named.words and DAEMON_UNIT in named.words
    assert "18:37" not in named.words

    # With no sighting, the registry's birth of this id bounds the life the same way.
    named = name(
        machine_floor,
        session=session(created=second_life),
        now=datetime(2026, 9, 5, 20, 40, tzinfo=UTC),
    )
    assert named.cause == Cause.DAEMON_KILLED


def test_a_process_alive_when_the_laptop_went_down_died_with_it(machine_floor: Floor):
    machine_floor.write_boots(
        (-1, "3d9e048e", "2026-09-03T01:54:39+02:00", "2026-09-07T18:51:43+02:00"),
        (0, "5438b1ea", "2026-09-07T22:06:11+02:00", "2026-09-09T11:26:25+02:00"),
    )
    last = datetime(2026, 9, 7, 16, 51, 10, tzinfo=UTC)
    named = name(
        machine_floor,
        sighting=sighting(last - timedelta(hours=2), last, boot="3d9e048e"),
        now=datetime(2026, 9, 7, 20, 10, tzinfo=UTC),
    )
    assert named.cause == Cause.BOOT and named.settled
    assert named.words == (
        "the laptop went down: the machine's last record before it went down is at "
        "2026-09-07 16:51Z, it came back at 2026-09-07 20:06Z, and the session was alive at "
        "2026-09-07 16:51Z"
    )
    # A sighting in another boot than the one that ended there is not that
    # boot's casualty, whatever the times say.
    elsewhere = name(
        machine_floor,
        sighting=sighting(last - timedelta(hours=2), last, boot="some-other-boot"),
        now=datetime(2026, 9, 7, 20, 10, tzinfo=UTC),
    )
    assert elsewhere.cause == Cause.UNKNOWN
    # A transcript that last grew at the boot's end says the same for a row
    # nobody sighted (#85's four lanes predate the sightings).
    named = name(machine_floor, last_activity=last, now=datetime(2026, 9, 7, 20, 10, tzinfo=UTC))
    assert named.cause == Cause.BOOT
    # A process last known alive hours before the boot may have died of
    # anything: the boot is not named.
    named = name(
        machine_floor,
        last_activity=last - timedelta(hours=5),
        now=datetime(2026, 9, 7, 20, 10, tzinfo=UTC),
    )
    assert named.cause == Cause.UNKNOWN and named.settled
    assert "in a boot that ended 5.0 h later; the cause is not established" in named.words


def test_a_wall_a_stop_and_nothing(machine_floor: Floor):
    wall = Handoff(
        session_id="aaaa0001-0000-4000-8000-000000000000",
        short_id="aaaa0001",
        from_slot="hrme",
        account="armana",
        model="opus",
        prompt="",
        reason="You've hit your session limit · resets 9:30pm (Europe/Stockholm)",
        at=NOW - timedelta(hours=1),
        cwd=None,
        worktree=None,
        pid=None,
        stopped=False,
        path="/x",
        why="no Fable left anywhere; armana has the most weekly headroom",
    )
    walled = name(machine_floor, session=session().model_copy(update={"wall": wall}))
    assert walled.cause == Cause.WALL
    assert walled.words == (
        "its allowance ran out on hrme (You've hit your session limit · resets 9:30pm "
        "(Europe/Stockholm)), at 2026-09-05 19:40Z"
    )
    stopped = name(
        machine_floor, session=session("stopped").model_copy(update={"detail": "stopped"})
    )
    assert stopped.cause == Cause.STOPPED and stopped.words == "it was stopped through its account"
    # The daemon writes `stopped` with its own words for a session it lost
    # (#435: "ended while the background service was off"): a death it
    # reports, not a stop it made, so the cause is read from the machine.
    lost = name(
        machine_floor,
        session=session("stopped").model_copy(
            update={"detail": "ended while the background service was off"}
        ),
        last_activity=NOW - timedelta(minutes=3),
    )
    assert lost.cause == Cause.UNKNOWN
    assert lost.evidence == "the registry reads stopped: ended while the background service was off"
    nothing = name(machine_floor, last_activity=NOW - timedelta(minutes=3))
    assert nothing.cause == Cause.UNKNOWN and not nothing.settled
    assert nothing.words == (
        "the process disappeared after its last activity at 2026-09-05 20:37Z; "
        "the cause is not established"
    )
    # Never from the registry's word: `done` and a progress note name nothing.
    done = name(machine_floor, session=session("done"))
    assert done.cause == Cause.UNKNOWN and "finished" not in done.words


def test_a_handoff_says_what_it_asks_for():
    def handoff(why: str) -> Handoff:
        return Handoff(
            session_id="s",
            short_id="s",
            from_slot="hrme",
            account="hrme",
            model=None,
            prompt="",
            reason="x",
            at=NOW,
            cwd=None,
            worktree=None,
            pid=None,
            stopped=False,
            path="/x",
            why=why,
        )

    assert handoffs.cause_of(handoff("no Fable left anywhere; hrme has the most")) == Cause.WALL
    assert handoffs.cause_of(handoff("connection back after a transient death")) == Cause.RECOVERED
    assert (
        handoffs.cause_of(handoff("Fable headroom is back: Fable headroom on hrme; back on Fable"))
        == Cause.STRONGER_MODEL
    )
    assert handoffs.cause_of(handoff("")) == Cause.WALL


def test_the_accounts_snapshot_says_when_a_spent_allowance_returns(machine_floor: Floor):
    assert limits.snapshot("armana") is None
    machine_floor.write_limits(
        "armana",
        spent={"Session (5-hour)": 0.0, "Weekly (7-day)": 0.51, "Fable Weekly": 1.0},
        resets={
            "Weekly (7-day)": "2026-09-13T15:00:00.172950+00:00",
            "Fable Weekly": "2026-09-13T15:00:00.173305+00:00",
        },
        fetched_at=1788945726.29,
    )
    snap = limits.snapshot("armana")
    assert snap is not None and snap.spent["Fable Weekly"] == 1.0
    label, when = limits.next_reset(snap)
    assert label == "Fable Weekly" and when == datetime(2026, 9, 13, 15, 0, 0, 173305, tzinfo=UTC)
    nothing_gone = Limits(slot="a", fetched_at=NOW, spent={"Fable Weekly": 0.4}, resets=snap.resets)
    assert limits.next_reset(nothing_gone) is None
    two_gone = Limits(
        slot="a",
        fetched_at=NOW,
        spent={"Session (5-hour)": 1.0, "Fable Weekly": 1.0},
        resets={
            "Session (5-hour)": NOW + timedelta(hours=1),
            "Fable Weekly": NOW + timedelta(days=3),
        },
    )
    assert limits.next_reset(two_gone) == ("Session (5-hour)", NOW + timedelta(hours=1))


def test_boots_are_read_newest_first(machine_floor: Floor):
    assert reasons.boots() == []
    machine_floor.write_boots(
        (-1, "old", "2026-09-03T01:54:39+02:00", "2026-09-07T18:51:43+02:00"),
        (0, "new", "2026-09-07T22:06:11+02:00", "2026-09-09T11:26:25+02:00"),
    )
    listed = reasons.boots()
    assert [b.index for b in listed] == [0, -1]
    assert listed[1].last_entry == datetime(2026, 9, 7, 16, 51, 43, tzinfo=UTC)
