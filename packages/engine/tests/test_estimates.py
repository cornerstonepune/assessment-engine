"""Estimating a product or a quotient, and judging an answer without working it out (goals/md4b1-estimates.yaml).

MD.ESTIMATE (Grade 4) holds the drafted document's ten estimating cases. Each is drawn on the sizes of its example,
here as on the skill it shares; odd or even, the closest estimate and whether an answer can be right are asked of a
product as well as a sum; and every judging question names a mistake a wrong answer shows. Every answer is worked out
here from the question as printed, never read back from the code that made it."""

import dataclasses
import importlib
import json
import pathlib
import random
import sys
from collections import Counter

from engine.assess import draw, skills, tags, taxonomy
from engine.assess import misconceptions as M
from engine.assess import reasoning as RS
from engine.assess.rounding import half_up
from engine.checks import scenarios
from engine.w1_bank import cases
from engine.w3_read import marking

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
VOCAB = {(m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code")) for m in ROWS}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
LEVELS = {
    "Easy": ["V06", "V07"],
    "Medium": ["V01", "V03", "V04"],
    "Hard": ["V02", "V08", "V10"],
    "Advance": ["V05", "V09"],
}
# each case's example, its numbers' sizes: a × either way round (A10), a ÷ as written
SIZES = {
    "V06": ("×", (2, 1)),  # 6 × 13
    "V07": ("×", (2, 1)),  # 47 × 3
    "V01": ("×", (2, 1)),  # 48 × 6
    "V03": ("×", (2, 2)),  # 67 × 75
    "V04": ("÷", (3, 1)),  # 156 ÷ 4
    "V02": ("×", (2, 2)),  # 38 × 21
    "V08": ("×", (2, 1)),  # 52 × 9
    "V10": ("÷", (3, 1)),  # 412 ÷ 8
    "V05": ("×", (2, 1)),  # 23 × 4
    "V09": ("÷", (2, 1)),  # 47 ÷ 6
}
# the shared cases, and the Advance each is also on
SHARED = {
    "V07": "MUL.2D1D",
    "V01": "MUL.2D1D",
    "V03": "MUL.2D2D",
    "V02": "MUL.2D2D",
    "V04": "DIV.3D1D",
    "V10": "DIV.3D1D",
    "V09": "DIV.2D1D",
}
SIZE_KEYS = ("digits_max", "digits_min", "operand_1_digits", "operand_2_digits")
R = "R48"
if str(ROOT / "research") not in sys.path:
    sys.path.insert(0, str(ROOT / "research"))


def _estimate():
    return SETS["MD.ESTIMATE"]


def _drawn(code, level, case, n, rows=None, seed=5):
    """[question] of one case drawn alone on a level, as the bank draws it (`cases.on_level`), from `rows` (the case
    rows by code, the seed's where none are given)."""
    check = {**SETS[code]["difficulty"][level]["check"], "cases": [case]}
    matches = cases.on_level(check, {c: row["match"] for c, row in (rows or CASES).items()})
    got = draw.level(random.Random(seed), check, matches, SETS[code]["rung_code"], n)
    return [it for _, it in got]


def _level(level, n, seed=5):
    """[(case, question)] of one MD.ESTIMATE level, drawn as the bank draws it."""
    check = _estimate()["difficulty"][level]["check"]
    matches = cases.on_level(check, {c: row["match"] for c, row in CASES.items()})
    got = draw.level(random.Random(seed), check, matches, R, n)
    assert len(got) == n, (level, len(got))
    return got


def _of(case, n=24, seed=5):
    level = next(lv for lv, cs in LEVELS.items() if case in cs)
    got = _drawn("MD.ESTIMATE", level, case, n, seed=seed)
    assert len(got) == n, (case, len(got))
    return got


def _sizes(it):
    return len(str(it.spec["a"])), len(str(it.spec["b"]))


def _tick(it):
    return next(r for r in it.responses if r.kind == "tick")


def _product_pairs(n, seed=7):
    """Numbers a closest estimate of a product is asked on: a 2-digit number that is not round and does not end in 5
    (equally near two tens), by a 1-digit number from 2 to 9."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        a, b = rng.randint(11, 99), rng.randint(2, 9)
        if a % 10 not in (0, 5):
            out.append((a, b))
    return out


def _built(build, pairs, seed=3):
    """A × judging kind built on each pair, as the drawer builds it; a pair it draws again is skipped."""
    rng, out = random.Random(seed), []
    for a, b in pairs:
        try:
            out.append(build(rng, a, b, R, {}))
        except RuntimeError:
            continue
    return out


def _judged(make, op, n, seed=11):
    """`n` + or − judging questions, as their own kind draws them."""
    rng, out = random.Random(seed), []
    while len(out) < n:
        try:
            out.append(make(rng, "R18", "Conceptual", op, 3))
        except RuntimeError:
            continue
    return out


# ------------------------------------------------------------------------------------------- the cases' sizes


def test_every_estimate_draws_the_sizes_of_its_example_on_a_level_with_no_shape_of_its_own():
    """MD.ESTIMATE's levels are made of cases and say no numbers' sizes: each case says its own, as its example has
    them, so 48 × 6 is drawn 2 digits by 1 here as on MUL.2D1D. Before, four of them failed (`KeyError: 'digits'`) and
    three drew numbers past Grade 4 (8686 ÷ 3)."""
    for case, (op, sizes) in SIZES.items():
        match = CASES[case]["match"]
        keys = ("digits_max", "digits_min") if op == "×" else ("operand_1_digits", "operand_2_digits")
        assert all(k in match for k in keys), (case, match)
        for it in _of(case, 12):
            got = _sizes(it)
            assert (tuple(sorted(got, reverse=True)) if op == "×" else got) == sizes, (case, it.spec)
            assert taxonomy.matches(match, it.fmt, tags.derive(it)), (case, it.spec)


def test_a_shared_estimate_draws_on_its_other_home_what_it_drew_before():
    """The sizes a case's row now says are its other home's own (MUL.2D1D is 2 digits by 1, as 48 × 6 is), so that home
    draws the very questions it drew before: nothing new reaches its bank, and nothing stored there is retired."""
    for case, code in SHARED.items():
        before = {
            **CASES,
            case: {
                **CASES[case],
                "match": {k: v for k, v in CASES[case]["match"].items() if k not in SIZE_KEYS},
            },
        }
        now = [it.item_id for it in _drawn(code, "Advance", case, 12)]
        then = [it.item_id for it in _drawn(code, "Advance", case, 12, rows=before)]
        assert now == then and len(now) == 12, (case, code)


# ------------------------------------------------------------------------------------------- the × judging kinds


def test_odd_or_even_of_a_product_past_the_tables():
    """V06: will 6 × 13 be odd or even? A product past the tables, 2 digits by 1, odd as often as even (three products in
    four are even, so a child who always ticked "even" would score three in four)."""
    drawn = _of("V06", 48)
    for it in drawn:
        s = it.spec
        assert it.fmt == "odd_even" and s["op"] == "×", s
        assert tags.derive(it)["fact"] == "NO" and sorted(_sizes(it), reverse=True) == [2, 1], s
        tick = _tick(it)
        assert tick.options == ["odd", "even"], tick
        assert tick.answer == ("even" if s["a"] * s["b"] % 2 == 0 else "odd"), s
        assert f"{s['a']} × {s['b']}" in it.stem and "odd or even" in it.stem, it.stem
    evens = Counter(_tick(it).answer for it in drawn)["even"]
    assert 0.3 <= evens / len(drawn) <= 0.7, evens


def test_the_closest_estimate_of_a_product_is_what_rounding_to_a_ten_gives():
    """V08: 52 × 9 is closest to 360, 450 or 540? The options are the larger number rounded to three tens in a row,
    each times the other; the right one is the larger number rounded to the nearest ten, and no other option is as
    near the product."""
    for it in _of("V08", 36) + _built(RS.closest_product, _product_pairs(200)):
        s = it.spec
        big, small = max(s["a"], s["b"]), min(s["a"], s["b"])
        exact = s["a"] * s["b"]
        options = s["options"]
        assert options == sorted(options) and len(options) == 3, s
        tens = [o // small for o in options]
        assert all(o % small == 0 and t % 10 == 0 for o, t in zip(options, tens, strict=True)), s
        assert [t - tens[0] for t in tens] == [0, 10, 20], s
        right = half_up(big, 10) * small
        tick = _tick(it)
        assert int(tick.answer) == right and tick.options == [str(o) for o in options], s
        near = sorted(abs(o - exact) for o in options)
        assert near[0] < near[1], s
        assert f"{s['a']} × {s['b']}" in it.stem and "closest" in it.stem, it.stem


def test_whether_a_product_can_be_right_is_judged_by_its_size():
    """V05: Riya says 23 × 4 = 812; could that be right? The claim is the product, or what a named slip gives when it
    has a different number of digits from the product (812 is 23 × 4 with its products side by side), one as often as
    the other; a claim the right size but wrong could only be judged by working it out."""
    drawn = _of("V05", 48)
    for it in drawn:
        s = it.spec
        exact, claimed = s["a"] * s["b"], s["claimed"]
        assert it.fmt == "possible_answer" and s["op"] == "×", s
        if claimed != exact:
            assert claimed in M.predict("×", s["a"], s["b"]).values(), s
            assert len(str(claimed)) != len(str(exact)), s
        assert _tick(it).answer == ("yes" if claimed == exact else "no"), s
        assert f"{s['a']} × {s['b']} = {claimed:,}" in it.stem, it.stem
    rights = sum(it.spec["claimed"] == it.spec["a"] * it.spec["b"] for it in drawn)
    assert 0.3 <= rights / len(drawn) <= 0.7, rights


# ------------------------------------------------------------------------------------------- levels and grades


def test_each_level_holds_its_cases_at_grade_4():
    """MD.ESTIMATE is Grade 4's at every level, as the document drafts it: no school objective names estimating a
    product, so the draft's grade stands (A6). It is on a rung of its own, counts for estimating and reasoning, and is
    in a topic of its own, untaught until an educator says so."""
    s = _estimate()
    assert s["rung_code"] == R and s["level_band"] == dict.fromkeys(LEVELS, "G4"), s["level_band"]
    assert {lv: d["check"]["cases"] for lv, d in s["difficulty"].items()} == LEVELS
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    assert rung["skill_codes"] == ["NUM.PV.03", "NUM.PRB.03"] and rung["band"] == "G4", rung
    topic = next(
        t
        for t in json.loads((SEED / "topics.json").read_text())["topics"]
        if "MD.ESTIMATE" in t["skill_sets"]
    )
    assert topic["skill_sets"] == ["MD.ESTIMATE"] and topic["taught"] is False, topic
    drafted = importlib.import_module("md_taxonomy")
    _, _, grades, levels, _ = next(x for x in drafted.SKILLS if x[0] == "MD.ESTIMATE")
    assert grades == "G4 G4 G4 G4" and levels == LEVELS, (grades, levels)


def test_the_right_option_is_first_in_the_middle_or_last_as_often_as_each():
    """Ticking one place every time scores a third, not more: the closest estimate of a product puts its right option
    first, in the middle or last about as often as each, and so does the closest hundred, now that each names the
    rounding a wrong option shows."""
    times = _built(RS.closest_product, _product_pairs(600))
    plus = _judged(RS.choose_estimate, "+", 300) + _judged(RS.choose_estimate, "-", 300)
    for made in (times, plus):
        places = Counter(it.spec["options"].index(int(_tick(it).answer)) for it in made)
        assert set(places) == {0, 1, 2}, places
        assert max(places.values()) / len(made) < 0.42, places


# ------------------------------------------------------------------------------------------- the mistakes named


def test_rounding_up_always_and_down_always_are_named():
    """A wrong option is named by the rounding that gives it: 52 × 9 answered 540 is 52 rounded up, as a child who always
    rounds up does (M_ROUNDS_AWAY_ZERO); 58 × 9 answered 450 is 58 rounded down, as a child who always rounds down does
    (M_ROUNDS_TOWARD_ZERO, new). The closest hundred names the same two for both numbers rounded up or down."""
    for it in _built(RS.closest_product, _product_pairs(300)):
        s = it.spec
        big, small = max(s["a"], s["b"]), min(s["a"], s["b"])
        tick = _tick(it)
        named = {code: value for code, value in tick.misconceptions.items()}
        assert named, s
        if big % 10 < 5:
            assert named.get("M_ROUNDS_AWAY_ZERO") == (big // 10 + 1) * 10 * small, (s, named)
        else:
            assert named.get("M_ROUNDS_TOWARD_ZERO") == big // 10 * 10 * small, (s, named)
        assert all(v in s["options"] and v != int(tick.answer) for v in named.values()), (s, named)
    for it in _judged(RS.choose_estimate, "+", 200) + _judged(RS.choose_estimate, "-", 200):
        s, tick = it.spec, _tick(it)
        up = -(-s["a"] // 100) * 100, -(-s["b"] // 100) * 100
        down = s["a"] // 100 * 100, s["b"] // 100 * 100
        sign = 1 if s["op"] == "+" else -1
        if "M_ROUNDS_AWAY_ZERO" in tick.misconceptions:
            assert tick.misconceptions["M_ROUNDS_AWAY_ZERO"] == up[0] + sign * up[1], s
        if "M_ROUNDS_TOWARD_ZERO" in tick.misconceptions:
            assert tick.misconceptions["M_ROUNDS_TOWARD_ZERO"] == down[0] + sign * down[1], s
        assert all(v in s["options"] and v != int(tick.answer) for v in tick.misconceptions.values()), s
    row = next(r for r in ROWS if r["code"] == "M_ROUNDS_TOWARD_ZERO")
    assert row["op"] == "any" and row["skill_code"] == "NUM.PV.03" and row["name"] and row["repair_hint"], row


def test_an_answer_accepted_without_its_size_and_a_right_answer_judged_wrong_are_named():
    """Ticking yes to a claim the wrong size accepts it without checking its size (M_IGNORES_SIZE); ticking no to the
    right answer judges a true claim false (M_REVERSES_CLAIM_TRUTH), a sum's as a product's: before, a right claim of a
    sum named nothing, half of what that kind asks."""
    for it in _of("V05", 24) + _judged(RS.possible_answer, "+", 100) + _judged(RS.possible_answer, "-", 100):
        s, tick = it.spec, _tick(it)
        right = s["claimed"] == M.compute(s["op"], s["a"], s["b"])
        assert tick.misconceptions == (
            {"M_REVERSES_CLAIM_TRUTH": "no"} if right else {"M_IGNORES_SIZE": "yes"}
        ), s


def test_every_judging_question_names_a_mistake_plus_and_minus_too():
    """No judging question is asked that cannot name the mistake a wrong answer shows: the closest hundred named one in
    16 draws of 100 and a right claim none; every name is a row of the vocabulary."""
    rows = {code for code, _ in VOCAB}
    made = [
        *_judged(RS.choose_estimate, "+", 150),
        *_judged(RS.choose_estimate, "-", 150),
        *_judged(RS.possible_answer, "+", 150),
        *_judged(RS.possible_answer, "-", 150),
        *_judged(RS.odd_even, "+", 150),
        *_judged(RS.odd_even, "-", 150),
        *_built(RS.closest_product, _product_pairs(150)),
        *_built(RS.possible_product, _product_pairs(150)),
        *_built(RS.parity_of_product, _product_pairs(150)),
    ]
    for it in made:
        named = {c for r in it.responses for c in r.misconceptions}
        assert named and named <= rows, (it.fmt, it.spec, named)


# ------------------------------------------------------------------------------------------- V06 and F08


def test_v06_and_f08_are_told_apart_by_their_numbers():
    """V06 and F08 are one kind of question, a product odd or even. F08 asks it of a table fact (6 × 7, multiples and
    factors, Grade 3), V06 of a product past the tables, without working (6 × 13, Grade 4): no question is both."""
    v06, f08 = CASES["V06"]["match"], CASES["F08"]["match"]
    assert v06["fact"] == "NO" and (v06["digits_max"], v06["digits_min"]) == (2, 1), v06
    assert f08["fact"] == "YES" and "shape" not in f08, f08
    for (a, b), want in {
        (6, 7): {"F08"},
        (7, 9): {"F08"},
        (6, 13): {"V06"},
        (17, 4): {"V06"},
        (23, 45): set(),
    }.items():
        measured = tags.derive(_parity_item(a, b))
        held = {c for c, m in (("V06", v06), ("F08", f08)) if taxonomy.matches(m, "odd_even", measured)}
        assert held == want, (a, b, held)


def _parity_item(a, b):
    """A product odd or even, as the kind builds it on these two numbers (drawn again until it is asked)."""
    for seed in range(50):
        try:
            return RS.parity_of_product(random.Random(seed), a, b, R, {})
        except RuntimeError:
            continue
    raise AssertionError((a, b))


def test_the_document_gives_the_closest_estimate_and_odd_or_even_their_numbers():
    """The drafted document is corrected at its source: the closest estimate's options are what rounding to a ten gives
    (52 × 9: 360, 450 or 540, where 400 and 500 were what no rounding gives), and V06 is asked past the tables
    (6 × 13 and 7 × 15), 7 × 9 being F08's table fact."""
    assert DOC["V08"]["example"] == "52 × 9 is closest to 360, 450 or 540?" and DOC["V08"]["answer"] == "450"
    assert DOC["V06"]["example"] == "6 × 13 and 7 × 15" and DOC["V06"]["answer"] == "even and odd"
    assert DOC["F08"]["example"] == "Is 6 × 7 even or odd?"


# ------------------------------------------------------------------------------------------- skills, scenarios, marking


def test_a_right_answer_counts_for_estimating_and_a_rounding_mistake_against_it():
    """A right closest estimate counts for estimating and for multiplication; a rounding mistake against estimating. A
    right odd or even counts for reasoning and multiplication, the parity rule backwards against reasoning; the exact
    answer's slips against the operation they are made in."""
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    closest = _built(RS.closest_product, [(52, 9)])[0]
    used = skills.used(closest.fmt, closest.spec, closest.stem, rung["skill_codes"], RULES)
    assert used == ["NUM.PV.03", "NUM.OPS.03"], used
    codes = ["M_ROUNDS_AWAY_ZERO", "M_ROUNDS_TOWARD_ZERO"]
    assert skills.charges(
        closest.fmt, closest.spec, closest.stem, used, codes, VOCAB, RULES
    ) == dict.fromkeys(codes, "NUM.PV.03")
    parity = _parity_item(6, 13)
    used = skills.used(parity.fmt, parity.spec, parity.stem, rung["skill_codes"], RULES)
    assert used == ["NUM.PRB.03", "NUM.OPS.03"], used
    assert skills.charges(parity.fmt, parity.spec, parity.stem, used, ["M_PARITY_RULE"], VOCAB, RULES) == {
        "M_PARITY_RULE": "NUM.PRB.03"
    }
    rounded = _of("V01", 4)[0]
    used = skills.used(rounded.fmt, rounded.spec, rounded.stem, rung["skill_codes"], RULES)
    assert skills.charges(
        rounded.fmt, rounded.spec, rounded.stem, used, ["M_MUL_NO_CARRY"], VOCAB, RULES
    ) == {"M_MUL_NO_CARRY": "NUM.OPS.03"}


def _every_level():
    return [it for level in LEVELS for _, it in _level(level, 4 * len(LEVELS[level]))]


def test_a_scenario_works_out_odd_or_even_and_the_closest_estimate():
    """The scenarios' own check works out every answer from the question as printed: an odd or even answer from its two
    numbers, a closest estimate as the option nearest the exact answer, a claim from its sum. Before, the first two
    were counted as nothing to work out; one changed tick is now found wrong."""
    made = [
        *_every_level(),
        *_judged(RS.choose_estimate, "+", 20),
        *_judged(RS.odd_even, "-", 20),
        *_built(RS.closest_product, _product_pairs(20)),
        *_built(RS.parity_of_product, _product_pairs(20)),
    ]
    for it in made:
        assert scenarios._answer_is_right(it) is True, (it.fmt, it.spec, [r.answer for r in it.responses])
        tick = next((r for r in it.responses if r.kind == "tick"), None)
        if tick is None:
            continue
        other = next(o for o in tick.options if o != tick.answer)
        bad = [dataclasses.replace(r, answer=other) if r is tick else r for r in it.responses]
        assert scenarios._answer_is_right(dataclasses.replace(it, responses=bad)) is False, it.spec


def _ticked(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_every_tick_is_marked_against_its_own_key():
    """A tick is marked against its own key, and a wrong one names the mistake its option shows."""
    for it in _every_level():
        for r in it.responses:
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _ticked(str(r.answer)))[0] == "correct", (it.spec, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _ticked(str(wrong)))
                assert status == "wrong" and code in codes, (it.spec, r.rid, code, wrong)


def test_every_mistake_the_estimates_name_is_a_row_and_on_md_estimates_list():
    """The estimates' mistakes are rows of the vocabulary and on MD.ESTIMATE's list; the rounding ones count against
    estimating."""
    rows = {code for code, _ in VOCAB}
    named = {
        c
        for level in LEVELS
        for _, it in _level(level, 12 * len(LEVELS[level]))
        for r in it.responses
        for c in r.misconceptions
    }
    assert named <= rows, named - rows
    assert named <= set(_estimate()["misconception_codes"]), named - set(_estimate()["misconception_codes"])
    for code in ("M_ROUNDS_AWAY_ZERO", "M_ROUNDS_TOWARD_ZERO", "M_PARITY_RULE", "M_IGNORES_SIZE"):
        assert code in named, code


def test_every_level_fills_each_case_as_often_as_it_asks():
    """A case is covered when the bank holds as many of it as its row asks (12 where it names none); each level, filled
    as the bank fills it, holds every case it lists that often, every question distinct."""
    for level, d in _estimate()["difficulty"].items():
        got = _level(level, d["min_items"])
        held = Counter(c for c, _ in got)
        assert len({it.item_id for _, it in got}) == len(got), level
        for c in d["check"]["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (level, c, held[c])
