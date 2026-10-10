"""MUL.MODELS: multiplication as the models a child meets first (goals/md2d1-multiplication-models.yaml).

Every question is drawn on its own level as the bank draws it, read back as measured (`tags.derive`), and its answer and
wrong answers worked here from its own numbers, not read back from the code that made it."""

import json
import pathlib
import random
import re
from collections import Counter

import pytest

from engine.assess import draw, render, stale, tags, taxonomy, verify, words
from engine.assess.pick import Sheet

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
MODELS = SETS.get("MUL.MODELS", {})
LEVEL_OF = {c: lv for lv, d in MODELS.get("difficulty", {}).items() for c in d["check"]["cases"]}


def _drawn(case, n=8, seed=3):
    """[question] of one case, drawn alone on the level MUL.MODELS lists it at, as the bank draws a level."""
    level = MODELS["difficulty"][LEVEL_OF[case]]["check"]
    match = taxonomy.within(CASES[case]["match"], level.get("within"))
    got = draw.level(random.Random(seed), {**level, "cases": [case]}, {case: match}, MODELS["rung_code"], n)
    assert len(got) == n, (case, len(got))
    for _, it in got:
        assert taxonomy.matches(match, it.fmt, tags.derive(it)), (case, it.spec)
    return [it for _, it in got]


def _named(right, predicted):
    """The mistakes a wrong answer names: a wrong answer that is the right one, or that two mistakes give, names
    neither for certain, so the first to give it keeps it."""
    out = {}
    for code, wrong in predicted:
        if wrong != right and wrong not in out.values():
            out[code] = wrong
    return out


def _groups(a, b):
    """`a` groups of `b`, worked wrong the three ways equal groups are: the two numbers added, one group, a group missed."""
    return _named(a * b, [("M_WRONG_OP", a + b), ("M_ONE_GROUP", b), ("M_GROUP_MISSED", (a - 1) * b)])


def _answers(it):
    return {r.rid: r for r in it.responses}


def _html(it):
    return render.render_item(Sheet("CS000000", "G2", "Easy", 1, "W1", [it]), it, 1)


def test_every_case_mul_models_lists_draws_on_its_level():
    """Easy holds skip counting and arrays, Medium the jumps, Hard the swap and the square, Advance the three stories;
    all Grade 2, as the drafted document sets them."""
    assert {lv: d["check"]["cases"] for lv, d in MODELS["difficulty"].items()} == {
        "Easy": ["G03", "G05"],
        "Medium": ["G04"],
        "Hard": ["G14", "TF17"],
        "Advance": ["B04", "B11", "B13"],
    }
    assert set(MODELS["level_band"].values()) == {"G2"}
    for case in LEVEL_OF:
        _drawn(case, n=4)


def test_skip_counting_prints_the_steps_before_its_box():
    """5, 10, 15, 20, □: `a` steps of `b`, every step but the last printed before the box, the step one of the
    tables the level counts as known. Writing the last step printed again is one group fewer."""
    known = MODELS["difficulty"]["Easy"]["check"]["known"]
    for it in _drawn("G03"):
        a, b = it.spec["a"], it.spec["b"]
        ans = _answers(it)["ans"]
        assert it.fmt == "skip_counting" and it.spec["method"] == "SKIP_COUNTING" and b in known and a >= 3
        assert ans.answer == str(a * b) and len(it.responses) == 1
        assert ", ".join(str(b * k) for k in range(1, a)) + ", " in _html(it)
        assert ans.misconceptions == _named(a * b, [("M_GROUP_MISSED", (a - 1) * b)])


def test_an_array_is_read_in_three_labelled_boxes():
    """3 rows of 5: how many rows, how many in each row, how many in all, as the sentence rows × in each row = in all.
    Labelled, so 3 and 5 are never read the wrong way round. The picture holds exactly rows × in-each-row dots."""
    for it in _drawn("G05"):
        a, b = it.spec["a"], it.spec["b"]
        r = _answers(it)
        assert (
            it.fmt == "equal_groups" and it.spec["shape"] == "ARRAY" and tags.derive(it)["method"] == "ARRAY"
        )
        assert (r["rows"].answer, r["each"].answer, r["ans"].answer) == (str(a), str(b), str(a * b))
        assert r["ans"].misconceptions == _groups(a, b)
        page = _html(it)
        assert len(re.findall(r'class="dot"', page)) == a * b
        assert re.search(r">rows<.*>×<.*>in each row<.*>=<.*>in all<", page)


