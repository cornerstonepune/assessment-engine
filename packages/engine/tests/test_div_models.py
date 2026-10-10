"""DIV.GROUPS: division as the models a child meets first (goals/md3c-division-models.yaml).

Every question is drawn on its own level as the bank draws it, read back as measured (`tags.derive`), and its answer and
wrong answers worked here from its own numbers, not read back from the code that made it."""

import json
import pathlib
import random
import re
from collections import Counter

import pytest

from engine.assess import bands, draw, render, tags, taxonomy, words
from engine.assess import div_mistakes as DM
from engine.assess import operations as O
from engine.assess.pick import Sheet
from engine.w1_bank import labels

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
ROWS = json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
RUNGS = {r["code"]: r for r in json.loads((SEED / "rungs.json").read_text())["rungs"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
TOPICS = {t["code"]: t for t in json.loads((SEED / "topics.json").read_text())["topics"]}
MODELS = SETS.get("DIV.GROUPS", {})
LEVEL_OF = {c: lv for lv, d in MODELS.get("difficulty", {}).items() for c in d["check"]["cases"]}
STORIES = {"B02": "SHARING", "B03": "GROUPING", "B05": "ARRAY", "B24": "GROUPING_BY_EACH"}


def _drawn(case, n=8, seed=3):
    """[question] of one case, drawn alone on the level DIV.GROUPS lists it at, as the bank draws a level."""
    level = MODELS["difficulty"][LEVEL_OF[case]]["check"]
    match = taxonomy.within(CASES[case]["match"], level.get("within"))
    got = draw.level(random.Random(seed), {**level, "cases": [case]}, {case: match}, MODELS["rung_code"], n)
    assert len(got) == n, (case, len(got))
    for _, it in got:
        assert taxonomy.matches(match, it.fmt, tags.derive(it)), (case, it.spec)
    return [it for _, it in got]


def _named(right, predicted):
    """The mistakes a wrong answer names: a wrong answer that is the right one, or that an earlier mistake gives,
    names no further mistake, so the first to give it keeps it."""
    out = {}
    for code, wrong in predicted:
        if wrong != right and wrong not in out.values():
            out[code] = wrong
    return out


def _pictured(a, b):
    """a dots shared into b rings, or ringed in groups of b, worked wrong the four ways: multiplied, one group taken
    away, all of them counted, and the number the question gives written for the one it asks."""
    q = a // b
    return _named(
        q,
        [
            ("M_WRONG_OP", a * b),
            ("M_DIV_SUBTRACTED", a - b),
            ("M_DIV_ALL_COUNTED", a),
            ("M_DIV_GROUPS_FOR_SIZE", b),
        ],
    )


def _answers(it):
    return {r.rid: r for r in it.responses}


def _html(it):
    return render.render_item(Sheet("CS000000", "G2", "Easy", 1, "W1", [it]), it, 1)


def _exact(it):
    a, b = it.spec["a"], it.spec["b"]
    assert it.spec["op"] == "÷" and b >= 2 and a % b == 0 and a // b >= 2, it.spec
    return a, b, a // b


def test_every_case_div_groups_lists_draws_on_its_level():
    """Easy holds sharing and grouping, Medium repeated subtraction and the array, Hard the jumps back, Advance the
    four stories; all Grade 2, as the drafted document sets them. Its own rung and its own topic, untaught; no level
    says `within`, so placing never holds one of its questions in a calculation skill too (ADR 0054)."""
    assert {lv: d["check"]["cases"] for lv, d in MODELS["difficulty"].items()} == {
        "Easy": ["G15", "G16"],
        "Medium": ["G17", "G19"],
        "Hard": ["G18"],
        "Advance": ["B02", "B03", "B05", "B24"],
    }
    assert set(MODELS["level_band"].values()) == {"G2"}
    assert not any("within" in d["check"] for d in MODELS["difficulty"].values())
    rung = RUNGS[MODELS["rung_code"]]
    assert rung["band"] == "G2" and rung["skill_codes"] == ["NUM.OPS.04"]
    homes = [t for t in TOPICS.values() if "DIV.GROUPS" in t["skill_sets"]]
    assert len(homes) == 1 and homes[0]["skill_sets"] == ["DIV.GROUPS"] and homes[0]["taught"] is False
    for case in LEVEL_OF:
        _drawn(case, n=4)


def test_dots_are_shared_equally_into_rings():
    """12 dots into 3 rings: the dots loose, the rings empty, the box how many go in each. The picture holds exactly
    the dots and the rings the numbers say. A kind handed an operation it does not make refuses in a sentence."""
    for it in _drawn("G15"):
        a, b, q = _exact(it)
        ans = _answers(it)["ans"]
        assert it.fmt == "equal_groups" and it.spec["method"] == "SHARING" and len(it.responses) == 1
        assert ans.answer == str(q) and ans.misconceptions == _pictured(a, b)
        page = _html(it)
        assert len(re.findall(r'class="dot"', page)) == a and len(re.findall(r'class="group"', page)) == b
        assert ">in each ring<" in page
    with pytest.raises(O.CannotMake):
        bands.native_item(
            "equal_groups", {"op": "-", "groups": [2, 3], "size": [2, 3]}, random.Random(1), "R1", ""
        )
    with pytest.raises(ValueError, match="shared, grouped or an array"):  # a rule it cannot read, said aloud
        bands.native_item("equal_groups", {"op": "÷", "method": "PICTURE"}, random.Random(1), "R1", "")


def test_dots_are_ringed_in_equal_groups():
    """12 dots in groups of 4: the dots loose and no ring drawn, for the child rings them; the box how many groups."""
    for it in _drawn("G16"):
        a, b, q = _exact(it)
        ans = _answers(it)["ans"]
        assert it.fmt == "equal_groups" and it.spec["method"] == "GROUPING" and len(it.responses) == 1
        assert ans.answer == str(q) and ans.misconceptions == _pictured(a, b)
        page = _html(it)
        assert len(re.findall(r'class="dot"', page)) == a and 'class="group"' not in page
        assert ">groups<" in page


def test_a_number_taken_away_again_and_again_to_zero_counts_its_groups():
    """15 − 3 − 3 − 3 − 3 − 3 = 0, how many 3s: a kind of its own (the draft filed it as a straight sum), printed whole
    from its own numbers, a 3 for every group. Counting the 15 as one more, or writing the 3, are the mistakes it
    names."""
    for it in _drawn("G17"):
        a, b, q = _exact(it)
        ans = _answers(it)["ans"]
        assert it.fmt == "repeated_subtraction" and it.spec["method"] == "REPEATED_SUBTRACTION"
        assert ans.answer == str(q) and len(it.responses) == 1
        assert ans.misconceptions == _named(q, [("M_DIV_START_COUNTED", q + 1), ("M_DIV_GROUPS_FOR_SIZE", b)])
        page = _html(it)
        assert " − ".join([str(a)] + [str(b)] * q) + " = 0" in page
        # the subtraction is drawn from its numbers, never typed into the sentence
        assert str(b) in it.stem and "−" not in it.stem


def test_an_array_divided_is_read_in_three_labelled_boxes():
    """20 dots in 4 equal rows: how many in all, how many rows, how many in each row, as the sentence in all ÷ rows =
    in each row. Labelled, so 4 and 5 are never read the wrong way round. The picture holds rows × in-each-row dots."""
    for it in _drawn("G19"):
        a, b, q = _exact(it)
        r = _answers(it)
        assert it.fmt == "equal_groups" and it.spec["method"] == "ARRAY"
        assert (r["all"].answer, r["rows"].answer, r["ans"].answer) == (str(a), str(b), str(q))
        assert r["ans"].misconceptions == _named(
            q, [("M_WRONG_OP", a * b), ("M_DIV_SUBTRACTED", a - b), ("M_DIV_GROUPS_FOR_SIZE", b)]
        )
        page = _html(it)
        assert len(re.findall(r'class="dot"', page)) == a
        assert re.search(r">in all<.*>÷<.*>rows<.*>=<.*>in each row<", page, re.S)


def test_jumps_back_on_a_number_line_to_zero_are_counted():
    """From 20, jumps of 4 back to 0: a line from 0 to 20 with a mark at every number, its start numbered, and no jump
    drawn, for the child draws them. Writing where the first jump lands, counting the start as a jump, or writing the
    jump are the mistakes it names."""
    for it in _drawn("G18"):
        a, b, q = _exact(it)
        ans = _answers(it)["ans"]
        assert it.fmt == "number_line_jumps" and it.spec["method"] == "NUMBER_LINE" and len(it.responses) == 1
        assert ans.answer == str(q)
        assert ans.misconceptions == _named(
            q, [("M_DIV_SUBTRACTED", a - b), ("M_DIV_START_COUNTED", q + 1), ("M_DIV_GROUPS_FOR_SIZE", b)]
        )
        page = _html(it)
        assert 'class="jump"' not in page and len(re.findall(r'class="mark"', page)) == a + 1
        assert f">{a}<" in page and ">0<" in page and ">jumps<" in page


def test_four_stories_divide_a_table_read_backwards():
    """Sharing, grouping, an array and "each", as stories of a table to 10 read backwards (24 laddoos on 4 plates):
    each its shape's own words, a template row, two rows at least for each shape, nothing left over. The answer is the
    division's, and its wrong answers the division's own."""
    for case, shape in STORIES.items():
        rows = [t for t in words.templates("word_1step", "÷", shape) if not t.get("remainder_use")]
        assert len(rows) >= 2, (shape, rows)
        for it in _drawn(case, n=12):
            a, b, q = _exact(it)
            ans = _answers(it)["ans"]
            assert it.fmt == "word_1step" and it.spec["structure"] == shape and set(_answers(it)) == {"ans"}
            assert b <= 10 and q <= 10, it.spec
            assert words.template_of(it.stem) in rows, it.stem
            assert ans.answer == str(q)
            want = {k: v for k, v in DM.in_box(a, b, 0).items() if v != q and v >= 0}
            if shape == "GROUPING_BY_EACH":
                want = {("M_KEYWORD_OVERGENERALISED" if k == "M_WRONG_OP" else k): v for k, v in want.items()}
            assert ans.misconceptions == want, (case, it.spec, ans.misconceptions)


def test_each_in_a_story_that_divides_is_its_own_mistake():
    """30 stickers, 5 for each child, answered 150: multiplying because the story says "each" is its own mistake on the
    stories whose "each" is the trap, with a row of its own for division. A grouping story without that word names
    multiplying the wrong operation. Every template of one shape names the same mistake."""
    assert words.wrong_op_by_shape()["GROUPING_BY_EACH"] == "M_KEYWORD_OVERGENERALISED"
    for shape, code in words.wrong_op_by_shape().items():
        assert {t.get("wrong_op_as") for t in words.templates("word_1step", structure=shape)} == {code}
    each = [r for r in ROWS if (r["code"], r["op"]) == ("M_KEYWORD_OVERGENERALISED", "÷")]
    assert len(each) == 1 and "each" in each[0]["name"] and each[0]["repair_hint"].strip()
    for t in words.templates("word_1step", "÷", "GROUPING_BY_EACH"):
        assert re.search(r"\beach\b", t["text"]), t["text"]
    for t in words.templates("word_1step", "÷", "GROUPING"):
        if not t.get("remainder_use"):
            assert not re.search(r"\beach\b", t["text"]), t["text"]
    for it in _drawn("B03", n=4):
        assert _answers(it)["ans"].misconceptions["M_WRONG_OP"] == it.spec["a"] * it.spec["b"]


def test_every_mistake_its_questions_name_is_on_its_list_and_is_a_row():
    """What a question names a wrong answer is a mistake the skill set lists (so the curriculum shows it) and a row of
    the vocabulary for division (so the marker and the reports can say it in words). The three the models add are
    rows of their own, each with a name and what the school does about it."""
    rows = {(m["code"], m["op"]) for m in ROWS if m["name"].strip() and m["repair_hint"].strip()}
    named = set()
    for d in MODELS["difficulty"].values():
        check = d["check"]
        matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
        for _, it in draw.level(random.Random(2), check, matches, MODELS["rung_code"], d["min_items"]):
            named |= {c for r in it.responses for c in r.misconceptions}
    assert named <= set(MODELS["misconception_codes"]), named - set(MODELS["misconception_codes"])
    assert all((c, "÷") in rows or (c, "any") in rows for c in named), {
        c for c in named if (c, "÷") not in rows and (c, "any") not in rows
    }
    assert {"M_DIV_ALL_COUNTED", "M_DIV_GROUPS_FOR_SIZE", "M_DIV_START_COUNTED"} <= named
    assert {(c, "÷") for c in ("M_DIV_ALL_COUNTED", "M_DIV_GROUPS_FOR_SIZE", "M_DIV_START_COUNTED")} <= rows


def test_a_right_answer_counts_for_division_alone():
    """A question of division's models uses division, and a story a word problem too; never multiplication or addition,
    which an equal-groups question of multiplication uses (Grade 1's groups added again). Every mistake it names
    charges a skill it uses."""
    rs = {name: CONFIG[key] for name, key in labels.RULE_KEYS.items()}
    vocab = {(m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code")) for m in ROWS}
    own = RUNGS[MODELS["rung_code"]]["skill_codes"]
    for case in LEVEL_OF:
        for it in _drawn(case, n=4):
            used, charged = labels.measure(
                it.fmt, it.spec, it.stem, [vars(r) for r in it.responses], own, rs, vocab
            )
            assert used[0] == "NUM.OPS.04" and not {"NUM.OPS.03", "NUM.OPS.01"} & set(used), (case, used)
            assert set(charged.values()) <= set(used), (case, charged)
    times = SETS["MUL.MODELS"]
    level = times["difficulty"]["Easy"]["check"]
    for _, it in draw.level(
        random.Random(1), {**level, "cases": ["G05"]}, {"G05": CASES["G05"]["match"]}, "R41", 2
    ):
        used, _ = labels.measure(it.fmt, it.spec, it.stem, [], RUNGS["R41"]["skill_codes"], rs, vocab)
        assert {"NUM.OPS.03", "NUM.OPS.01"} <= set(used), used


def test_a_filled_level_holds_each_of_its_cases_as_often_as_the_case_asks():
    """A case is covered when the bank holds as many of it as its row asks (12 where it names none); each level, filled
    as the bank fills it, holds every case it lists that often."""
    for lv, d in MODELS["difficulty"].items():
        check = d["check"]
        matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
        held = Counter(
            c for c, _ in draw.level(random.Random(5), check, matches, MODELS["rung_code"], d["min_items"])
        )
        for c in check["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (lv, c, held[c])


def test_every_model_question_prints_a_box_for_every_answer():
    """Each answer has its own box on the page, so the reader reads it and marking marks it against its own key."""
    assert sorted(LEVEL_OF) == ["B02", "B03", "B05", "B24", "G15", "G16", "G17", "G18", "G19"]
    for case in LEVEL_OF:
        for it in _drawn(case, n=3):
            page = _html(it)
            for r in it.responses:
                assert f'data-resp="{it.item_id}|{r.rid}"' in page, (case, r.rid)


def test_every_model_answer_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of one question of every case, printed through Chromium as a paper is: the key's geometry holds each
    answer's boxes, as many as its right answer has digits, so the reader finds every one (the array's three too)."""
    its = [it for case in sorted(LEVEL_OF) for it in _drawn(case, n=1)]
    assert len(its) == 9
    key = render.render_sheet(Sheet("CS00D3C0", "G2", "Easy", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        for r in it.responses:
            assert boxes[(it.item_id, r.rid)] == len(r.answer), (it.fmt, r.rid)
