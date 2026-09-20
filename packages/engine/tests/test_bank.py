"""The bank against the real schema, inside one transaction that is rolled back.

The model is replaced by a fake that returns candidates built from the deterministic sampler,
so these tests prove the rows, the verifier's gate, the trigger and the renderer — not Gemini.
"""

import os
import random

import pytest

from engine import bank, db, spec
from engine.assess import bands
from engine.assess import items as I
from engine.assess import misconceptions as M

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET, DIFF = "SUB.2D.EXCH", "Hard"  # 3-digit minus 2-digit, one exchange


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def candidates(k, seed=3):
    rng = random.Random(seed)
    out = []
    while len(out) < k:
        a, b = I.sample_sub(rng, 3, 2, {1})
        fmt = ["column_grid", "bare_sum", "word_1step"][len(out) % 3]
        stem = f"A shop had {a} mangoes and sold {b}. How many are left?" if fmt == "word_1step" else ""
        out.append(
            {
                "format": fmt,
                "op": "-",
                "a": a,
                "b": b,
                "answer": a - b,
                "stem": stem,
                "missing": None,
                "misconceptions": [{"code": c, "wrong_answer": v} for c, v in M.predict("-", a, b).items()],
            }
        )
    return out


def fake_model(batch):
    def generate(conn, purpose, variables, images=(), subject=None, meta=None):
        assert purpose == "item_generate" and "spec" in variables
        if meta is not None:
            meta.update(prompt_id=None, model="fake-model")
        return {"items": batch}

    return generate


def test_spec_is_built_only_from_rows(conn):
    prompt_input, s, check = spec.read(conn, SET, DIFF)
    assert check == {"op": "-", "digits": [3, 2], "regroups": [1]}
    assert prompt_input["difficulty"].startswith("Hard:")
    assert any("exchange" in line.lower() for line in prompt_input["philosophy"])
    assert {m["code"] for m in prompt_input["misconceptions"]} >= {"M_SMALL_FROM_LARGE", "M_NO_DECREMENT"}
    assert s["rung_code"] == "R6"


def test_fill_stores_verified_items_and_gates_the_rest(conn, monkeypatch):
    good = candidates(3)
    bad = dict(
        good[0], a=good[0]["a"], answer=good[0]["answer"] + 1, format="bare_sum"
    )  # wrong key, same numbers
    dup = dict(good[1])
    monkeypatch.setattr(bank.llm, "generate", fake_model(good + [bad, dup]))
    counts, reasons, accepted = bank.fill(conn, SET, DIFF, 3)
    assert counts["accepted"] == 3 and counts["duplicate"] >= 1
    assert counts["rejected"] == 1 and "answer" in reasons
    row = conn.execute(
        "select status, source, skill_set_code, difficulty, tags, rung_code from item where item_key = %s",
        (accepted[0].item_id,),
    ).fetchone()
    assert (row["status"], row["source"], row["skill_set_code"], row["difficulty"], row["rung_code"]) == (
        "active",
        "generated",
        SET,
        DIFF,
        "R6",
    )
    assert row["tags"]["operation"] == "SUB" and row["tags"]["regrouping"] == "SINGLE"


def test_fill_accepts_the_typographic_minus_the_model_actually_writes(conn, monkeypatch):
    batch = [dict(c, op="−") for c in candidates(2, seed=11)]
    monkeypatch.setattr(bank.llm, "generate", fake_model(batch))
    counts, _, accepted = bank.fill(conn, SET, DIFF, 2)
    assert counts["accepted"] == 2 and accepted[0].spec["op"] == "-"


def test_filling_again_with_the_same_numbers_adds_nothing(conn, monkeypatch):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(3)))
    bank.fill(conn, SET, DIFF, 3)
    before = conn.execute("select count(*) as n from item").fetchone()["n"]
    counts, _, _ = bank.fill(conn, SET, DIFF, 3)
    assert counts["accepted"] == 0 and counts["already_in_bank"] > 0
    assert conn.execute("select count(*) as n from item").fetchone()["n"] == before


def test_recheck_agrees_with_what_the_verifier_let_through(conn, monkeypatch):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(4)))
    bank.fill(conn, SET, DIFF, 4)
    assert bank.recheck(conn) == []


def test_recheck_catches_an_answer_edited_behind_the_engines_back(conn, monkeypatch):
    """The audit exists for the case nobody plans for: a row changed by hand."""
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(2)))
    _, _, accepted = bank.fill(conn, SET, DIFF, 2)
    key = accepted[0].item_id
    conn.execute(
        "update item set responses = jsonb_set(responses::jsonb, '{0,answer}', '\"999\"')::json"
        " where item_key = %s",
        (key,),
    )
    assert key in bank.recheck(conn)


