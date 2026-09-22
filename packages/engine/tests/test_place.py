"""Which skill sets an old paper's question counts for, and the next paper it shapes (engine/w3_read/place.py).

The case these were written for: on shared rung R9 (3-digit ± with regrouping) Dhanvi's subtraction
mistakes were charged to 3-digit addition's next paper, and 3-digit subtraction got none.
"""

from engine.core import db
from engine.w3_read import place

KIND_AS = {"legacy_bare": "bare_sum", "legacy_word": "bare_sum", "legacy_missing": "missing_number"}


def test_placements_a_three_digit_subtraction_counts_for_the_subtraction_levels_that_hold_it(old_row):
    holders = {"S31": [("SUB.2D.EXCH", "Hard")], "A40": [("ADD.3D.REG", "Hard")]}
    matches = {
        "S31": {"fmt": ["bare_sum"], "operation": "SUB", "operand_1_digits": 3, "operand_2_digits": 2},
        "A40": {"fmt": ["bare_sum"], "operation": "ADD", "operand_1_digits": 3},
    }
    on_rung = {"R9": [("ADD.3D.REG", ["NUM.OPS.01"])]}
    assert place.placements(old_row("425 - 38"), KIND_AS, matches, holders, on_rung) == [
        ("SUB.2D.EXCH", "Hard", "case:S31")
    ]


def test_placements_no_case_falls_back_to_the_rungs_skill_set_only_when_it_practises_the_skill(old_row):
    on_rung = {"R9": [("ADD.3D.REG", ["NUM.OPS.01"])]}
    add = old_row("342 + 268", fmt="legacy_text")
    sub = old_row("862 - 268", fmt="legacy_text")
    assert place.placements(add, KIND_AS, {}, {}, on_rung) == [("ADD.3D.REG", None, "rung")]
    assert place.placements(sub, KIND_AS, {}, {}, on_rung) == []


def test_a_subtraction_mistake_on_a_shared_rung_shapes_the_subtraction_paper_not_the_addition_one(
    conn, old_paper
):
    child = old_paper(
        conn,
        [
            ("425 - 38", "wrong", ["M_NO_DECREMENT"]),
            ("342 - 58", "wrong", ["M_NO_DECREMENT"]),
            ("456 - 23", "correct", []),
        ],
    )
    added = conn.execute("select * from next_difficulty(%s, 'ADD.3D.REG')", (child,)).fetchone()
    taken = conn.execute("select * from next_difficulty(%s, 'SUB.2D.EXCH')", (child,)).fetchone()
    assert added["rule"] == "band_default" and added["targets"] == []
    assert taken["rule"] == "from_state" and taken["targets"] == ["M_NO_DECREMENT"]


def test_place_lists_an_old_question_that_counts_for_no_skill_set(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem, spec,"
        " responses, source) values (%s,'legacy/TESTPLACE/order','legacy','R11','{NUM.PV.02}','Procedural',"
        " 'legacy_text','Arrange from smallest to largest: 45, 12, 30','{\"kind\": \"text\"}','[]','legacy')",
        (tenant,),
    )
    assert "legacy/TESTPLACE/order" in {r["item_key"] for r in place.place(conn)}
