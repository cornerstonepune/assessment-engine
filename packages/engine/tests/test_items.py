"""Generator constraints.

An item that claims one regrouping but needs none is a silent failure: it prints, a child
answers it, and the result is filed against a rung it never tested. The spec calls this out
explicitly (§8.2) as common and worth checking on purpose.
"""

import random

import pytest

from engine.assess import diagnosis as D
from engine.assess import equality as EQ
from engine.assess import items as I
from engine.assess import missing_digits as MD
from engine.assess import reasoning as RS
from engine.assess import tags


def test_sample_add_produces_exactly_the_requested_regrouping_count():
    rng = random.Random(7)
    for _ in range(50):
        a, b = I.sample_add(rng, 2, 2, {1})
        assert I._regroup_count_add(a, b) == 1, (a, b)


def test_sample_add_honours_a_two_regrouping_request():
    rng = random.Random(9)
    for _ in range(30):
        a, b = I.sample_add(rng, 3, 3, {2})
        assert I._regroup_count_add(a, b) == 2, (a, b)


def test_sample_sub_across_zero_has_a_zero_in_a_column_that_gets_borrowed_from():
    # "Across zero" means the zero is a lender column. The ones column is never a lender,
    # so 970 - 339 does not qualify: the slice drops the last digit, not the first.
    rng = random.Random(11)
    for _ in range(25):
        a, b = I.sample_sub(rng, 3, 3, {1, 2}, across_zero=True)
        assert "0" in str(a)[:-1], (a, b)
        assert a > b, "a subtraction item must not have a negative answer"


def test_sample_sub_without_across_zero_has_no_zero_in_a_lender_column():
    rng = random.Random(13)
    for _ in range(25):
        a, b = I.sample_sub(rng, 3, 3, {1}, across_zero=False)
        assert "0" not in str(a)[:-1], (a, b)


def test_bare_sum_answer_is_exact_arithmetic():
    rng = random.Random(3)
    for op in ("+", "-"):
        item = I.bare_sum(rng, "R5" if op == "+" else "R6", "Procedural", op, 2, 2, {1})
        a, b = item.spec["a"], item.spec["b"]
        expected = a + b if op == "+" else a - b
        assert int(item.responses[0].answer) == expected


def test_misconception_table_never_contains_the_correct_answer():
    rng = random.Random(5)
    for _ in range(20):
        item = I.bare_sum(rng, "R6", "Procedural", "-", 2, 2, {1})
        r = item.responses[0]
        assert int(r.answer) not in [int(v) for v in r.misconceptions.values()]


