"""The rule is asked of `claude-acct best` and never re-implemented (plan 02, item 2)."""

from domain.slot import Make, Rung
from runtime import rule
from tests.floor import Floor


def test_where_asks_the_one_rule_and_reads_its_answer(machine_floor: Floor):
    machine_floor.answer_best("beta", None, "Fable headroom on beta (12% used)")

    answer = rule.where(
        "alpha",
        [Rung(slot="alpha", model="fable"), Rung(slot="gamma", model=None)],
        cached=True,
    )

    assert answer.placement is not None
    assert answer.placement.slot == "beta" and answer.placement.model is None
    assert answer.placement.make is Make.CLAUDE and answer.placement.tier is None
    assert answer.placement.config_dir == str(machine_floor.config_dir("beta"))
    assert answer.placement.why == "Fable headroom on beta (12% used)"
    assert machine_floor.state()["best_calls"] == [
        ["best", "--json", "--cached", "--from", "alpha", "--tried", "alpha:fable,gamma"]
    ]


def test_a_live_ask_leaves_the_cache_out(machine_floor: Floor):
    rule.where(None, [], cached=False)

    assert machine_floor.state()["best_calls"] == [["best", "--json"]]


def test_opus_is_the_rules_word_for_no_fable_anywhere(machine_floor: Floor):
    machine_floor.answer_best(
        "alpha", "opus", "no Fable left anywhere; alpha has the most weekly headroom"
    )

    answer = rule.where(None, [], cached=True)

    assert answer.placement is not None and answer.placement.model == "opus"


def test_nowhere_to_run_carries_the_rules_words(machine_floor: Floor):
    machine_floor.refuse_best("no account with headroom")

    answer = rule.where(None, [], cached=True)

    assert answer.placement is None and "no account with headroom" in answer.reason


def test_a_slot_the_floor_does_not_declare_is_refused_by_name(machine_floor: Floor):
    machine_floor.answer_best("gamma")

    answer = rule.where(None, [], cached=True)

    assert answer.placement is None and "'gamma'" in answer.reason


def test_a_missing_rule_is_named(machine_floor: Floor, monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")

    answer = rule.where(None, [], cached=True)

    assert answer.placement is None and "claude-acct" in answer.reason


def test_a_make_this_runtime_cannot_launch_is_refused_by_the_word_the_rule_used(
    machine_floor: Floor
):
    """A make with no launcher here is named, not run as the make we happen
    to know. Adding one is a launcher and a row of the machine's data; until
    there is a launcher the refusal says which word it could not honour
    (card #63, item 4)."""
    machine_floor.answer_best("mistral-slot", "large", "the only headroom", make="mistral")

    answer = rule.where(None, [], cached=False)

    assert answer.placement is None
    assert "'mistral'" in answer.reason and "no launcher" in answer.reason
    assert "claude" in answer.reason and "codex" in answer.reason


def test_the_rule_may_name_a_make_a_model_and_the_owners_dated_tier_ruling(
    machine_floor: Floor
):
    machine_floor.answer_best(
        "codex",
        "gpt-6-astra",
        "no Fable left anywhere",
        make="codex",
        tier=1,
        tier_ruled_on="2026-09-05",
        tier_why="the tier is quality, not allowance",
    )

    answer = rule.where(None, [], cached=False)

    assert answer.placement is not None
    placement = answer.placement
    assert placement.make is Make.CODEX and placement.model == "gpt-6-astra"
    assert placement.tier is not None
    assert placement.tier.rank == 1
    assert placement.tier.ruled_on.isoformat() == "2026-09-05"
    assert placement.tier.why == "the tier is quality, not allowance"


def test_a_tier_the_rule_only_half_named_is_no_tier(machine_floor: Floor):
    """A rank with no date is a ruling nobody can look up, so the board shows
    the rung without one rather than a tier it cannot date."""
    machine_floor.answer_best("alpha", "fable", "headroom", tier=1)

    answer = rule.where(None, [], cached=False)

    assert answer.placement is not None and answer.placement.tier is None


def test_a_model_that_is_not_a_name_is_refused(machine_floor: Floor):
    machine_floor.update(best={"slot": "alpha", "model": 7, "why": "headroom"})

    answer = rule.where(None, [], cached=False)

    assert answer.placement is None and "not a model's name" in answer.reason
