"""A child's graph per skill set, read from their signed-off answers (goals/two-child-loop.yaml, step 13).

Written 2026-09-22, before the work: `engine/w3_read/skill_graph.py` does not exist yet, so each test fails.
`xfail(strict=True)` keeps the suite green meanwhile and turns the day a test passes into a failure until
its marker is taken off — `engine done two-child-loop` reports every one NOT PROVED until then.
"""

import pytest

NOT_BUILT = pytest.mark.xfail(strict=True, reason="step 13, the loop on two children: not built yet")

DHANVI_LIKE = [
    ("425 - 38", "wrong", ["M_NO_DECREMENT"]),
    ("342 - 58", "wrong", ["M_NO_DECREMENT"]),
    ("456 - 23", "correct", []),
    ("342 + 268", "correct", []),
]


def _graph(conn, old_paper):
    from engine.w3_read import skill_graph

    child = old_paper(conn, DHANVI_LIKE)
    return child, skill_graph.read(conn, child)


@NOT_BUILT
def test_every_signed_off_answer_is_on_the_graph_of_each_skill_set_that_holds_it(conn, old_paper):
    child, g = _graph(conn, old_paper)
    signed_off = {
        r["id"]
        for r in conn.execute(
            "select r.id from item_result r join capture c on c.id = r.capture_id"
            " join sheet_instance si on si.id = c.sheet_instance_id"
            " where si.child_id = %s and r.state = 'confirmed'",
            (child,),
        )
    }
    on_graph = {a for s in g["skills"] for a in s["answer_ids"]}
    assert on_graph | set(g["counted_nowhere"]) == signed_off
    by = {s["skill_set"]: s for s in g["skills"]}
    assert (by["SUB.2D.EXCH"]["answers"], by["SUB.2D.EXCH"]["right"]) == (3, 1)


@NOT_BUILT
def test_each_skill_is_read_as_a_state_with_the_childs_own_example(conn, old_paper):
    _, g = _graph(conn, old_paper)
    sub = {s["skill_set"]: s for s in g["skills"]}["SUB.2D.EXCH"]
    assert sub["state"] == "patterned_error" and sub["mistake"] == "M_NO_DECREMENT"
    assert sub["example"]["question"] in {"425 - 38 =", "342 - 58 ="}


@NOT_BUILT
def test_each_skill_is_read_in_one_plain_sentence_a_teacher_can_act_on(conn, old_paper):
    _, g = _graph(conn, old_paper)
    sentence = {s["skill_set"]: s for s in g["skills"]}["SUB.2D.EXCH"]["sentence"]
    mistake = conn.execute(
        "select name from misconception where code = 'M_NO_DECREMENT' and op = '-'"
    ).fetchone()["name"]
    assert "1 of 3" in sentence and mistake.lower() in sentence.lower()
    assert "M_" not in sentence and "SUB." not in sentence  # codes are demoted, never led with
