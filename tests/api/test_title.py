"""Every card title says what it is for at a glance, in plain words (card
#74), on the floor.

The owner ranks cards from their titles alone and could not read his own
board. What is held here, against the served fixture:

- item 3, the cold read at birth: a plan carded with a vocabulary word in
  its title is read by the dial's seat, the reading's failing verdict is a
  machine fact on the face with the reader's words and the words that
  failed, its Start door is closed with that fact as the reason, the hold
  survives a rewrite until a reading of the new title passes, and then
  clears; the same on an idea, and the same on a second project, so the
  hold is the board's and not one project's; a defect's reading lands the
  mark's result and the title's verdict together and the title changes no
  routing; a reading of a plan is refused a mark's result and a reading of
  a defect is refused without one;
- item 4, the line under a defect's title names the intent it breaks and
  never where the code is: a defect with the section shows its first
  sentence, one without it shows its first path-free sentence.
"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from domain.card import CardOrigin
from domain.project import Project
from infrastructure.live import sweep
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_dial import (
    SOURCE,
    number_of,
    open_readings,
    read_the_rail_until,
    tick,
    turn,
    write_defect,
)
from tests.api.test_doors import detail, git, reconcile
from tests.conftest import NOW, write_plan, write_suggestion
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

JARGON = "A lane the machine ended comes back by itself"
PLAIN = "Work the laptop interrupted picks itself up again"


def face_of(client: TestClient, number: int, slug: str = "proj") -> dict:
    board = client.get(f"/api/projects/{slug}/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return card
    raise AssertionError(f"#{number} is not on the {slug} board")


def landed(repo: Path, message: str) -> None:
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", message)


def card_a_plan(client: TestClient, repo: Path, slug: str, stem: str, title: str) -> int:
    write_plan(repo, stem, title=title, intent="The owner gets the work back. Because.")
    landed(repo, stem)
    client.app.state.loops.live.rescan(slug)
    reconcile(client)
    return number_of(client, title) if slug == "proj" else _number_on(client, slug, title)


def _number_on(client: TestClient, slug: str, title: str) -> int:
    board = client.get(f"/api/projects/{slug}/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["title"] == title:
                    return card["number"]
    raise AssertionError(f"no card titled {title!r} on {slug}")


def retitle(client: TestClient, repo: Path, slug: str, path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8").replace(f"# {old}", f"# {new}", 1))
    landed(repo, "retitled")
    client.app.state.loops.live.rescan(slug)
    reconcile(client)


def read_cold(
    client: TestClient, machine_floor: Floor, slug: str, number: int, *argv: str
) -> dict:
    """Tick until the seat opens on this card, land the verdict given, and
    hand back the launch that opened it."""
    opened = read_the_rail_until(client, machine_floor, number, slug=slug)
    assert main(["triage", slug, str(number), *argv]) == 0
    reconcile(client)
    return opened


# ── item 3: the cold read at birth ─────────────────────────────────────


def test_a_plan_with_a_vocabulary_word_is_marked_on_its_face_and_held_until_a_reading_passes(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, capsys
):
    turn(client, on=True, lanes=1)
    stem = "2026-09-07-a-lane-the-machine-ended-comes-back-by-itself"
    number = card_a_plan(client, repo, "proj", stem, JARGON)
    before = detail(client, number)
    assert before["summary"]["title_reading"] is None
    assert before["doors"]["start"]["offered"], "an unread title holds nothing yet"

    opened = read_cold(
        client,
        machine_floor,
        "proj",
        number,
        "--title",
        "what a lane is and why the machine ended it are the board's words, not his",
        "--failed",
        "lane,machine ended",
    )
    brief = opened["argv"][-1]
    assert brief.startswith(f"A cold reading of #{number}'s title on Harbourmaster")
    assert "you must not go looking for one" in brief
    assert "could he place it against every other card without opening it?" in brief
    assert "- lane — " in brief, "the vocabulary is quoted from the file, whole"
    assert "docs/vocabulary.md" in brief
    assert f"#{number} — {JARGON}" in brief
    assert "--title passes" in brief
    said = capsys.readouterr().out
    assert "unplaceable" in said and "Start stays closed" in said

    # The machine fact on the face, with the reader's words and the words that failed.
    face = face_of(client, number)
    reading = face["title_reading"]
    assert reading["verdict"] == "unplaceable"
    assert reading["failed"] == ["lane", "machine ended"]
    assert reading["session_id"] == opened["session_id"]
    assert face["state"]["word"] == "title fails" and face["state"]["meaning"] == "broken"
    assert "could not place this card from its title" in face["state"]["detail"]
    assert "the words that failed: lane, machine ended" in face["state"]["detail"]
    assert "title fails" in face["claims"]
    after = detail(client, number)
    assert not after["doors"]["start"]["offered"]
    assert after["doors"]["start"]["why"] == face["state"]["detail"]
    assert after["doors"]["readiness"]["state"] == "title fails"
    refused = client.post(f"/api/projects/proj/cards/{number}/start", json={})
    assert refused.status_code == 409 and "could not place" in refused.json()["detail"]
    history = [h for h in after["history"] if h["kind"] == "title"]
    assert len(history) == 1 and opened["session_id"][:8] in history[0]["detail"]
    assert "lane, machine ended" in history[0]["detail"]
    assert store.title_readings("proj", number)[0].session_id == opened["session_id"]

    # A rewrite is never its own verification: the hold stays, and says the
    # title changed, until a reading of the new title passes.
    retitle(client, repo, "proj", repo / "docs" / "plans" / f"{stem}.md", JARGON, PLAIN)
    held = detail(client, number)
    assert held["card"]["title"] == PLAIN
    assert not held["doors"]["start"]["offered"]
    assert "the title has changed since" in held["doors"]["start"]["why"]
    assert face_of(client, number)["state"]["word"] == "title fails"

    read_cold(client, machine_floor, "proj", number, "--title", "passes")
    cleared = detail(client, number)
    assert cleared["summary"]["title_reading"]["verdict"] == "placeable"
    assert cleared["doors"]["start"]["offered"], cleared["doors"]["start"]["why"]
    face = face_of(client, number)
    assert face["state"]["word"] == "free to start" and "title fails" not in face["claims"]
    assert len(store.title_readings("proj", number)) == 2, "readings are a history"
    # A passing title is not read again while it stands.
    tick_log = len(machine_floor.state()["launch_log"])
    tick(client)
    assert number not in open_readings(client)
    assert len(machine_floor.state()["launch_log"]) in (tick_log, tick_log + 1)


def test_an_idea_born_with_lane_in_its_title_shows_the_mark_and_loses_it_on_the_next_reading(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    turn(client, on=True, lanes=1)
    stem = "2026-09-07-two-lanes-never-share-one-file"
    title = "Two lanes never share one file"
    path = write_suggestion(repo, stem, title=title, intent="Two sessions edit one file.")
    # An idea by its own word; the template's Found-by line would read as a defect.
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "\n\n**Found by:**", "\n\n**Kind:** idea\n**Found by:**", 1
        ),
        encoding="utf-8",
    )
    landed(repo, stem)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, title)
    assert face_of(client, number)["kind"] == "idea"

    read_cold(
        client,
        machine_floor,
        "proj",
        number,
        "--title",
        "a lane is the board's word",
        "--failed",
        "lane",
    )
    face = face_of(client, number)
    assert face["state"]["word"] == "title fails"
    assert face["title_reading"]["failed"] == ["lane"]
    assert "title fails" in face["claims"]
    capsys.readouterr()

    retitle(client, repo, "proj", path, title, "Two sessions never edit the same file")
    read_cold(client, machine_floor, "proj", number, "--title", "passes")
    face = face_of(client, number)
    assert face["title_reading"]["verdict"] == "placeable"
    assert face["state"]["word"] == "no plan yet" and "title fails" not in face["claims"]


def test_the_hold_is_the_boards_on_a_second_project_with_nothing_copied_into_it(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store, tmp_path: Path, capsys
):
    """Start is the one door every project's card goes through, so the
    refusal holds for a project that carries no ratchet and no vocabulary
    of its own: the second fixture project is a bare copy."""
    second = tmp_path / "second"
    shutil.copytree(repo, second, ignore=shutil.ignore_patterns(".git"))
    git(second, "init", "-q", "-b", "develop")
    landed(second, "founding")
    project = Project(slug="two", name="Second", path=str(second), registered_at=NOW)
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    client.app.state.loops.live.load()
    reconcile(client)
    assert not (second / "tests").exists() and not (second / "docs" / "vocabulary.md").exists()

    turn(client, on=True, lanes=1)
    stem = "2026-09-07-the-fold-lands-on-the-trunk"
    number = card_a_plan(client, second, "two", stem, "The fold lands on the trunk")
    read_cold(
        client,
        machine_floor,
        "two",
        number,
        "--title",
        "fold and trunk are the board's words",
        "--failed",
        "fold,trunk",
    )
    held = client.get(f"/api/projects/two/cards/{number}").json()
    assert not held["doors"]["start"]["offered"]
    assert held["doors"]["readiness"]["state"] == "title fails"
    assert face_of(client, number, "two")["state"]["word"] == "title fails"
    refused = client.post(f"/api/projects/two/cards/{number}/start", json={})
    assert refused.status_code == 409 and "could not place" in refused.json()["detail"]

    retitle(
        client,
        second,
        "two",
        second / "docs" / "plans" / f"{stem}.md",
        "The fold lands on the trunk",
        "Finished work lands where everyone builds on it",
    )
    read_cold(client, machine_floor, "two", number, "--title", "passes")
    opened = client.get(f"/api/projects/two/cards/{number}").json()
    assert opened["doors"]["start"]["offered"], opened["doors"]["start"]["why"]


def test_a_defects_reading_lands_both_halves_and_the_title_changes_no_routing(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    turn(client, on=True, lanes=1)
    stem = "2026-09-07-the-dial-takes-a-lane-twice"
    title = "The dial takes a lane twice"
    write_defect(repo, stem, title, f"**Fix:** now `{SOURCE}` already says the pontoon sleeps")
    landed(repo, stem)
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    number = number_of(client, title)

    opened = read_the_rail_until(client, machine_floor, number, slug="proj")
    brief = opened["argv"][-1]
    assert brief.startswith(f"A reading of #{number}'s mark on Harbourmaster")
    assert "The title, read cold." in brief and "- dial — " in brief
    # One reading, one command: a mark's result without the title is refused,
    # and a title without the mark's result is refused.
    with pytest.raises(SystemExit):
        main(["triage", "proj", str(number), "his", "the record selects neither"])
    capsys.readouterr()
    assert main(["triage", "proj", str(number), "--title", "passes"]) == 1
    assert "lands the mark's result and the title's verdict" in capsys.readouterr().err
    assert (
        main(
            [
                "triage",
                "proj",
                str(number),
                "his",
                "the record selects neither of the two shapes",
                "--title",
                "dial and lane are the board's words",
                "--failed",
                "dial,lane",
            ]
        )
        == 0
    )
    said = capsys.readouterr().out
    assert "routes as triaged his" in said and "title read as unplaceable" in said
    reconcile(client)
    face = face_of(client, number)
    assert face["routing"]["state"] == "triaged his", "the title reading changes no routing"
    assert face["title_reading"]["failed"] == ["dial", "lane"]
    assert face["state"]["word"] == "title fails", "broken before yours"
    assert "ruling yours" in face["claims"] and "title fails" in face["claims"]


def test_a_reading_of_a_plan_is_refused_a_marks_result(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    turn(client, on=True, lanes=1)
    stem = "2026-09-07-the-berth-map-is-printed-each-morning"
    number = card_a_plan(client, repo, "proj", stem, "The berth map is printed each morning")
    read_the_rail_until(client, machine_floor, number, slug="proj")
    assert main(["triage", "proj", str(number), "his", "no", "--title", "passes"]) == 1
    assert "has no mark to verify" in capsys.readouterr().err
    assert main(["triage", "proj", str(number), "--title", "passes", "--failed", "lane"]) == 1
    assert "A passing title names no failed words" in capsys.readouterr().err
    assert main(["triage", "proj", str(number), "--title", "passes"]) == 0


# ── item 4: the line under a defect's title ────────────────────────────


def test_a_defects_face_names_the_intent_it_breaks_and_never_a_path(client: TestClient):
    with_section = number_of(client, "The tide clock drifts a minute a day")
    face = face_of(client, with_section)
    assert face["essence"] == "The board on the pontoon says the same high water as the office."
    assert face["essence_source"] == "document"
    without = number_of(client, "The quay display polls the office all night")
    # This card's own SERVES row stands in front of its document on the
    # face; the document's essence is what a card with no such row shows.
    document = doors.detail(client, without)["document"]
    assert document["essence"] == (
        "The office costs nothing while nothing happens — but only because the quay display "
        "is not installed."
    )
    board = client.get("/api/projects/proj/board").json()
    faces = [c for column in board["columns"] for g in column["groups"] for c in g["cards"]]
    assert faces, "the board serves cards"
    for card in faces:
        essence = card["essence"] or ""
        assert "`" not in essence and "::" not in essence and "()" not in essence, (
            card["number"],
            essence,
        )


# ── item 2: the sweep keeps every card ─────────────────────────────────


def test_a_rename_that_changes_stem_and_title_keeps_the_card_its_number_and_its_history(
    client: TestClient, repo: Path
):
    """What the sweep does to every live document, rehearsed on the fixture
    before any real board is touched: `git mv` to the new stem, the title
    rewritten in place, the old title kept on a Formerly line under the
    head. The card keeps its number and its history and gains one retitled
    row; no second card is born and nothing is archived."""
    old = "The tide clock drifts a minute a day"
    new = "The pontoon board tells the same tide as the office"
    number = number_of(client, old)
    before = detail(client, number)
    born = [h for h in before["history"] if h["kind"] == "born"]
    assert len(born) == 1
    folder = repo / "docs" / "slice-suggestions"
    old_path = folder / "2026-09-04-the-tide-clock-drifts-a-minute-a-day.md"
    new_path = folder / "2026-09-04-the-pontoon-board-tells-the-same-tide-as-the-office.md"
    git(repo, "mv", str(old_path), str(new_path))
    text = new_path.read_text(encoding="utf-8")
    text = text.replace(
        f"# {old}\n\n", f"# {new}\n\n**Formerly:** {old} (retitled 2026-09-07, card #74)\n", 1
    )
    new_path.write_text(text, encoding="utf-8")
    # The board may read the tree before the commit lands: the staged rename is enough.
    client.app.state.loops.live.rescan("proj")
    reconcile(client)

    def numbers() -> set[int]:
        return {
            c["number"]
            for column in client.get("/api/projects/proj/board").json()["columns"]
            for g in column["groups"]
            for c in g["cards"]
        }

    live = numbers()
    assert number in live
    assert number_of(client, new) == number, "the card followed the rename"
    after = detail(client, number)
    assert after["summary"]["document_path"].endswith(new_path.name)
    assert [h for h in after["history"] if h["kind"] == "born"] == born
    # A rename that also retitles is one renamed row carrying the new title.
    renamed = [h for h in after["history"] if h["kind"] in ("renamed", "retitled")]
    assert renamed and new in renamed[-1]["detail"], after["history"]
    assert not any(h["kind"] == "archived" for h in after["history"])
    assert client.get("/api/projects/proj/board").json()["documents_without_card"] == []
    landed(repo, "retitled by the sweep")
    client.app.state.loops.live.rescan("proj")
    reconcile(client)
    assert number_of(client, new) == number and numbers() == live
    fields = {f["key"]: f["value"] for f in detail(client, number)["document"]["head_fields"]}
    assert fields["Formerly"].startswith(old)
