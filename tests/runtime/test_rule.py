"""The rule is asked of `claude-acct best` and never re-implemented (plan 02, item 2)."""

from domain.slot import Model, Rung
from runtime import rule
from tests.floor import Floor


def test_where_asks_the_one_rule_and_reads_its_answer(machine_floor: Floor):
    machine_floor.answer_best("beta", None, "Fable headroom on beta (12% used)")

    answer = rule.where(
        "alpha",
        [Rung(slot="alpha", model=Model.FABLE), Rung(slot="gamma", model=None)],
        cached=True,
    )

    assert answer.placement is not None
    assert answer.placement.slot == "beta" and answer.placement.model == Model.FABLE
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

    assert answer.placement is not None and answer.placement.model == Model.OPUS


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