def test_equal_jumps_from_zero_land_on_the_product():
    """4 jumps of 3 from 0 land on 12: the line is drawn with every jump from 0, no landing numbered, and the box asks
    where the last lands."""
    for it in _drawn("G04"):
        a, b = it.spec["a"], it.spec["b"]
        ans = _answers(it)["ans"]
        assert it.fmt == "number_line_jumps" and it.spec["op"] == "×" and it.spec["method"] == "NUMBER_LINE"
        assert ans.answer == str(a * b) and len(it.responses) == 1
        page = _html(it)
        assert len(re.findall(r'class="jump"', page)) == a
        assert f">{a * b}<" not in page
        assert ans.misconceptions == _groups(a, b)


def test_a_table_is_swapped_to_one_the_level_counts_as_known():
    """9 × 2 = 2 × 9 = □: the second number is one of the tables the level's own row counts as known, the first is
    not, and the swap is printed whole. A level that names no known tables cannot make it, and says so."""
    hard = MODELS["difficulty"]["Hard"]["check"]
    for it in _drawn("G14"):
        a, k = map(int, re.match(r"(\d+) × (\d+) = ", it.spec["text"]).groups())
        assert k in hard["known"] and a not in hard["known"]
        assert it.spec["text"] == f"{a} × {k} = {k} × {a} = □"
        ans = _answers(it)["ans"]
        assert ans.answer == str(a * k) and ans.misconceptions["M_WRONG_OP"] == a + k
    unknown = {key: v for key, v in hard.items() if key != "known"}
    with pytest.raises(ValueError, match="known"):
        draw.level(random.Random(1), {**unknown, "cases": ["G14"]}, {"G14": CASES["G14"]["match"]}, "R1", 1)


def test_a_cell_of_the_multiplication_square_is_found_from_its_row_and_column():
    """A part of the multiplication square, its rows and columns headed, one cell a box: every other cell printed as
    its row times its column, none of them the answer; the next row of the table, the cell beside it in its row or its
    column, is a mistake it names."""
    for it in _drawn("TF17"):
        a, b = it.spec["a"], it.spec["b"]
        ans = _answers(it)["ans"]
        assert it.fmt == "multiplication_square" and ans.answer == str(a * b) and len(it.responses) == 1
        assert a in it.spec["rows"] and b in it.spec["cols"]
        page = _html(it)
        for r in it.spec["rows"]:
            assert f"<th>{r}</th>" in page
            for c in it.spec["cols"]:
                assert (r, c) == (a, b) or f'<td class="p">{r * c}</td>' in page
        assert f'<td class="p">{a * b}</td>' not in page  # the answer is never printed
        assert ans.misconceptions["M_MUL_ROW_OUT"] in ((a - 1) * b, a * (b - 1))  # the cell beside it


def test_three_stories_multiply_an_array_twice_as_many_and_an_area():
    """An array, twice as many and area in squares, as stories. Twice as many is a story's own 2; reading it as
    two more is its named mistake, as reading three times as many as three more is. The same words arriving the other
    way into the bank (`verify.to_item`, a sentence checked) are the same question with the same mistakes."""
    shapes = {}
    for case in ("B04", "B11", "B13"):
        for it in _drawn(case, n=6):
            a, b = it.spec["a"], it.spec["b"]
            ans = _answers(it)["ans"]
            shapes.setdefault(it.spec["structure"], set()).add(b)
            assert it.fmt == "word_1step" and it.spec["op"] == "×" and ans.answer == str(a * b)
            if it.spec["structure"] == "TWICE_AS_MANY":
                assert b == 2 and ans.misconceptions["M_TIMES_AS_MORE"] == a + 2
                assert "M_WRONG_OP" not in ans.misconceptions
            checked = verify.to_item(
                {"format": "word_1step", "op": "×", "a": a, "b": b, "stem": it.stem, "missing": None}, it.rung
            )
            assert (checked.item_id, checked.responses[0].misconceptions) == (it.item_id, ans.misconceptions)
    assert set(shapes) == {"ARRAY", "TWICE_AS_MANY", "AREA"}
    made = []
    for seed in range(30):
        try:
            made.append(
                words.word_1step(
                    random.Random(seed), "R1", "Application", 1, structure="TIMES_AS_MANY_LARGER", op="×"
                )
            )
        except RuntimeError:
            continue  # 2 times as many as 2 is drawn again: read as two more, it would be right
    assert len(made) >= 20
    for it in made:
        a, b = it.spec["a"], it.spec["b"]
        assert a + b != a * b and _answers(it)["ans"].misconceptions["M_TIMES_AS_MORE"] == a + b


