"""The store's rows for a call and for a lane's hearing of the machine's
watercooler (plan 17): a call is recorded, follows a fork, and ends once;
the notes a lane heard are stamped per path and cleared with the lane."""

from datetime import UTC, datetime, timedelta

from domain.lane import LaneRecord

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def record(store) -> None:
    return store.record_call(
        session_id="aaaa0001-0000-4000-8000-000000000000",
        slot="alpha",
        name="colleague-x",
        note="/srv/d/from-codex-topic.md",
        answer="/srv/d/from-aaaa0001-re-topic.md",
        brief="read the note",
        caller="/srv/chair",
        at=NOW,
    )


def test_a_call_is_recorded_follows_a_fork_and_ends_once(store):
    call = record(store)
    assert call.id == 1 and call.ended_at is None and call.moved is None
    assert store.call(1) == call and store.call(2) is None
    assert store.calls(open_only=True) == [call]

    store.move_call(1, "bbbb0002-0000-4000-8000-000000000000", "beta", "moved to beta")
    moved = store.call(1)
    assert moved is not None
    assert (moved.session_id, moved.slot, moved.moved) == (
        "bbbb0002-0000-4000-8000-000000000000",
        "beta",
        "moved to beta",
    )

    store.end_call(1, NOW + timedelta(minutes=5), "the answer landed")
    store.end_call(1, NOW + timedelta(minutes=9), "said twice")
    ended = store.call(1)
    assert ended is not None
    assert (ended.ended_at, ended.words) == (NOW + timedelta(minutes=5), "the answer landed")
    assert store.calls(open_only=True) == [] and store.calls() == [ended]
    assert store.calls(since=NOW) == [ended] and store.calls(since=NOW + timedelta(seconds=1)) == []


def test_heard_notes_are_stamped_per_path_and_cleared_with_the_lane(store, project):
    store.add_project(project)
    slug = project.slug
    assert store.heard_notes(slug, 7) == {}
    store.stamp_notes(slug, 7, {"/srv/d/a.md": NOW, "/srv/d/b.md": NOW})
    store.stamp_notes(slug, 7, {"/srv/d/a.md": NOW + timedelta(seconds=1)})
    assert store.heard_notes(slug, 7) == {
        "/srv/d/a.md": NOW + timedelta(seconds=1),
        "/srv/d/b.md": NOW,
    }
    assert store.heard_notes(slug, 8) == {}

    store.record_lane(
        LaneRecord(
            project=slug,
            card_number=7,
            name="card-7-x",
            path="/srv/p/.claude/worktrees/card-7-x",
            branch="worktree-card-7-x",
            birth=None,
            tip=None,
            first_seen=NOW,
            last_seen=NOW,
            gone_at=None,
            folded_at=None,
            trunk_synced_at=None,
            main_synced_at=None,
        )
    )
    store.forget_lane(slug, 7)
    assert store.heard_notes(slug, 7) == {}, "a card launched again hears afresh"