def test_recheck_passes_the_missing_number_items_the_samplers_make(conn):
    """A missing-number question's answer is the hidden number, and its distractors are about
    that number — not about the whole equation. The audit must use the same rule."""
    counts, _, accepted = bank.fill(conn, SET, DIFF, 8, offline=True)
    assert counts["accepted"] == 8
    assert any(i.fmt == "missing_number" for i in accepted), "the sampler should make some"
    assert bank.recheck(conn) == []


def test_a_flag_retires_the_item_by_trigger(conn, monkeypatch):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(2)))
    _, _, accepted = bank.fill(conn, SET, DIFF, 2)
    assert bank.flag(conn, accepted[0].item_id, "nimish", "odd wording") == "retired"
    assert (
        conn.execute("select verdict from item_feedback where note = 'odd wording'").fetchone()["verdict"]
        == "retire"
    )


def test_sampled_with_an_op_list_produces_both_operations():
    # R4 (2-digit +/- without regrouping) is one skill_set covering both operations.
    check = {"op": ["+", "-"], "digits": [2, 2], "regroups": [0]}
    cands = bank._sampled(check, ["bare_sum"], 20, seed=1)
    assert len(cands) == 20
    assert {c["op"] for c in cands} == {"+", "-"}
    for c in cands:
        assert c["answer"] == M.compute(c["op"], c["a"], c["b"])


def test_sampled_refuses_a_skill_set_with_no_sampler_format():
    # R11/X2 declare only a native-generator format (estimate_then_calc, find_mistake) that the
    # sampler cannot render; it must refuse, not silently fall back to plain column arithmetic.
    check = {"op": "+", "digits": [2, 2], "regroups": [1]}
    with pytest.raises(ValueError, match="sampler"):
        bank._sampled(check, ["estimate_then_calc"], 5, seed=1)


def test_coverage_lists_every_skill_set_by_difficulty_with_real_counts(conn, monkeypatch):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(3)))
    bank.fill(conn, SET, DIFF, 3)
    table = bank.coverage(conn)
    # Every skill_set x every difficulty band, zeros included. Derived, not hardcoded: adding a
    # skill set is a row (W1 gate 3 added multiplication that way), and this must not need an edit.
    sets = conn.execute("select count(*) as n from skill_set").fetchone()["n"]
    assert len(table) == sets * 4
    row = next(r for r in table if r["code"] == SET and r["difficulty"] == DIFF)
    assert row["n"] >= 3
    # Every skill set must report all four bands, zeros included — the point of the grid is that
    # an empty unit is a visible 0, not a missing row. (No cell is empty any more, so this is
    # asserted on the shape rather than on any one unit staying at zero.)
    by_code = {}
    for r in table:
        by_code.setdefault(r["code"], []).append(r["difficulty"])
    assert all(set(v) == {"Easy", "Medium", "Hard", "Advance"} for v in by_code.values())
    assert all(isinstance(r["n"], int) and r["n"] >= 0 for r in table)


def test_coverage_targets_what_a_class_needs_and_a_units_own_ceiling_when_it_has_one(conn):
    """The target is `(class_size + spares) x items_per_sheet` — what one week of one class draws
    without replacement (ADR 0016) — except where a band recorded its whole number range."""
    need = bank._class_need(conn)
    assert need == 216, "16 children at 12 questions with 2 spares"
    rows = {(r["code"], r["difficulty"]): r for r in bank.coverage(conn)}
    assert rows[("SUB.2D.EXCH", "Hard")]["target"] == need
    small = rows[("ADD.1D.WITHIN10", "Easy")]
    assert small["target"] < need, "a rung whose numbers run out keeps its measured ceiling"
    assert (
        small["target"]
        == conn.execute(
            "select (difficulty -> 'Easy' ->> 'min_items')::int as n from skill_set where code = 'ADD.1D.WITHIN10'"
        ).fetchone()["n"]
    )


