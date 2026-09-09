"""The runtime can tell him (card #41, item 1): a notice on the floor leaves
one `notify-send` argv that stays until dismissed with the one action, and
one `pw-play` argv naming the sound; without the commands it says why;
and the button puts the card in front of him — the board asked, a board
window focused, or the desktop entry opened on the card's page."""

import time

import pytest

from domain.notice import Moment, Notice
from runtime import machine, notice
from runtime.windows import WindowRefused
from tests.floor import Floor

NOTICE = Notice(
    project="proj",
    project_name="Harbourmaster",
    card_number=253,
    title="Every metered kilowatt is billed",
    words="Moved to Executed: the close landed: the plan is archived and DELIVERED is written",
    moment=Moment.MOVED_ON,
)


def settled(floor: Floor, key: str, count: int, seconds: float = 5.0) -> list:
    """The fakes run in a shell the runtime never waits on; a test does."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        found = floor.state().get(key, [])
        if len(found) >= count:
            return found
        time.sleep(0.05)
    raise AssertionError(f"{key} never reached {count}: {floor.state().get(key)}")


def test_a_notice_stays_until_dismissed_and_rings_the_moments_sound(machine_floor: Floor):
    told = notice.tell(NOTICE, ["true"])
    assert told.raised and told.words == NOTICE.words
    (argv,) = settled(machine_floor, "notified", 1)
    assert argv[:6] == ["-u", "critical", "-t", "0", "-a", "notify-send"]
    assert argv[6:8] == ["-A", "default=Open the board"]
    assert argv[8:] == ["Needle · Harbourmaster #253: Every metered kilowatt is billed", NOTICE.words]
    (played,) = settled(machine_floor, "played", 1)
    assert played == ["/usr/share/sounds/freedesktop/stereo/complete.oga"]

    asks = NOTICE.model_copy(update={"words": "Asking you: high or medium?", "moment": Moment.NEEDS_YOU})
    assert notice.tell(asks, ["true"]).raised
    played = settled(machine_floor, "played", 2)
    assert played[1] == ["/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"]


def test_the_button_runs_what_it_was_given_and_a_dismissal_runs_nothing(
    machine_floor: Floor, tmp_path
):
    mark = tmp_path / "pressed"
    opens = ["sh", "-c", f"echo pressed > {mark}"]
    notice.tell(NOTICE, opens)
    settled(machine_floor, "notified", 1)
    time.sleep(0.3)
    assert not mark.exists(), "dismissed: the button's command never ran"

    machine_floor.update(press="default")
    notice.tell(NOTICE, opens)
    settled(machine_floor, "notified", 2)
    deadline = time.time() + 5
    while time.time() < deadline and not mark.exists():
        time.sleep(0.05)
    assert mark.read_text().strip() == "pressed"


def test_without_the_notifier_the_words_say_why_and_nothing_is_raised(
    machine_floor: Floor, monkeypatch: pytest.MonkeyPatch, tmp_path
):
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    told = notice.tell(NOTICE, ["true"])
    assert not told.raised
    assert told.words == "could not tell you: `notify-send` is not on PATH"
    assert machine_floor.state()["notified"] == []


def test_show_asks_the_board_and_focuses_an_open_board_window_whatever_it_shows(
    machine_floor: Floor,
):
    machine_floor.write_board_entry("proj")
    machine_floor.update(
        urls={"http://127.0.0.1:8480/api/show/proj/253": {"code": 200, "body": "{}"}},
        clients=[
            {
                "address": "0xboard01",
                "class": "chrome-127.0.0.1__p_other-Profile_5",
                "initialClass": "chrome-127.0.0.1__p_other-Profile_5",
                "title": "Other · Needle",
            },
            {
                "address": "0xboard02",
                "class": "chrome-127.0.0.1__p_proj-Profile_5",
                "initialClass": "chrome-127.0.0.1__p_proj-Profile_5",
                "title": "Harbourmaster · Needle",
            },
        ],
    )
    said = notice.show("proj", 253)
    assert said == (
        "Showed #253 on proj: the board was asked to show it; focused the board's window "
        "(0xboard02)."
    ), "the window already on the card's project comes first"
    assert machine_floor.state()["focus_calls"] == ["0xboard02"]
    assert machine_floor.state()["spawned"] == [], "a window was open, so none was opened"

    # Only another project's board is open: it is focused, and its page switches.
    machine_floor.update(clients=[machine_floor.state()["clients"][0]], focus_calls=[])
    assert notice.show("proj", 253).endswith("focused the board's window (0xboard01).")
    assert machine_floor.state()["focus_calls"] == ["0xboard01"]


def test_show_opens_the_desktop_entry_on_the_card_when_no_board_window_is_open(
    machine_floor: Floor,
):
    machine_floor.write_board_entry("proj")
    said = notice.show("proj", 253)
    assert said == (
        "Showed #253 on proj: the board could not be asked (curl: (7) Failed to connect to "
        "http://127.0.0.1:8480/api/show/proj/253); no board window was open, so "
        "http://127.0.0.1:8480/p/proj#card-253 was opened."
    )
    (spawned,) = machine_floor.state()["spawned"]
    assert spawned["command"] == ["--app=http://127.0.0.1:8480/p/proj#card-253"]
    assert spawned["app_id"] == "chrome-127.0.0.1__p_proj-Profile_5"


def test_show_refuses_by_name_without_an_entry_or_when_focus_does_not_land(
    machine_floor: Floor,
):
    with pytest.raises(notice.NoBoardEntry, match="opens the board on proj"):
        notice.show("proj", 253)
    machine_floor.write_board_entry("proj")
    machine_floor.update(
        clients=[{"address": "0xboard01", "class": "chrome-127.0.0.1__p_proj-Profile_5"}],
        focus_works=False,
    )
    with pytest.raises(WindowRefused, match="still reports"):
        notice.show("proj", 253)


def test_the_entry_is_read_as_the_machine_wrote_it(machine_floor: Floor):
    path = machine_floor.write_board_entry("proj", base="http://localhost:9999")
    entry = notice.board_entry("proj")
    assert entry.path == str(path) and entry.base == "http://localhost:9999"
    assert entry.host == "localhost:9999"
    assert entry.argv[-1] == "--app=http://localhost:9999/p/proj"
    assert machine.applications_dir() == machine_floor.applications