def test_a_filled_level_holds_each_of_its_cases_as_often_as_the_case_asks():
    """A case is covered when the bank holds as many of it as its row asks (12 where it names none, as `engine load`
    reads it); fewer is what `engine bank taxonomy` calls thin. Each level, filled as the bank fills it, holds every
    case it lists that often: twice as many takes a number to 20, where 1-digit numbers gave it only 7 questions."""
    for lv, d in MODELS["difficulty"].items():
        check = d["check"]
        matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
        held = Counter(
            c for c, _ in draw.level(random.Random(5), check, matches, MODELS["rung_code"], d["min_items"])
        )
        for c in check["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (lv, c, held[c])


def test_every_mistake_its_questions_name_is_on_its_list_and_is_a_row():
    """What a question names a wrong answer is a mistake the skill set lists (so the curriculum shows it) and a row of
    the vocabulary (so the marker and the reports can say it in words)."""
    rows = {m["code"] for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]}
    named = set()
    for d in MODELS["difficulty"].values():
        check = d["check"]
        matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
        for _, it in draw.level(random.Random(2), check, matches, MODELS["rung_code"], d["min_items"]):
            named |= {c for r in it.responses for c in r.misconceptions}
    assert named <= set(MODELS["misconception_codes"]) and named <= rows, named - set(
        MODELS["misconception_codes"]
    )


def _story(structure, seed=1):
    for k in range(seed, seed + 50):
        try:
            return words.word_1step(
                random.Random(k), "R1", "Application", 1, structure=structure, op="×"
            ).to_dict()
        except RuntimeError:
            continue  # its misreading would be its answer: drawn again
    raise AssertionError(structure)


def test_a_times_as_many_story_keyed_before_its_mistake_had_a_name_leaves_the_bank():
    """A "times as many" story stored when adding its two numbers was named the wrong operation is keyed by a rule
    since corrected: it leaves the bank and is drawn again, as a straight sum keyed by an old predictor does, so no
    printed paper changes under it. So does one whose numbers added are its answer. Every template of one shape names
    the same mistake, so a story's shape alone says which."""
    for shape, code in words.wrong_op_by_shape().items():
        assert {t.get("wrong_op_as") for t in words.templates("word_1step", structure=shape)} == {code}
    today = _story("TIMES_AS_MANY_LARGER")
    assert stale.key_problems("word_1step", today["spec"], today["responses"]) == []
    before = {**today, "responses": [dict(today["responses"][0])]}
    mis = before["responses"][0]["misconceptions"]
    before["responses"][0]["misconceptions"] = {
        ("M_WRONG_OP" if c == "M_TIMES_AS_MORE" else c): v for c, v in mis.items()
    }
    corrected = ["keyed by a mistake rule since corrected: M_WRONG_OP"]
    assert stale.key_problems("word_1step", before["spec"], before["responses"]) == corrected
    two = {**today["spec"], "a": 2, "b": 2}
    assert stale.key_problems("word_1step", two, today["responses"]) == corrected
    groups = _story("EQUAL_GROUPS")  # adding is the wrong operation there, and stays so named
    assert "M_WRONG_OP" in groups["responses"][0]["misconceptions"]
    assert stale.key_problems("word_1step", groups["spec"], groups["responses"]) == []


def test_every_model_question_prints_a_box_for_every_answer():
    """Each answer has its own box on the page, so the reader reads it and marking marks it against its own key."""
    assert sorted(LEVEL_OF) == ["B04", "B11", "B13", "G03", "G04", "G05", "G14", "TF17"]
    for case in LEVEL_OF:
        for it in _drawn(case, n=3):
            page = _html(it)
            for r in it.responses:
                assert f'data-resp="{it.item_id}|{r.rid}"' in page, (case, r.rid)


def test_every_model_answer_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of one question of every case, printed through Chromium as a paper is: the key's geometry holds each
    answer's boxes, as many as its right answer has digits, so the reader finds every one (the array's three too)."""
    its = [it for case in sorted(LEVEL_OF) for it in _drawn(case, n=1)]
    key = render.render_sheet(Sheet("CS00D2D1", "G2", "Easy", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        for r in it.responses:
            assert boxes[(it.item_id, r.rid)] == len(r.answer), (it.fmt, r.rid)
