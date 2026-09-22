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
    got = used(
        "missing_number", {"text": "74 + □ = 96", "a": 74, "b": 22, "op": "+", "missing": "b"}, ["NUM.OPS.01"]
    )
    assert got == ["NUM.OPS.01", "NUM.OPS.05"]


def test_used_a_story_names_money_only_when_it_is_about_money():
    rung = ["NUM.PRB.02", "NUM.MEAS.04"]
    shop = "Vihaan had ₹85. Vihaan bought a book for ₹19. How much money does Vihaan have left?"
    marbles = "Tara has 83 marbles. Vihaan gives Tara 91 more. How many marbles does Tara have now?"
    assert used("word_1step", {"a": 85, "b": 19, "op": "-"}, rung, shop) == [
        "NUM.PRB.02",
        "NUM.MEAS.04",
        "NUM.OPS.02",
    ]
    assert used("word_1step", {"a": 83, "b": 91, "op": "+"}, rung, marbles) == ["NUM.PRB.02", "NUM.OPS.01"]


def test_used_train_story_takes_away_then_adds_and_mela_story_only_takes_away():
    rung = ["NUM.PRB.02", "NUM.MEAS.04"]
    train = "A train has 778 passengers. At the first station 47 get off and 18 get on. How many passengers are on the train now?"
    mela = "831 people are at a mela. 174 of them are adults and 168 are teachers. How many children are at the mela?"
    assert used("word_2step", {"a": 778, "b": 47, "c": 18}, rung, train) == [
        "NUM.PRB.02",
        "NUM.OPS.02",
        "NUM.OPS.01",
    ]
    assert used("word_2step", {"a": 831, "b": 174, "c": 168}, rung, mela) == ["NUM.PRB.02", "NUM.OPS.02"]


def test_used_multi_addend_column_and_multiplication_name_their_operation():
    assert used(
        "column_grid", {"addends": [5676, 3294, 1152], "op": "+", "layout": "column"}, ["NUM.OPS.01"]
    ) == ["NUM.OPS.01"]
    assert used("bare_sum", {"a": 33, "b": 7, "op": "×"}, ["NUM.OPS.03"]) == ["NUM.OPS.03"]


def test_used_a_missing_number_that_kept_only_its_text_is_read_from_the_text():
    assert used("missing_number", {"text": "22 − □ = 10"}, ["NUM.OPS.05"]) == ["NUM.OPS.05", "NUM.OPS.02"]


def test_used_a_kind_with_no_operation_of_its_own_uses_its_kinds_skills_alone():
    assert used("explain_claim", {"a": 417, "topic": "regrouping"}, ["NUM.PRB.03"]) == []
    rules = dict(RULES, by_kind=dict(RULES["by_kind"], explain_claim=["NUM.PRB.03"]))
    assert S.used("explain_claim", {"a": 417, "topic": "regrouping"}, "", ["NUM.PRB.03"], rules) == [
        "NUM.PRB.03"
    ]


# ---------------------------------------------------------------- 8b: the skill a mistake charges

VOCAB = {
    ("M_SUM_ONLY", "any"): ("row", "NUM.OPS.02"),
    ("M_ONE_STEP_ONLY", "any"): ("row", "NUM.PRB.02"),
    ("M_WRONG_OP", "+"): ("operation", None),
    ("M_WRONG_OP", "-"): ("operation", None),
    ("M_NOCARRY", "+"): ("operation", None),
    ("M_SMALL_FROM_LARGE", "-"): ("operation", None),
    ("M_ZERO_DROPPED", "any"): ("operation", None),
    ("M_EQUALS_MEANS_ANSWER", "any"): ("row", "NUM.OPS.05"),
    ("M_COMPARE_REVERSED", "any"): ("row", "NUM.PV.02"),
}
CHARGING = dict(
    RULES,
    charges_by_kind={"word_1step": {"M_WRONG_OP": "NUM.PRB.02"}, "word_2step": {"M_WRONG_OP": "NUM.PRB.02"}},
)


def charges(fmt, spec, rung, codes, stem=""):
    return S.charges(fmt, spec, stem, used(fmt, spec, rung, stem), codes, VOCAB, CHARGING)


