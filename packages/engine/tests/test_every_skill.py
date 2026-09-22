"""A question counts for every skill it uses (ADR 0023) — step 8.

The skills are read from the question: its operations and its kind, each mapped to a registry skill by a
row. The rung's own skills only decide which of them leads, so `skill_codes[1]` stays the question's own
skill for every reader that already takes the first one.
"""

import json

import pytest

from engine import bank, db, labels
from engine.assess import skills as S

RULES = {
    "by_operation": {"+": "NUM.OPS.01", "-": "NUM.OPS.02", "×": "NUM.OPS.03"},
    "by_kind": {
        "missing_number": ["NUM.OPS.05"],
        "word_1step": ["NUM.PRB.02"],
        "word_2step": ["NUM.PRB.02"],
        "estimate_then_calc": ["NUM.PV.03"],
        "find_mistake": ["NUM.PRB.03"],
    },
    "by_symbol": {"₹": "NUM.MEAS.04"},
}


def used(fmt, spec, rung, stem=""):
    return S.used(fmt, spec, stem, rung, RULES)


def test_used_bare_addition_in_a_rung_that_names_both_operations_counts_for_addition_only():
    assert used("column_grid", {"a": 345, "b": 27, "op": "+"}, ["NUM.OPS.01", "NUM.OPS.02"]) == ["NUM.OPS.01"]
    assert used("bare_sum", {"a": 76, "b": 23, "op": "-"}, ["NUM.OPS.01", "NUM.OPS.02"]) == ["NUM.OPS.02"]


def test_used_budget_problem_counts_for_the_story_the_money_the_adding_and_the_subtracting():
    spec = {"budget": 8000, "a": 1231, "b": 797, "c": 548}
    stem = "The class has ₹8000 for a picnic. Bus tickets cost ₹1231 …"
    assert used("word_2step", spec, ["NUM.PRB.02", "NUM.MEAS.04"], stem) == [
        "NUM.PRB.02",
        "NUM.MEAS.04",
        "NUM.OPS.01",
        "NUM.OPS.02",
    ]


def test_used_the_rungs_own_skill_leads_so_the_first_label_is_still_the_questions_own():
    got = used("missing_number", {"text": "74 + □ = 96", "a": 74, "b": 22, "op": "+", "missing": "b"}, ["NUM.OPS.01"])
    assert got == ["NUM.OPS.01", "NUM.OPS.05"]


def test_used_a_story_names_money_only_when_it_is_about_money():
    rung = ["NUM.PRB.02", "NUM.MEAS.04"]
    shop = "Vihaan had ₹85. Vihaan bought a book for ₹19. How much money does Vihaan have left?"
    marbles = "Tara has 83 marbles. Vihaan gives Tara 91 more. How many marbles does Tara have now?"
    assert used("word_1step", {"a": 85, "b": 19, "op": "-"}, rung, shop) == ["NUM.PRB.02", "NUM.MEAS.04", "NUM.OPS.02"]
    assert used("word_1step", {"a": 83, "b": 91, "op": "+"}, rung, marbles) == ["NUM.PRB.02", "NUM.OPS.01"]


def test_used_train_story_takes_away_then_adds_and_mela_story_only_takes_away():
    rung = ["NUM.PRB.02", "NUM.MEAS.04"]
    train = "A train has 778 passengers. At the first station 47 get off and 18 get on. How many passengers are on the train now?"
    mela = "831 people are at a mela. 174 of them are adults and 168 are teachers. How many children are at the mela?"
    assert used("word_2step", {"a": 778, "b": 47, "c": 18}, rung, train) == ["NUM.PRB.02", "NUM.OPS.02", "NUM.OPS.01"]
    assert used("word_2step", {"a": 831, "b": 174, "c": 168}, rung, mela) == ["NUM.PRB.02", "NUM.OPS.02"]


def test_used_multi_addend_column_and_multiplication_name_their_operation():
    assert used("column_grid", {"addends": [5676, 3294, 1152], "op": "+", "layout": "column"}, ["NUM.OPS.01"]) == [
        "NUM.OPS.01"
    ]
    assert used("bare_sum", {"a": 33, "b": 7, "op": "×"}, ["NUM.OPS.03"]) == ["NUM.OPS.03"]


def test_used_a_missing_number_that_kept_only_its_text_is_read_from_the_text():
    assert used("missing_number", {"text": "22 − □ = 10"}, ["NUM.OPS.05"]) == ["NUM.OPS.05", "NUM.OPS.02"]


def test_used_a_kind_with_no_operation_of_its_own_uses_its_kinds_skills_alone():
    assert used("explain_claim", {"a": 417, "topic": "regrouping"}, ["NUM.PRB.03"]) == []
    rules = dict(RULES, by_kind=dict(RULES["by_kind"], explain_claim=["NUM.PRB.03"]))
    assert S.used("explain_claim", {"a": 417, "topic": "regrouping"}, "", ["NUM.PRB.03"], rules) == ["NUM.PRB.03"]


# ---------------------------------------------------------------- against the copy


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_rules_are_rows_in_config(conn):
    rules = labels.rules(conn)
    assert rules["by_operation"]["+"] == "NUM.OPS.01"
    assert "word_2step" in rules["by_kind"]
    registry = {r["code"] for r in conn.execute("select code from skill").fetchall()}
    named = set(rules["by_operation"].values()) | set(rules["by_symbol"].values())
    named |= {s for v in rules["by_kind"].values() for s in v}
    assert named <= registry, named - registry


def test_fill_labels_a_budget_problem_with_the_skills_it_uses(conn):
    _, items = bank.fill_native(conn, "WORD.BUDGET", "Hard", 3, dry_run=True)
    assert items and all(it.skills == ["NUM.PRB.02", "NUM.MEAS.04", "NUM.OPS.01", "NUM.OPS.02"] for it in items)


def test_fill_labels_3_digit_addition_with_addition_alone(conn):
    _, _, items = bank.fill(conn, "ADD.3D.REG", "Medium", 8, dry_run=True, offline=True)
    assert items and {tuple(it.skills) for it in items if it.fmt in ("column_grid", "bare_sum")} == {("NUM.OPS.01",)}


def test_relabel_leaves_no_question_carrying_a_skill_it_does_not_use(conn):
    changed = labels.relabel(conn)
    assert changed["skills"] >= 0
    assert labels.mislabelled(conn) == []
    assert labels.relabel(conn)["skills"] == 0  # a second pass finds nothing left to correct


def test_relabel_never_touches_a_question_from_an_old_paper(conn):
    before = conn.execute(
        "select id, skill_codes, spec from item where source = 'legacy' order by id limit 20"
    ).fetchall()
    labels.relabel(conn)
    after = {
        r["id"]: (r["skill_codes"], json.dumps(r["spec"], sort_keys=True))
        for r in conn.execute("select id, skill_codes, spec from item where id = any(%s)", ([b["id"] for b in before],))
    }
    assert all(after[b["id"]] == (b["skill_codes"], json.dumps(b["spec"], sort_keys=True)) for b in before)
