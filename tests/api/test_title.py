"""Every card title says what it is for at a glance, in plain words (card
#74), on the floor.

The owner ranks cards from their titles alone and could not read his own
board. What is held here, against the served fixture:

- item 4, the line under a defect's title names the intent it breaks and
  never where the code is: a defect with the section shows its first
  sentence, one without it shows its first path-free sentence.
"""

from fastapi.testclient import TestClient

from tests.api import test_doors as doors
from tests.api.test_dial import number_of

client = doors.client
repo = doors.repo
quick = doors.quick


def face_of(client: TestClient, number: int) -> dict:
    return doors.summary_of(client, number)


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