def test_charges_budget_mistakes_charge_the_step_that_broke():
    spec = {"budget": 8000, "a": 1231, "b": 797, "c": 548}
    got = charges(
        "word_2step",
        spec,
        ["NUM.PRB.02", "NUM.MEAS.04"],
        ["M_SUM_ONLY", "M_ONE_STEP_ONLY", "M_WRONG_OP"],
        "₹",
    )
    assert got == {"M_SUM_ONLY": "NUM.OPS.02", "M_ONE_STEP_ONLY": "NUM.PRB.02", "M_WRONG_OP": "NUM.PRB.02"}


def test_charges_every_mistake_on_a_bare_subtraction_charges_subtraction():
    got = charges(
        "column_grid",
        {"a": 402, "b": 185, "op": "-"},
        ["NUM.OPS.02"],
        ["M_SMALL_FROM_LARGE", "M_ZERO_DROPPED"],
    )
    assert got == {"M_SMALL_FROM_LARGE": "NUM.OPS.02", "M_ZERO_DROPPED": "NUM.OPS.02"}


def test_charges_choosing_the_wrong_operation_in_a_story_is_a_word_problem_slip_not_an_addition_one():
    got = charges(
        "word_1step", {"a": 47, "b": 38, "op": "+"}, ["NUM.PRB.02"], ["M_WRONG_OP", "M_NOCARRY"], "marbles"
    )
    assert got == {"M_WRONG_OP": "NUM.PRB.02", "M_NOCARRY": "NUM.OPS.01"}


def test_charges_a_mistake_about_equality_charges_equality_whatever_the_numbers():
    rules = dict(CHARGING, by_kind=dict(RULES["by_kind"], balance_scale=["NUM.OPS.05"]))
    spec = {"left": [20, 60], "right": [None, 40]}
    got = S.charges(
        "balance_scale",
        spec,
        "",
        S.used("balance_scale", spec, "", ["NUM.OPS.05"], rules),
        ["M_EQUALS_MEANS_ANSWER"],
        VOCAB,
        rules,
    )
    assert got == {"M_EQUALS_MEANS_ANSWER": "NUM.OPS.05"}


def test_charges_a_skill_the_question_does_not_use_falls_back_to_its_own_skill():
    got = charges(
        "bare_sum", {"a": 47, "b": 38, "op": "+"}, ["NUM.OPS.01"], ["M_COMPARE_REVERSED", "M_UNKNOWN"]
    )
    assert got == {"M_COMPARE_REVERSED": "NUM.OPS.01", "M_UNKNOWN": "NUM.OPS.01"}


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
    assert items and all(
        it.skills == ["NUM.PRB.02", "NUM.MEAS.04", "NUM.OPS.01", "NUM.OPS.02"] for it in items
    )


def test_fill_labels_3_digit_addition_with_addition_alone(conn):
    from engine import refill

    _, _, items = refill.fill_cases(conn, "ADD.3D.REG", "Medium", 16, dry_run=True)
    assert items and {tuple(it.skills) for it in items if it.fmt in ("column_grid", "bare_sum")} == {
        ("NUM.OPS.01",)
    }


def test_relabel_leaves_no_question_carrying_a_skill_it_does_not_use(conn):
    labels.relabel(conn)
    assert labels.mislabelled(conn) == []
    assert labels.relabel(conn) == {
        "skills": 0,
        "mistake_skills": 0,
        "tags": 0,
    }  # a second pass finds nothing


def test_relabel_records_what_each_mistake_on_a_budget_problem_charges(conn):
    labels.relabel(conn)
    row = conn.execute(
        "select mistake_skills from item where status = 'active' and skill_set_code = 'WORD.BUDGET' limit 1"
    ).fetchone()
    assert {"M_SUM_ONLY": "NUM.OPS.02", "M_ONE_STEP_ONLY": "NUM.PRB.02"}.items() <= row[
        "mistake_skills"
    ].items()
    assert row["mistake_skills"].get("M_WRONG_OP", "NUM.PRB.02") == "NUM.PRB.02"


def test_every_named_mistake_says_which_skill_it_charges(conn):
    rows = conn.execute("select code, op, skill_from, skill_code from misconception").fetchall()
    assert rows and all(r["skill_from"] == "operation" or r["skill_code"] for r in rows)


def test_relabel_never_touches_a_question_from_an_old_paper(conn):
    before = conn.execute(
        "select id, skill_codes, spec from item where source = 'legacy' order by id limit 20"
    ).fetchall()
    labels.relabel(conn)
    after = {
        r["id"]: (r["skill_codes"], json.dumps(r["spec"], sort_keys=True))
        for r in conn.execute(
            "select id, skill_codes, spec from item where id = any(%s)", ([b["id"] for b in before],)
        )
    }
    assert all(after[b["id"]] == (b["skill_codes"], json.dumps(b["spec"], sort_keys=True)) for b in before)


