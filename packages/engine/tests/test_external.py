"""W3 — placing a paper that is not on the add/sub ladder against the skill registry.

The cases here are the ones the first real run got wrong, on both SOF forms: a cover page invents a
question, and a question numbered once holds two answers.
"""

from engine import external


def q(n, part="", page=None):
    return {"n": n, "part": part, "question_as_printed": f"q{n}{part}", "what_it_tests": "x"}


def test_a_cover_page_invention_loses_to_the_page_that_prints_the_question():
    """Measured on both booklets: page 1 returned exactly one question, numbered in the middle of a
    run that page 4 or 5 actually prints. Keeping the first occurrence kept the invention."""
    kept, conflicts = external.resolve({1: [q(18)], 5: [q(16), q(17), q(18), q(19)]})
    assert [k["n"] for k in kept] == [16, 17, 18, 19]
    assert all(k["page"] == 5 for k in kept)
    assert conflicts == [{"n": 18, "part": "", "kept": 5, "dropped": 1}]


def test_one_printed_number_with_two_parts_stays_two_questions():
    """`35 (p)` and `35 (q)` are two answers and are marked separately — the same defect class as the
    Cambridge paper's Q5, whose three boxes were stored as one row."""
    kept, conflicts = external.resolve({8: [q(35, "p"), q(35, "q")]})
    assert [(k["n"], k["part"]) for k in kept] == [(35, "p"), (35, "q")]
    assert conflicts == []


def test_nothing_is_dropped_when_no_two_pages_claim_the_same_question():
    kept, conflicts = external.resolve({2: [q(1), q(2)], 3: [q(3)]})
    assert len(kept) == 3
    assert conflicts == []


def test_questions_come_back_in_printed_order_whatever_order_pages_resolved_in():
    """Resolution walks the richest page first, so the output has to be re-sorted or a reader sees
    the paper out of order."""
    kept, _ = external.resolve({7: [q(30)], 2: [q(1), q(2), q(3)]})
    assert [(k["page"], k["n"]) for k in kept] == [(2, 1), (2, 2), (2, 3), (7, 30)]


def test_the_rate_is_what_landed_not_what_was_confident():
    matches = [
        {"confidence": "clear"},
        {"confidence": "clear"},
        {"confidence": "arguable"},
        {"confidence": "none"},
    ]
    r = external.rate(matches)
    assert r["total"] == 4
    assert r["mapped"] == 0.75  # clear + arguable: the registry has a home for it
    assert r["clear_only"] == 0.5


def test_unmatched_questions_group_by_what_the_engine_thinks_they_test():
    """One stray is not a skill; a cluster is the candidate. Grouping is what makes that visible."""
    groups = external.unmatched_groups(
        [
            {"confidence": "none", "proposed_skill": "Embedded figures", "n": "4"},
            {"confidence": "none", "proposed_skill": "embedded figures ", "n": "9"},
            {"confidence": "none", "proposed_skill": "Letter sequences", "n": "2"},
            {"confidence": "clear", "proposed_skill": "", "n": "3"},
        ]
    )
    assert groups[0] == ("embedded figures", ["4", "9"])
    assert len(groups) == 2
