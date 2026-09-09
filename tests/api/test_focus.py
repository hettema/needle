"""You name what matters now, a colleague finds what holds it back, and the
board sorts every card by whether it moves that (card #87), on the served
board over the floor.

Item 1: the strip reads the fixture's focus as proposed, the verb and the
API return one object, and a ruling bound to one text over another is
proposed. Item 2: the Focus door opens a conversation with its own brief,
the rail lists it, and a second is refused while it lives. Item 3: a
proposed focus gets exactly one cold check of the other kind in a fresh
thread, a re-edited document is read again, and a call that ends without
an answer offers the ruling with the reason shown. Item 4: every open
card is read once, each in a thread of its own, only an edited card again,
and the verb refuses any other word and moves nothing. Item 5: an
acceptance moves exactly the ticked cards with the owner's name and one
batch, a put-back restores them, a hand move retires the put-back, an
unticked move is not re-proposed, and nothing starts or turns. Item 6: a
ruling reads the two measures as the baseline, and each recheck word
pauses the order in its sentence."""

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.cli import main
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, column_of, detail, reconcile, summary_of
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

FOCUS = "docs/FOCUS.md"
TODAY = datetime.now(UTC).date().isoformat()


def strip(client: TestClient) -> dict:
    response = client.get("/api/projects/proj/focus")
    assert response.status_code == 200, response.text
    return response.json()


def board(client: TestClient) -> dict:
    return client.get("/api/projects/proj/board").json()


def tick(client: TestClient) -> None:
    client.portal.call(client.app.state.focus.tick)


def rescan(client: TestClient) -> None:
    client.app.state.loops.live.rescan("proj")


def codex_asks(floor: Floor) -> list[dict]:
    """Every fresh reading the runtime asked of the fake Codex."""
    return [entry for entry in floor.state().get("codex_log", []) if entry.get("fresh")]


def check_answer(verdict: str = "stands", line: str = "the log shows it berth by berth") -> str:
    return json.dumps(
        {"verdict": verdict, "line": line, "how_known": "checked", "sources": ["office/log"]}
    )


def leverage_answer(
    leverage: str, likelihood: str | None, why: str = "it bills the reading"
) -> str:
    return json.dumps(
        {
            "leverage": leverage,
            "likelihood": likelihood,
            "why": why,
            "how_known": "checked",
            "sources": ["docs/FOCUS.md"],
        }
    )


def recheck_answer(outcome: str, words: str = "both moved") -> str:
    return json.dumps(
        {"outcome": outcome, "words": words, "how_known": "checked", "sources": ["office/log"]}
    )


def bring_to_proposed(client: TestClient, repo: Path, floor: Floor) -> dict:
    """The fixture's focus, checked by the other kind and ready for his click."""
    floor.script_codex({"then": "answer", "text": check_answer()})
    tick(client)
    tick(client)
    shown = strip(client)
    assert shown["state"] == "proposed" and shown["choose"]["offered"], shown
    return shown


def choose(client: TestClient, repo: Path, floor: Floor) -> dict:
    bring_to_proposed(client, repo, floor)
    chosen = client.post("/api/projects/proj/focus/choose")
    assert chosen.status_code == 200, chosen.text
    return strip(client)


def card_asks(floor: Floor) -> list[dict]:
    return [a for a in codex_asks(floor) if a["prompt"].startswith("A reading of #")]


def read_every_card(client: TestClient, floor: Floor, answers: dict[int, str] | None = None) -> int:
    """Tick until no card is left unread: every beat tends the reading it
    opened last and opens the next, so one tick is one card. Answers by card
    number; the rest read as protecting progress. Answers how many readings
    were opened."""
    answers = answers or {}
    seen: set[str] = {a["answer"] for a in card_asks(floor)}
    before = len(seen)
    for _ in range(80):
        floor.update(codex=[])
        floor.script_codex({"then": "answer", "text": leverage_answer("protects progress", None)})
        tick(client)
        new = [a for a in card_asks(floor) if a["answer"] not in seen]
        if not new:
            return len(seen) - before
        for ask in new:
            seen.add(ask["answer"])
            number = int(ask["prompt"].split("A reading of #")[1].split(" ")[0])
            if number in answers:
                Path(ask["answer"]).write_text(answers[number], encoding="utf-8")
    raise AssertionError("the loop never ran out of cards to read")


# ── item 1 ─────────────────────────────────────────────────────────────