# ---------------------------------------------------------------- 8c: evidence per skill, on the copy


def _paper(conn, answers):
    """One child, one scanned paper, one answer row per (item_id, status, codes). Returns the child."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','TESTSEC8','G4') returning id",
        (tenant,),
    ).fetchone()["id"]
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, week) values (%s,'G4','2026-W39') returning id",
        (tenant,),
    ).fetchone()["id"]
    inst = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id)"
        " values (%s, 'CSTEST8' || substr(md5(random()::text), 1, 6), %s, %s) returning id",
        (tenant, tpl, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, sheet_instance_id) values (%s,'test/8c.pdf',%s) returning id",
        (tenant, inst),
    ).fetchone()["id"]
    for item_id, status, codes in answers:
        conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, status, misconception_codes)"
            " values (%s,%s,%s,'ans',%s,%s)",
            (tenant, cap, item_id, status, codes),
        )
    return child


def _item(conn, where):
    return conn.execute(
        f"select id, skill_codes from item where status = 'active' and {where} limit 1"
    ).fetchone()


def _evidence(conn, child):
    return [
        (r["skill_code"], r["correct"], sorted(r["misconception_codes"]))
        for r in conn.execute(
            "select skill_code, correct, misconception_codes from evidence_event where child_id = %s"
            " order by skill_code, correct nulls first",
            (child,),
        )
    ]


def test_confirm_a_right_budget_answer_is_evidence_for_each_skill_it_uses(conn):
    labels.relabel(conn)
    q = _item(conn, "skill_set_code = 'WORD.BUDGET'")
    child = _paper(conn, [(q["id"], "correct", [])])
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    assert _evidence(conn, child) == sorted((s, True, []) for s in q["skill_codes"])


def test_confirm_added_but_never_subtracted_is_evidence_against_subtraction_only(conn):
    labels.relabel(conn)
    q = _item(conn, "skill_set_code = 'WORD.BUDGET'")
    child = _paper(conn, [(q["id"], "wrong", ["M_SUM_ONLY"])])
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    assert _evidence(conn, child) == [("NUM.OPS.02", False, ["M_SUM_ONLY"])]


def test_confirm_an_unexplained_wrong_answer_or_a_blank_counts_once_against_the_questions_own_skill(conn):
    labels.relabel(conn)
    two = conn.execute(
        "select id from item where status = 'active' and skill_set_code = 'WORD.BUDGET' limit 2"
    ).fetchall()
    child = _paper(conn, [(two[0]["id"], "wrong", []), (two[1]["id"], "blank", [])])
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    assert _evidence(conn, child) == [("NUM.PRB.02", None, []), ("NUM.PRB.02", False, [])]


def test_confirm_a_one_skill_question_counts_exactly_as_it_did_before(conn):
    labels.relabel(conn)
    q = _item(conn, "skill_set_code = 'ADD.2D.REG' and fmt = 'column_grid'")
    child = _paper(conn, [(q["id"], "wrong", ["M_NOCARRY"])])
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    assert q["skill_codes"] == ["NUM.OPS.01"]
    assert _evidence(conn, child) == [("NUM.OPS.01", False, ["M_NOCARRY"])]


def test_next_difficulty_counts_answers_not_evidence_rows(conn):
    """A right budget answer is four evidence rows; the level rule must still see one answer. Two right and
    one wrong is 67 % — the level holds. Counted by rows it would be 8 of 9 and promote the child."""
    labels.relabel(conn)
    three = conn.execute(
        "select id from item where status = 'active' and skill_set_code = 'WORD.BUDGET' limit 3"
    ).fetchall()
    child = _paper(
        conn,
        [
            (three[0]["id"], "correct", []),
            (three[1]["id"], "correct", []),
            (three[2]["id"], "wrong", ["M_SUM_ONLY"]),
        ],
    )
    conn.execute("select confirm_results(%s, 'a test')", (child,))
    row = conn.execute("select * from next_difficulty(%s, 'WORD.BUDGET')", (child,)).fetchone()
    assert row["rule"] == "from_state" and row["difficulty"] == "Medium"
