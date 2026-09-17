"""The bank against the real schema, inside one transaction that is rolled back.

The model is replaced by a fake that returns candidates built from the deterministic sampler,
so these tests prove the rows, the verifier's gate, the trigger and the renderer — not Gemini.
"""
import os
import random

import pytest

from engine import bank, db
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
        out.append({"format": fmt, "op": "-", "a": a, "b": b, "answer": a - b, "stem": stem, "missing": None,
                    "misconceptions": [{"code": c, "wrong_answer": v} for c, v in M.predict("-", a, b).items()]})
    return out


def fake_model(batch):
    def generate(conn, purpose, variables, images=()):
        assert purpose == "item_generate" and "spec" in variables
        return {"items": batch}
    return generate


def test_spec_is_built_only_from_rows(conn):
    prompt_input, s, check = bank.spec(conn, SET, DIFF)
    assert check == {"op": "-", "digits": [3, 2], "regroups": [1]}
    assert prompt_input["difficulty"].startswith("Hard:")
    assert any("exchange" in line.lower() for line in prompt_input["philosophy"])
    assert {m["code"] for m in prompt_input["misconceptions"]} >= {"M_SMALL_FROM_LARGE", "M_NO_DECREMENT"}
    assert s["rung_code"] == "R6"


def test_fill_stores_verified_items_and_gates_the_rest(conn, monkeypatch):
    good = candidates(3)
    bad = dict(good[0], a=good[0]["a"], answer=good[0]["answer"] + 1, format="bare_sum")  # wrong key, same numbers
    dup = dict(good[1])
    monkeypatch.setattr(bank.llm, "generate", fake_model(good + [bad, dup]))
    counts, reasons, accepted = bank.fill(conn, SET, DIFF, 3)
    assert counts["accepted"] == 3 and counts["duplicate"] >= 1
    assert counts["rejected"] == 1 and "answer" in reasons
    row = conn.execute("select status, source, skill_set_code, difficulty, tags, rung_code from item where item_key = %s",
                       (accepted[0].item_id,)).fetchone()
    assert (row["status"], row["source"], row["skill_set_code"], row["difficulty"], row["rung_code"]) == \
           ("active", "generated", SET, DIFF, "R6")
    assert row["tags"]["operation"] == "SUB" and row["tags"]["regrouping"] == "SINGLE"


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


def test_a_flag_retires_the_item_by_trigger(conn, monkeypatch):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(2)))
    _, _, accepted = bank.fill(conn, SET, DIFF, 2)
    assert bank.flag(conn, accepted[0].item_id, "nimish", "odd wording") == "retired"
    assert conn.execute("select verdict from item_feedback where note = 'odd wording'").fetchone()["verdict"] == "retire"


def test_sheet_renders_only_active_items_of_that_set(conn, monkeypatch, tmp_path):
    monkeypatch.setattr(bank.llm, "generate", fake_model(candidates(13)))
    _, _, accepted = bank.fill(conn, SET, DIFF, 13)
    bank.flag(conn, accepted[0].item_id, "nimish", "retired on purpose")
    key = bank.sheet(conn, SET, DIFF, 12, tmp_path)
    assert (tmp_path / f"{key['sheet_id']}.pdf").exists() and key["pages"] >= 1
    assert accepted[0].item_id not in {i["item_id"] for i in key["items"]}
    with pytest.raises(ValueError, match="only 12"):
        bank.sheet(conn, SET, DIFF, 13, tmp_path)
