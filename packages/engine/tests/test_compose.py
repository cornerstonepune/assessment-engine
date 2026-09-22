"""A child's paper composed from their graph: several skill sets, levels in proportion (goals/custom-paper.yaml,
step 14). The mixed bag is the same engine given a teacher's list.

Written 2026-09-22, before the work: `engine/w2_print/compose.py` does not exist yet, so each test fails.
`xfail(strict=True)` keeps the suite green meanwhile and turns the day a test passes into a failure until
its marker is taken off — `engine done custom-paper` reports every one NOT PROVED until then.
"""

import pytest

NOT_BUILT = pytest.mark.xfail(strict=True, reason="step 14, the paper engine: not built yet")
ORDER = ["Easy", "Medium", "Hard", "Advance"]

WEAK_SUB_STRONG_ADD = [
    ("425 - 38", "wrong", ["M_NO_DECREMENT"]),
    ("342 - 58", "wrong", ["M_NO_DECREMENT"]),
    ("456 - 23", "correct", []),
    ("342 + 268", "correct", []),
    ("247 + 315", "correct", []),
    ("678 + 457", "correct", []),
]


def _sat(conn, child):
    return {
        r["item_id"]
        for r in conn.execute(
            "select r.item_id from item_result r join capture c on c.id = r.capture_id"
            " join sheet_instance si on si.id = c.sheet_instance_id where si.child_id = %s",
            (child,),
        )
    }


@NOT_BUILT
def test_a_paper_draws_from_several_skill_sets_most_from_the_weakest(conn, old_paper):
    from engine.w2_print import compose

    child = old_paper(conn, WEAK_SUB_STRONG_ADD)
    p = compose.paper(conn, child)
    counts = {s["skill_set"]: s["n"] for s in p["sections"]}
    assert len(counts) >= 2 and max(counts, key=counts.get) == "SUB.2D.EXCH"
    assert sum(counts.values()) == len(p["items"])
    held = {
        r["id"]: (r["skill_set_code"], r["difficulty"])
        for r in conn.execute(
            "select id, skill_set_code, difficulty from item where id = any(%s)", (p["items"],)
        )
    }
    sections = {(s["skill_set"], d) for s in p["sections"] for d in s["levels"]}
    assert set(held.values()) <= sections
    assert not set(p["items"]) & _sat(conn, child)
    assert all(s["why"] for s in p["sections"])  # each section says in one line why it is there


@NOT_BUILT
def test_difficulty_is_mixed_in_the_proportion_the_config_row_sets(conn, old_paper):
    from engine.w2_print import compose

    child = old_paper(conn, WEAK_SUB_STRONG_ADD)
    mix = conn.execute("select value from config where key = 'compose.level_mix'").fetchone()["value"]
    for s in compose.paper(conn, child)["sections"]:
        at = ORDER.index(s["level"])
        steps = {ORDER.index(d) - at for d in s["levels"]}
        assert steps <= {-1, 0, 1}  # one level either side of the child's own, never further
        assert s["levels"][s["level"]] == max(s["levels"].values())  # most at the child's own level
        assert set(mix) == {"below", "at", "above"}


@NOT_BUILT
def test_a_mixed_bag_is_the_same_engine_given_the_teachers_list_of_skill_sets(conn, old_paper):
    from engine.w2_print import compose

    child = old_paper(conn, WEAK_SUB_STRONG_ADD)
    asked = ["ADD.2D.REG", "SUB.2D.EXCH", "WORD.1_2STEP"]
    p = compose.paper(conn, child, skill_sets=asked)
    assert {s["skill_set"] for s in p["sections"]} == set(asked)
    for s in p["sections"]:
        own = conn.execute(
            "select difficulty from next_difficulty(%s, %s)", (child, s["skill_set"])
        ).fetchone()
        assert own["difficulty"] in (None, s["level"])  # None: no answers yet, so the grade's starting level


@NOT_BUILT
def test_two_children_with_the_same_answers_get_different_papers(conn, old_paper):
    from engine.w2_print import compose

    one, two = old_paper(conn, WEAK_SUB_STRONG_ADD), old_paper(conn, WEAK_SUB_STRONG_ADD)
    assert set(compose.paper(conn, one)["items"]) != set(compose.paper(conn, two)["items"])