def test_missing_digit_item_has_a_unique_solution():
    rng = random.Random(17)
    item = MD.one(
        rng, "R13", "Conceptual", {"op": "+", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
    )
    assert len(item.responses) == 2
    for r in item.responses:
        assert r.answer.isdigit() and len(r.answer) == 1


def test_estimate_item_carries_a_tolerance_so_a_near_estimate_is_not_marked_wrong():
    rng = random.Random(19)
    item = I.estimate_then_calc(rng, "R11", "Application", "+", 3, 3, {1})
    est = next(r for r in item.responses if r.rid == "est")
    exact = next(r for r in item.responses if r.rid == "ans")
    assert est.tolerance, "an estimate marked to the exact digit is not an estimate"
    assert exact.tolerance is None, "the exact answer must not be marked with a tolerance"


@pytest.mark.parametrize("digits_b", [1, 2])
def test_unequal_length_operands_are_tagged_as_requiring_alignment(digits_b):
    rng = random.Random(23)
    item = I.bare_sum(rng, "R5", "Procedural", "+", 3, digits_b, {1}, layout="column")
    t = tags.derive(item)
    if digits_b == 3:
        return
    assert t["alignment_required"] == "YES"
    assert t["operand_order"] == "LONGER_FIRST"


@pytest.mark.parametrize("kind,expect_op", [("near100", "+"), ("same_tens", "-"), ("near1000", "+")])
def test_efficient_method_honours_an_explicit_kind(kind, expect_op):
    # STRATEGY.EFFICIENT's Easy/Medium/Hard bands each test one named shortcut family — without a
    # way to pin `kind`, the function's own random choice would mix all three into every band.
    rng = random.Random(29)
    for _ in range(10):
        item = I.efficient_method(rng, "R13", "Conceptual", kind=kind)
        assert item.spec["op"] == expect_op, (kind, item.spec)


def test_efficient_method_still_picks_a_random_kind_when_none_is_given():
    rng = random.Random(31)
    ops = {I.efficient_method(rng, "R13", "Conceptual").spec["op"] for _ in range(20)}
    assert ops == {"+", "-"}, "near100/near1000 give +, same_tens gives -; 20 draws should see both"


@pytest.mark.parametrize("digits", [2, 3])
def test_find_mistake_honours_a_digit_width(digits):
    # REASON.FIND_MISTAKE's Hard/Advance bands plant the mistake in a 3-digit calculation —
    # without a digits param the generator was fixed at 2-digit regardless of the band asked.
    rng = random.Random(37)
    item = D.find_mistake(rng, "X2", "Conceptual", op="+", digits=digits)
    assert len(str(item.spec["a"])) == digits and len(str(item.spec["b"])) == digits


def test_find_mistake_still_defaults_to_two_digit():
    rng = random.Random(41)
    item = D.find_mistake(rng, "X2", "Conceptual")
    assert len(str(item.spec["a"])) == 2


def test_explain_claim_defaults_to_the_true_compensation_claim_its_callers_expect():
    # blueprints.py calls this with no extra arguments; that behaviour must not move.
    rng = random.Random(43)
    item = D.explain_claim(rng, "X1", "Conceptual")
    tick = next(r for r in item.responses if r.rid == "tick")
    assert tick.answer == "yes" and item.spec["topic"] == "compensation"
    assert 120 <= item.spec["a"] <= 480


def test_explain_claim_can_state_a_false_claim_the_child_must_catch():
    rng = random.Random(47)
    item = D.explain_claim(rng, "X1", "Conceptual", claim_is_true=False)
    tick = next(r for r in item.responses if r.rid == "tick")
    assert tick.answer == "no", item.stem


def test_explain_claim_can_ask_about_regrouping_instead_of_compensation():
    rng = random.Random(53)
    item = D.explain_claim(rng, "X1", "Conceptual", claim_topic="regrouping", claim_is_true=False)
    assert item.spec["topic"] == "regrouping"
    assert next(r for r in item.responses if r.rid == "tick").answer == "no"
    assert "exchange" in item.stem.lower()


def test_explain_claim_honours_a_smaller_number_range_for_the_easy_band():
    rng = random.Random(59)
    for _ in range(10):
        item = D.explain_claim(rng, "X1", "Conceptual", a_range=(10, 99))
        assert 10 <= item.spec["a"] <= 99


@pytest.mark.parametrize("da,db", [(2, 1), (2, 2), (3, 1)])
def test_sample_mul_respects_digit_counts_and_skips_the_trivial_operands(da, db):
    """The one sampler a new operation costs, once (ADR 0010, W1 gate 3). x1 and x10 are not
    worth a question, so they are excluded the way sample_add excludes multiples of ten."""
    rng = random.Random(73)
    for _ in range(40):
        a, b = I.sample_mul(rng, da, db)
        assert (len(str(a)), len(str(b))) == (da, db), (a, b)
        assert a % 10 and b % 10 and a != 1 and b != 1, (a, b)


def test_sample_mul_honours_a_product_ceiling():
    rng = random.Random(79)
    for _ in range(30):
        a, b = I.sample_mul(rng, 2, 1, max_product=200)
        assert a * b <= 200, (a, b)


@pytest.mark.parametrize("op", ["+", "-"])
def test_number_line_bridges_one_ten_in_a_small_range(op):
    # R2's Advance band is "within 20, crossing ten": the first hop must land exactly on a ten,
    # and the whole question must stay inside the range.
    rng = random.Random(67)
    for _ in range(20):
        item = I.number_line_jumps(rng, "R2", "Conceptual", op, 20)
        a, b = item.spec["a"], item.spec["b"]
        land1 = int(next(r for r in item.responses if r.rid == "land1").answer)
        answer = int(next(r for r in item.responses if r.rid == "ans").answer)
        assert land1 % 10 == 0, (a, op, b, land1)
        assert answer == (a + b if op == "+" else a - b)
        assert 0 < answer <= 20 and 0 < a <= 20


def test_number_line_still_splits_into_tens_and_ones_at_full_scale():
    rng = random.Random(71)
    item = I.number_line_jumps(rng, "R9", "Procedural", "+", 200)
    assert item.spec["tens"] % 10 == 0 and 11 <= item.spec["b"] <= 39


def test_explain_claims_true_and_false_variants_are_different_items():
    # Same numbers, opposite claim: the stored spec must differ or one would overwrite the other.
    t = D.explain_claim(random.Random(61), "X1", "Conceptual", claim_is_true=True)
    f = D.explain_claim(random.Random(61), "X1", "Conceptual", claim_is_true=False)
    assert t.item_id != f.item_id


def _first(make, tries=200):
    """A generator's first question: some draws cannot make one and say so; the next draw can."""
    rng = random.Random(3)
    for _ in range(tries):
        try:
            return make(rng)
        except RuntimeError:
            continue
    raise AssertionError("no question in 200 draws")


def test_every_generator_gives_its_kind_the_working_space_the_bank_reads_back():
    """A question read back from the bank is printed with `layout.WORKING_LINES[fmt]`; a generator
    that gives its kind different room would print a stored question differently from a fresh one.
    Every band in the seed is driven through its own generator, and every generator no band uses
    yet is called directly — the day a skill set starts using it, it is already covered."""
    import json

    from engine.assess import bands, verify, words
    from engine.assess.layout import WORKING_LINES
    from engine.core import db

    rng = random.Random(7)
    made = []
    seed = json.loads((db.REPO_ROOT / "supabase/seed/skill_sets.json").read_text())["skill_sets"]
    for s in seed:
        for band in s["difficulty"].values():
            check = band.get("check", {})
            if check.get("format") in bands.NATIVE_GENERATORS:
                try:
                    made.append(bands.native_item(check["format"], check, rng, s["rung_code"], "Conceptual"))
                except (KeyError, ValueError, RuntimeError):
                    continue  # a band its generator cannot serve is filled another way (`bands.codes`)
    made += [
        I.bare_sum(rng, "R5", "Procedural", "+", 2, 2, {1}, layout="horizontal"),
        I.bare_sum(rng, "R5", "Procedural", "+", 2, 2, {1}, layout="column"),
        I.missing_part_20(rng, "R3", "Conceptual"),
        I.multi_add(rng, "R12", "Procedural"),
        MD.one(rng, "R9", "Conceptual", {"op": "+", "width": 3}),
        *(
            _first(lambda r, g=g: g(r))
            for g in (
                lambda r: EQ.equation(r, "R16", "Conceptual", "SAME_BOTH_SIDES"),
                lambda r: EQ.fact_family(r, "R16", "Conceptual", "FROM_ADDITION"),
                lambda r: EQ.inverse_check(r, "R16", "Conceptual", "+"),
                lambda r: RS.choose_estimate(r, "R18", "Conceptual"),
                lambda r: RS.possible_answer(r, "R18", "Conceptual"),
                lambda r: RS.odd_even(r, "R18", "Conceptual"),
                lambda r: RS.break_apart(r, "R13", "Conceptual"),
            )
        ),
        I.digit_cards(rng, "R13", "Conceptual"),
        I.partition_scaffold(rng, "R9", "Conceptual", {1}),
        I.sort_into_table(rng, "R9", "Conceptual", "+"),
        I.partial_worked(rng, "R10", "Conceptual"),
        words.word_1step(rng, "R8", "Application", 2, (0, 1)),
        # kinds whose levels are made of taxonomy cases since step 8h, so the seed loop above no longer
        # reaches them through a `format`
        D.find_mistake(rng, "X2", "Conceptual"),
        I.efficient_method(rng, "R13", "Conceptual"),
        I.number_line_jumps(rng, "R2", "Conceptual", "+", 20),
    ]
    assert {it.fmt for it in made} == set(WORKING_LINES), (
        "every kind the generators make has a row, and no row is orphaned"
    )
    for it in made:
        assert it.working_lines == WORKING_LINES[it.fmt], it.fmt
    for fmt, (_, lines, _) in verify.FORMATS.items():
        assert lines == WORKING_LINES[fmt], fmt