def test_the_strip_reads_the_fixtures_focus_as_proposed_and_the_verb_and_the_api_agree(
    client: TestClient, capsys
):
    shown = strip(client)
    assert shown["state"] == "proposed"
    assert shown["sentence"] == "A focus is ready for your decision"
    assert shown["what_matters"] == "Every season berth is paid before the boat arrives"
    assert shown["document"]["doubts"] == []
    assert not shown["choose"]["offered"], "no second reading yet"
    assert board(client)["focus"]["document"]["fingerprint"] == shown["document"]["fingerprint"]
    assert board(client)["leverage"]["available"] is False
    assert board(client)["leverage"]["why"] == "the proposed focus waits for your decision"

    assert main(["strip", "proj", "--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["state"] == shown["state"] and printed["sentence"] == shown["sentence"]
    assert printed["document"]["fingerprint"] == shown["document"]["fingerprint"]
    assert main(["strip", "proj"]) == 0
    words = capsys.readouterr().out
    assert words.startswith("A focus is ready for your decision\n")
    assert "Leverage order unavailable: the proposed focus waits for your decision" in words
    assert main(["strip", "--unbound", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_a_document_with_a_missing_measure_is_proposed_with_a_doubt_naming_the_line(
    client: TestClient, repo: Path
):
    path = repo / FOCUS
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "**Recheck:** the diagnosis is read again against both measures — session "
            "harbourmaster by 2026-10-15",
            "**Recheck:** when the season ends",
        ),
        encoding="utf-8",
    )
    rescan(client)
    shown = strip(client)
    assert shown["state"] == "proposed"
    assert len(shown["document"]["doubts"]) == 1
    assert shown["document"]["doubts"][0].startswith(
        "**Recheck:** the WATCH row names no reader (url, file, command, session or owner)"
    )
    assert not shown["choose"]["offered"] and "**Recheck:**" in shown["choose"]["why"]
    refused = client.post("/api/projects/proj/focus/choose")
    assert refused.status_code == 409 and "cannot be chosen" in refused.json()["detail"]


# ── item 2 ─────────────────────────────────────────────────────────────


def test_the_focus_door_opens_a_conversation_the_rail_lists_and_refuses_a_second_while_it_lives(
    client: TestClient, machine_floor: Floor, repo: Path
):
    (repo / FOCUS).unlink()
    rescan(client)
    assert strip(client)["state"] == "no focus"
    assert strip(client)["sentence"] == "No focus chosen"
    opened = client.post(
        "/api/projects/proj/focus", json={"text": "more berths paid before arrival"}
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["said"].startswith("Talking in org.omarchy.board-focus-proj, alpha")
    spawned = machine_floor.state()["spawned"][-1]
    assert spawned["app_id"] == "org.omarchy.board-focus-proj"
    command = spawned["command"][-1]
    assert command.startswith(f"cd {repo} &&"), "the conversation runs in the project's checkout"
    assert "The focus of Harbourmaster" in command and "more berths paid before arrival" in command
    assert "sharpen what matters now into one sentence with a number" in command
    assert "write docs/FOCUS.md with exactly this head" in command
    assert "the click is his, never yours" in command
    assert "No focus document exists yet." in command
    session_id = command.split("--session-id ")[1].split()[0]
    short = session_id[:8]
    machine_floor.write_job("alpha", short, session_id=session_id, cwd=str(repo), name="focus")
    machine_floor.write_process("alpha", session_id, os.getpid(), cwd=str(repo), kind="interactive")
    reconcile(client)
    shown = board(client)
    talk = shown["conversations"][0]
    assert talk["what"] == "Focus" and talk["kind"] == "board-focus" and talk["short_id"] == short
    assert shown["focus"]["state"] == "talking"
    assert shown["focus"]["sentence"] == "Working out what holds this back"
    assert shown["focus"]["conversation"]["short_id"] == short
    again = client.post("/api/projects/proj/focus", json={"text": ""})
    assert again.status_code == 409
    assert f"already open for this project: {short} on alpha" in again.json()["detail"]
    moves = client.post("/api/projects/proj/focus/propose")
    assert moves.status_code == 409 and "already open" in moves.json()["detail"]
    assert all(
        c["lane_state"] == "none"
        for col in shown["columns"]
        for g in col["groups"]
        for c in g["cards"]
    ), "a conversation is never hands on a tree"

    # The document lands: the strip moves to proposed while the conversation lives.
    shutil.copy(FIXTURE_FOCUS, repo / FOCUS)
    rescan(client)
    shown = strip(client)
    assert shown["state"] == "proposed" and shown["conversation"]["short_id"] == short

    # The conversation ends before a document is written: the strip says so.
    (repo / FOCUS).unlink()
    rescan(client)
    machine_floor.write_job(
        "alpha", short, session_id=session_id, cwd=str(repo), name="focus", state="done"
    )
    (machine_floor.config_dir("alpha") / "sessions").mkdir(exist_ok=True)
    for file in (machine_floor.config_dir("alpha") / "sessions").glob("*.json"):
        file.unlink()
    reconcile(client)
    shown = strip(client)
    assert shown["state"] == "ended without"
    assert shown["sentence"] == "A conversation ended before a focus was written"
    assert shown["talk"]["offered"]


FIXTURE_FOCUS = Path(__file__).resolve().parents[1] / "fixtures" / "harbourmaster" / FOCUS


def test_a_suggestion_written_from_the_focus_conversation_is_a_card_with_its_found_by_line(
    client: TestClient, repo: Path
):
    (
        repo / "docs" / "slice-suggestions" / "2026-09-09-the-office-reads-the-meter-itself.md"
    ).write_text(
        "# The office reads the meter itself\n\n"
        "**Kind:** idea\n"
        f"**Found by:** the owner, from the board's Focus door on {TODAY} (conversation 9a3c1e7f)\n"
        "**Cost:** two days · **Time:** a week · **Likelihood:** high\n\n"
        "## The intent it breaks\n\n"
        "Every season berth is paid before the boat arrives, and the office is blind to what it "
        "has to bill.\n",
        encoding="utf-8",
    )
    rescan(client)
    shown = board(client)
    card = next(
        c
        for col in shown["columns"]
        for g in col["groups"]
        for c in g["cards"]
        if c["title"] == "The office reads the meter itself"
    )
    assert card["place"]["column"] == "Backlog" and card["kind"] == "idea"
    assert card["essence"].startswith("Every season berth is paid before the boat arrives")


# ── item 3 ─────────────────────────────────────────────────────────────


def test_a_proposed_focus_gets_one_cold_check_in_a_fresh_thread_and_a_re_edited_one_is_read_again(
    client: TestClient, machine_floor: Floor, repo: Path
):
    machine_floor.script_codex(
        {
            "then": "answer",
            "text": check_answer("does not stand", "the rival is not separated by the log"),
        }
    )
    tick(client)
    asks = codex_asks(machine_floor)
    assert len(asks) == 1, "exactly one reading per proposal"
    argv = asks[0]["argv"]
    assert "resume" not in argv, "a fresh thread, never the slot's warm one"
    assert argv[argv.index("-s") + 1] == "read-only"
    assert argv[argv.index("-C") + 1] == str(repo)
    assert "--output-schema" in argv and asks[0]["schema"].endswith(".schema.json")
    schema = json.loads(Path(asks[0]["schema"]).read_text(encoding="utf-8"))
    assert set(schema["properties"]) == {"verdict", "line", "how_known", "sources"}
    brief = asks[0]["prompt"]
    assert brief.startswith("A cold reading of a proposed focus for Harbourmaster")
    assert "you have no share of that conversation and must not go looking for one" in brief
    assert "--- the proposed focus (docs/FOCUS.md) ---" in brief
    assert "every-metered-kilowatt-is-billed.md" in brief, (
        "the sources it cites, as the board read them"
    )
    assert "does the diagnosis stand on the evidence it cites?" in brief
    shown = strip(client)
    assert shown["checking"] is True and not shown["choose"]["offered"]
    assert "is checking the diagnosis" in shown["choose"]["why"]

    tick(client)
    assert len(codex_asks(machine_floor)) == 1, "landed, not opened again"
    shown = strip(client)
    assert shown["check"]["verdict"] == "does not stand"
    assert shown["check"]["line"] == "the rival is not separated by the log"
    assert shown["check"]["fingerprint"] == shown["document"]["fingerprint"]
    assert shown["choose"]["offered"], (
        "disagreement shows as disagreement and never blocks his click"
    )
    assert "says it does not stand: the rival is not separated by the log" in shown["choose"]["why"]
    assert shown["talk"]["offered"], "Keep discussing"

    # The document is edited after the reading: read again, exactly once more.
    path = repo / FOCUS
    path.write_text(
        path.read_text(encoding="utf-8") + "\nA line added after the reading.\n", encoding="utf-8"
    )
    rescan(client)
    shown = strip(client)
    assert shown["check"] is None and not shown["choose"]["offered"]
    machine_floor.script_codex({"then": "answer", "text": check_answer()})
    tick(client)
    tick(client)
    assert len(codex_asks(machine_floor)) == 2
    shown = strip(client)
    assert shown["check"]["verdict"] == "stands" and shown["choose"]["offered"]


def test_a_check_that_ends_without_an_answer_offers_the_ruling_with_the_reason_shown(
    client: TestClient, machine_floor: Floor, repo: Path
):
    machine_floor.script_codex({"then": "silent"}, {"then": "fail", "stderr": "error: no model"})
    tick(client)
    tick(client)
    shown = strip(client)
    assert shown["check"] is None and shown["check_note"] is not None
    assert shown["choose"]["offered"]
    assert "No second reading landed:" in shown["choose"]["why"]
    assert "ended" in shown["check_note"] and "without an answer" in shown["check_note"]
    tick(client)
    assert len(codex_asks(machine_floor)) == 2, "two attempts and then the door opens with the note"
    ratchet = client.app.state.loops.live.store.focus_calls("proj")
    assert [c.landed for c in ratchet] == [False, False]


# ── item 4 ─────────────────────────────────────────────────────────────


def test_choosing_binds_the_ruling_reads_the_baseline_and_an_edit_after_the_click_is_a_new_proposal(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    shown = choose(client, repo, machine_floor)
    assert shown["state"] == "chosen"
    assert shown["ruling"]["fingerprint"] == shown["document"]["fingerprint"]
    assert shown["ruling"]["what_matters"] == "Every season berth is paid before the boat arrives"
    assert {m["side"]: m["baseline"] for m in shown["measures"]} == {
        "outcome": True,
        "bottleneck": True,
    }
    assert all(m["delivered"] is False for m in shown["measures"]), (
        "the fixture's logs do not exist yet"
    )
    assert shown["sentence"].startswith("Focus chosen · 0 of ")
    assert shown["coverage"]["unread"] == shown["coverage"]["total"] > 0
    assert shown["coverage"]["line"] == "Nothing queued is evidenced to remove this limit"
    assert shown["propose"]["offered"] and not shown["choose"]["offered"]
    assert board(client)["leverage"]["available"] is True

    path = repo / FOCUS
    path.write_text(
        path.read_text(encoding="utf-8") + "\nEdited after the click.\n", encoding="utf-8"
    )
    rescan(client)
    shown = strip(client)
    assert shown["state"] == "proposed", (
        "an edit after the click is a new proposal, never an inherited ruling"
    )
    assert shown["ruling"]["fingerprint"] != shown["document"]["fingerprint"]
    assert board(client)["leverage"]["available"] is False
    assert main(["strip", "--unbound", "--count"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_every_open_card_is_read_once_in_a_thread_of_its_own_and_only_an_edited_card_again(
    client: TestClient, machine_floor: Floor, repo: Path
):
    choose(client, repo, machine_floor)
    shown = board(client)
    open_cards = [
        c["number"]
        for col in shown["columns"]
        for g in col["groups"]
        for c in g["cards"]
        if col["definition"]["column"] not in ("Executed", "Done")
        and c["document_state"] in ("plan", "suggestion")
    ]
    opened = read_every_card(
        client, machine_floor, {CARD: leverage_answer("helps remove this limit", "high")}
    )
    asks = card_asks(machine_floor)
    assert opened == len(open_cards) == len(asks)
    assert sorted({a["id"] for a in asks}) == sorted(a["id"] for a in asks), (
        "each in a thread of its own"
    )
    assert all("resume" not in a["argv"] for a in asks)
    assert all(a["prompt"].startswith("A reading of #") for a in asks)
    assert "never its aspiration" in asks[0]["prompt"]
    shown = strip(client)
    assert shown["coverage"]["assessed"] == shown["coverage"]["total"] == len(open_cards)
    assert shown["coverage"]["unread"] == 0 and shown["coverage"]["queued_helping"] == 1
    assert shown["coverage"]["line"] == "1 queued card helps remove this limit"
    card = summary_of(client, CARD)
    assert (
        card["leverage"]["state"] == "read"
        and card["leverage"]["leverage"] == "helps remove this limit"
    )
    assert card["leverage"]["likelihood"] == "high"
    assert card["leverage"]["sentence"].startswith(
        "Nothing for you: it helps remove this limit (high likelihood)."
    )
    history = detail(client, CARD)["history"]
    assert any(
        h["kind"] == "leverage" and "helps remove this limit (high)" in h["detail"] for h in history
    )

    # One plan edited: it, and only it, is read again.
    plan = next(repo.glob("docs/plans/*metered*"))
    plan.write_text(plan.read_text(encoding="utf-8") + "\nOne more sentence.\n", encoding="utf-8")
    rescan(client)
    assert summary_of(client, CARD)["leverage"]["state"] == "stale"
    assert strip(client)["coverage"]["stale"] == 1
    again = read_every_card(
        client, machine_floor, {CARD: leverage_answer("helps remove this limit", "medium")}
    )
    assert again == 1
    assert summary_of(client, CARD)["leverage"]["likelihood"] == "medium"

    # The focus itself renamed: every reading is stale.
    path = repo / FOCUS
    path.write_text(
        path.read_text(encoding="utf-8").replace("2026-10-15", "2026-10-16"), encoding="utf-8"
    )
    rescan(client)
    assert strip(client)["state"] == "proposed"
    choose(client, repo, machine_floor)
    shown = strip(client)
    assert shown["coverage"]["stale"] == shown["coverage"]["total"]


def test_the_verb_refuses_any_other_word_and_a_reading_moves_nothing(
    client: TestClient, machine_floor: Floor, repo: Path, capsys
):
    with pytest.raises(SystemExit):
        main(["leverage", "proj", str(CARD), "moves the needle", "why"])
    with pytest.raises(SystemExit):
        main(
            [
                "leverage",
                "proj",
                str(CARD),
                "helps remove this limit",
                "why",
                "--likelihood",
                "certain",
            ]
        )
    assert main(["leverage", "proj", str(CARD), "helps remove this limit", "why"]) == 1
    assert "no chosen focus" in capsys.readouterr().err
    choose(client, repo, machine_floor)
    assert main(["leverage", "proj", str(CARD), "helps remove this limit", "why"]) == 1
    assert "--likelihood high, medium or low" in capsys.readouterr().err
    assert (
        main(["leverage", "proj", str(CARD), "protects progress", "why", "--likelihood", "high"])
        == 1
    )
    assert "goes only with" in capsys.readouterr().err
    before = summary_of(client, CARD)["place"]
    assert (
        main(
            [
                "leverage",
                "proj",
                str(CARD),
                "helps remove this limit",
                "it bills the reading",
                "--likelihood",
                "low",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.startswith(f"#{CARD} read as helps remove this limit (low)")
    client.app.state.loops.live.rescan("proj")
    assert summary_of(client, CARD)["place"] == before, "a reading judges; it never moves a card"
    assert summary_of(client, CARD)["leverage"]["likelihood"] == "low"


# ── item 5 ─────────────────────────────────────────────────────────────


def arranged_up_next(client: TestClient) -> list[int]:
    column = next(c for c in board(client)["leverage"]["columns"] if c["column"] == "Up next")
    return [n for g in column["groups"] for n in g["numbers"]]


def test_an_acceptance_moves_the_ticked_cards_with_his_name_and_one_batch_and_a_put_back_restores(
    client: TestClient, machine_floor: Floor, repo: Path
):
    choose(client, repo, machine_floor)
    planned = [
        c["number"]
        for col in board(client)["columns"]
        if col["definition"]["column"] == "Planned"
        for g in col["groups"]
        for c in g["cards"]
    ]
    up_next = [
        c["number"]
        for col in board(client)["columns"]
        if col["definition"]["column"] == "Up next"
        for g in col["groups"]
        for c in g["cards"]
    ]
    first_planned, second_planned = planned[0], planned[1]
    parked = up_next[-1]
    read_every_card(
        client,
        machine_floor,
        {
            first_planned: leverage_answer("helps remove this limit", "high"),
            second_planned: leverage_answer("helps remove this limit", "low"),
            parked: leverage_answer("does not address this limit", None),
        },
    )
    shown = board(client)
    moves = {m["number"]: m for m in shown["leverage"]["moves"]}
    assert set(moves) == {first_planned, second_planned, parked}
    assert (
        moves[first_planned]["to_place"]["column"] == "Up next"
        and moves[first_planned]["to_place"]["position"] == 0
    )
    assert moves[second_planned]["to_place"]["column"] == "Up next"
    assert moves[parked]["to_place"]["column"] == "Not now" and moves[parked]["wake"].startswith(
        "WATCH: wake when"
    )
    assert shown["focus"]["moves_proposed"] == 3
    assert arranged_up_next(client)[0] == first_planned
    launches = len(machine_floor.state()["launch_log"])
    dial = shown["dial"]

    accepted = client.post(
        "/api/projects/proj/leverage/accept", json={"numbers": [first_planned, parked]}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["said"].startswith("Order accepted (batch 1): 2 of 2 moves made")
    assert "1 left unticked" in accepted.json()["said"]
    assert (
        column_of(client, first_planned) == "Up next"
        and summary_of(client, first_planned)["place"]["position"] == 0
    )
    assert column_of(client, parked) == "Not now"
    assert column_of(client, second_planned) == "Planned", "the unticked move was not made"
    moved = next(h for h in detail(client, first_planned)["history"] if h["kind"] == "moved")
    assert moved["actor"] == "owner"
    assert "accepted the leverage order (batch 1, focus " in moved["detail"]
    assert "helps remove this limit, high likelihood" in moved["detail"]
    parked_move = next(h for h in detail(client, parked)["history"] if h["kind"] == "moved")
    assert "wakes when WATCH: wake when" in parked_move["detail"]
    shown = board(client)
    assert shown["focus"]["accepted"]["id"] == 1 and len(shown["focus"]["accepted"]["moves"]) == 2
    assert shown["focus"]["put_back_offered"] is True
    assert (
        "Order accepted" in shown["focus"]["sentence"]
        and "Put it back" in shown["focus"]["sentence"]
    )
    assert [m["number"] for m in shown["leverage"]["moves"]] == [], (
        "the unticked move is not proposed again"
    )
    assert len(machine_floor.state()["launch_log"]) == launches, "accepting never starts a lane"
    assert shown["dial"] == dial, "accepting never turns the dial"
    assert summary_of(client, first_planned)["gate"] == "high", "accepting never changes a gate"

    put_back = client.post("/api/projects/proj/leverage/put-back")
    assert put_back.status_code == 200, put_back.text
    assert put_back.json()["said"].startswith("Put back (batch 1): 2 of 2 restored")
    assert column_of(client, first_planned) == "Planned" and column_of(client, parked) == "Up next"
    assert summary_of(client, parked)["place"]["position"] == len(up_next) - 1
    restored = next(h for h in detail(client, parked)["history"] if h["kind"] == "moved")
    assert (
        restored["actor"] == "owner"
        and "put back where it was before the leverage order (batch 1)" in restored["detail"]
    )
    shown = board(client)
    assert shown["focus"]["accepted"] is None and shown["focus"]["put_back_offered"] is False
    assert {m["number"] for m in shown["leverage"]["moves"]} == {first_planned, parked}, (
        "the two moves are proposed again; the declined one stays declined"
    )
    again = client.post("/api/projects/proj/leverage/put-back")
    assert again.status_code == 409


def test_a_hand_move_after_the_acceptance_retires_the_put_back(
    client: TestClient, machine_floor: Floor, repo: Path
):
    choose(client, repo, machine_floor)
    planned = [
        c["number"]
        for col in board(client)["columns"]
        if col["definition"]["column"] == "Planned"
        for g in col["groups"]
        for c in g["cards"]
    ]
    read_every_card(
        client, machine_floor, {planned[0]: leverage_answer("helps remove this limit", "high")}
    )
    accepted = client.post("/api/projects/proj/leverage/accept", json={"numbers": [planned[0]]})
    assert accepted.status_code == 200, accepted.text
    assert board(client)["focus"]["put_back_offered"] is True
    by_hand = client.post(
        f"/api/projects/proj/cards/{CARD}/move",
        json={"to": {"column": "Up next", "group": None, "position": 3}},
    )
    assert by_hand.status_code == 200, by_hand.text
    shown = board(client)
    assert shown["focus"]["put_back_offered"] is False and shown["focus"]["accepted"] is None
    refused = client.post("/api/projects/proj/leverage/put-back")
    assert refused.status_code == 409 and "moved a card by hand" in refused.json()["detail"]
    unknown = client.post("/api/projects/proj/leverage/accept", json={"numbers": [999]})
    assert unknown.status_code == 409 and "Not proposed" in unknown.json()["detail"]


def test_the_start_click_carries_the_lens_and_the_class_on_the_history(
    client: TestClient, machine_floor: Floor, repo: Path
):
    choose(client, repo, machine_floor)
    read_every_card(
        client, machine_floor, {CARD: leverage_answer("helps remove this limit", "high")}
    )
    machine_floor.script_launches({"then": "alive"})
    started = client.post(f"/api/projects/proj/cards/{CARD}/start", json={"lens": "Leverage"})
    assert started.status_code == 200, started.text
    row = next(h for h in detail(client, CARD)["history"] if h["kind"] == "started")
    assert "; under the Leverage lens, read as helps remove this limit (high)" in row["detail"]


# ── item 6 ─────────────────────────────────────────────────────────────


def with_recheck_on(repo: Path, day: str, was: str = "2026-10-15") -> None:
    path = repo / FOCUS
    text = path.read_text(encoding="utf-8")
    assert f"by {was}" in text
    path.write_text(text.replace(f"by {was}", f"by {day}"), encoding="utf-8")


@pytest.mark.parametrize(
    ("outcome", "opens"),
    [
        (
            "diagnosis challenged",
            "The bottleneck measure improved, but Every season berth is paid before the boat "
            "arrives did not. We are checking the diagnosis.",
        ),
        (
            "work not linked",
            "The work shipped, but invoices sent within a day of the reading has not improved. "
            "We are checking whether the work changed the limiting cause.",
        ),
        ("expired", "The evidence for this diagnosis expired on"),
    ],
)
def test_each_recheck_outcome_shows_its_sentence_and_pauses_the_order(
    client: TestClient, machine_floor: Floor, repo: Path, outcome: str, opens: str, capsys
):
    with_recheck_on(repo, TODAY)
    rescan(client)
    choose(client, repo, machine_floor)
    shown = strip(client)
    assert shown["state"] == "chosen" and shown["sentence"] == "Time to check this focus again"
    assert shown["recheck_due"] == TODAY
    machine_floor.script_codex(
        {"then": "answer", "text": recheck_answer(outcome, "the numbers say so")}
    )
    checks = len(codex_asks(machine_floor))
    tick(client)
    asks = codex_asks(machine_floor)
    assert len(asks) == checks + 1 and asks[-1]["prompt"].startswith(
        "The scheduled recheck of Harbourmaster"
    )
    assert "read since the ruling (baseline first)" in asks[-1]["prompt"]
    assert "Never say which priority to choose instead" in asks[-1]["prompt"]
    tick(client)
    shown = strip(client)
    assert (
        shown["recheck"]["outcome"] == outcome and shown["recheck"]["words"] == "the numbers say so"
    )
    assert shown["state"] == "paused" and shown["sentence"].startswith(opens)
    assert shown["paused"] == shown["sentence"]
    leverage = board(client)["leverage"]
    assert leverage["available"] is False and leverage["why"] == shown["sentence"]
    assert leverage["moves"] == [], "a paused order never orders"
    assert main(["strip", "proj"]) == 0
    assert capsys.readouterr().out.startswith(opens[:40])


def test_a_recheck_that_holds_keeps_the_order_and_a_missed_recheck_expires_by_itself(
    client: TestClient, machine_floor: Floor, repo: Path
):
    with_recheck_on(repo, TODAY)
    rescan(client)
    choose(client, repo, machine_floor)
    machine_floor.script_codex({"then": "answer", "text": recheck_answer("holds")})
    tick(client)
    tick(client)
    shown = strip(client)
    assert shown["state"] == "chosen" and shown["recheck"]["outcome"] == "holds"
    assert board(client)["leverage"]["available"] is True

    # A recheck date already passed with no reading since: expired by itself.
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    with_recheck_on(repo, yesterday, was=TODAY)
    rescan(client)
    machine_floor.script_codex({"then": "answer", "text": check_answer()})
    tick(client)
    tick(client)
    chosen = client.post("/api/projects/proj/focus/choose")
    assert chosen.status_code == 200, chosen.text
    shown = strip(client)
    assert shown["state"] == "paused"
    assert shown["sentence"].startswith(f"The evidence for this diagnosis expired on {yesterday}")
    assert board(client)["leverage"]["available"] is False