NATIVE_UNITS = [
    ("MENTAL.BRIDGE_EQ", "Easy"),
    ("MENTAL.BRIDGE_EQ", "Medium"),
    # MENTAL.BRIDGE_EQ Hard (balance_scale, hi=100) is not here: the real bank already holds 48
    # of its true ceiling (STATE.md, "W1 gate 2, chunk B") — a fresh 5-more request has almost no
    # room left, the same class of shortfall as R1/R2, not a dispatch bug this test should catch.
    ("MENTAL.BRIDGE_EQ", "Advance"),
    ("WORD.1_2STEP", "Easy"),
    ("WORD.1_2STEP", "Medium"),
    ("WORD.1_2STEP", "Hard"),
    ("WORD.1_2STEP", "Advance"),
    ("ESTIMATE.ROUND10", "Easy"),
    ("ESTIMATE.ROUND10", "Medium"),
    ("ESTIMATE.ROUND10", "Hard"),
    ("ESTIMATE.ROUND10", "Advance"),
    ("ADDSUB.4D.ADV", "Easy"),
    ("ADDSUB.4D.ADV", "Medium"),
    ("STRATEGY.EFFICIENT", "Easy"),
    ("STRATEGY.EFFICIENT", "Medium"),
    ("STRATEGY.EFFICIENT", "Hard"),
    ("STRATEGY.EFFICIENT", "Advance"),
    ("WORD.BUDGET", "Easy"),
    ("WORD.BUDGET", "Medium"),
    ("WORD.BUDGET", "Hard"),
    ("WORD.BUDGET", "Advance"),
    ("REASON.FIND_MISTAKE", "Easy"),
    ("REASON.FIND_MISTAKE", "Medium"),
    ("REASON.FIND_MISTAKE", "Hard"),
    ("REASON.FIND_MISTAKE", "Advance"),
    # ADD.1D.WITHIN10 Advance (missing_number, add_missing_addend, hi=10) is not here: its true
    # ceiling is 24 (STATE.md, "W1 gate 2, chunk B") — "sums to 10" has only so many (a, b)
    # pairs, and the real bank already holds all of them; the same class of shortfall as above.
    # ADD.1D.BRIDGE10 Advance (number_line_jumps, hi=20) is deliberately not here: that
    # generator's second jump needs hi >= 54 (see items.number_line_jumps) — see the test below.
    # REASON.EXPLAIN (X1) is deliberately not here — see NATIVE_GENERATORS' comment in bank.py.
]


@pytest.mark.parametrize("code,difficulty", NATIVE_UNITS)
def test_fill_native_produces_items_for_every_native_unit(conn, code, difficulty):
    """Five new questions, or nothing because the unit is already at its measured ceiling.

    Both are correct and the difference is a row: once a band records `min_items` — its whole number
    range (ADR 0011/0016) — a further fill *must* accept nothing. `MENTAL.BRIDGE_EQ Easy` holds 145
    and the numbers are spent. Asserting five unconditionally made a full bank look like a bug.
    """
    band = conn.execute("select difficulty from skill_set where code = %s", (code,)).fetchone()["difficulty"][
        difficulty
    ]
    counts, accepted = bank.fill_native(conn, code, difficulty, 5)
    assert counts["accepted"] == len(accepted)
    if counts["accepted"] < 5:
        assert band.get("min_items"), (
            f"{code} {difficulty} produced {counts['accepted']} of 5 and claims no ceiling —"
            " either the generator is broken or the band never recorded its universe"
        )


def test_fill_native_refuses_a_hi_below_any_possible_jump_rather_than_crashing_obscurely():
    # hi=20 is now supported (the bridge jump); a range with no room for any ten-crossing at all
    # must still fail with a sentence, not a raw randrange error from deep inside the generator.
    with pytest.raises(RuntimeError, match="hi"):
        bands.native_item("number_line_jumps", {"op": "+", "hi": 6}, random.Random(3), "R2", "Conceptual")


def test_fill_native_dry_run_inserts_nothing(conn):
    before = conn.execute("select count(*) as n from item").fetchone()["n"]
    counts, accepted = bank.fill_native(conn, "WORD.BUDGET", "Easy", 5, dry_run=True)
    assert counts["accepted"] == 5 and len(accepted) == 5
    assert conn.execute("select count(*) as n from item").fetchone()["n"] == before


def test_fill_native_honours_a_kind_list_across_the_shortcut_families(conn):
    # STRATEGY.EFFICIENT Advance's check names all three kinds; a real spread should show up.
    counts, accepted = bank.fill_native(conn, "STRATEGY.EFFICIENT", "Advance", 15)
    ops = {it.spec["op"] for it in accepted}
    assert ops == {"+", "-"}, "near100/near1000 give +, same_tens gives -"


def test_fill_native_produces_no_flow_run_row(conn):
    before = conn.execute("select count(*) as n from flow_run").fetchone()["n"]
    bank.fill_native(conn, "MENTAL.BRIDGE_EQ", "Hard", 5)
    assert conn.execute("select count(*) as n from flow_run").fetchone()["n"] == before


def test_sheet_renders_only_active_items_of_that_set(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(13)))
    _, _, accepted = bank.fill(conn, SET, DIFF, 13)
    bank.flag(conn, accepted[0].item_id, "nimish", "retired on purpose")
    key = bank.sheet(conn, SET, DIFF, 12, tmp_path)
    assert (tmp_path / f"{key['sheet_id']}.pdf").exists() and key["pages"] >= 1
    assert accepted[0].item_id not in {i["item_id"] for i in key["items"]}
    have = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        (SET, DIFF),
    ).fetchone()["n"]  # the real bank plus this test's
    with pytest.raises(ValueError, match=f"only {have}"):
        bank.sheet(conn, SET, DIFF, have + 1, tmp_path)
