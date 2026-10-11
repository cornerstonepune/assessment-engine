"""Mental multiplication and division, each method worked the way it is named (goals/md4a-mental-methods.yaml).

MD.MENTAL asks a child to work a product or a quotient by the method the question names, a box for every step and one
for the answer, each step printed as the sum it works out (13 × 8 as 13 × 2, 13 × 4, 13 × 8). Every key is worked out
here from the sum printed beside its box, and every mistake from the method, never read back from the code that made
it."""

import importlib
import json
import pathlib
import random
import re
import sys
from collections import Counter

import pytest

from engine.assess import draw, render, skills, tags, taxonomy
from engine.assess import mental as MN
from engine.assess import operations as O
from engine.assess.pick import Sheet
from engine.w3_read import marking

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
VOCAB = {
    (m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code"))
    for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
DOC = {
    c["code"]: c for c in json.loads((ROOT / "docs/design/multiplication-division-cases.json").read_text())
}
LEVELS = {
    "Easy": ["G06", "G25"],
    "Medium": ["H10", "H01", "H04", "H08"],
    "Hard": ["H02", "H03", "H05", "H07"],
    "Advance": ["H06", "H09"],
}
R = "R47"
if str(ROOT / "research") not in sys.path:
    sys.path.insert(0, str(ROOT / "research"))
SUM = re.compile(r"^(\d+) ([×÷]) (\d+) =$")  # a step printed as the sum it works out


def _mental():
    return SETS["MD.MENTAL"]


def _drawn(level, n, cases=None, seed=3):
    """[(case, question)] of one MD.MENTAL level, drawn as the bank draws it."""
    check = _mental()["difficulty"][level]["check"] | ({"cases": cases} if cases else {})
    matches = {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in check["cases"]}
    got = draw.level(random.Random(seed), check, matches, _mental()["rung_code"], n)
    assert len(got) == n, (level, cases, len(got))
    return got


def _steps(it):
    """Every box in print order: the sum printed beside it, and its key."""
    return [(r.label, r.answer) for r in it.responses]


def _worked(label):
    """The number a printed sum works out to, computed here: "13 × 4 =" is 52, "96 ÷ 2 =" is 48."""
    m = SUM.match(label)
    assert m, label
    a, op, b = int(m[1]), m[2], int(m[3])
    if op == "÷":
        assert a % b == 0, label  # a mental method's steps divide exactly
        return a // b
    return a * b


def _answer(it):
    return it.responses[-1]


def _named(it, code):
    return _answer(it).misconceptions.get(code)


# ------------------------------------------------------------------------------- each method worked here


def test_doubling_doubles_and_doubles_again():
    """14 × 4: double 14, then double again (G06). × 2 is one double; × 8 by doubling is H05's, not doubling's."""
    it = MN.make("DOUBLING", 14, 4, R)
    assert it.fmt == "efficient_method" and it.spec == {"a": 14, "b": 4, "op": "×", "method": "DOUBLING"}
    assert _steps(it) == [("14 × 2 =", "28"), ("14 × 4 =", "56")]
    assert "double" in it.stem.lower()
    assert _steps(MN.make("DOUBLING", 34, 2, R)) == [("34 × 2 =", "68")]
    for b in (3, 8):
        with pytest.raises(O.CannotMake):
            MN.make("DOUBLING", 14, b, R)


def test_halving_halves_and_halves_again():
    """96 ÷ 4: halve 96, then halve again (G25). A number that does not halve twice into whole numbers is refused."""
    it = MN.make("HALVING", 96, 4, R)
    assert it.fmt == "efficient_method" and it.spec == {"a": 96, "b": 4, "op": "÷", "method": "HALVING"}
    assert _steps(it) == [("96 ÷ 2 =", "48"), ("96 ÷ 4 =", "24")]
    assert "halve" in it.stem.lower()
    assert _steps(MN.make("HALVING", 74, 2, R)) == [("74 ÷ 2 =", "37")]
    for a, b in ((98, 4), (75, 2), (96, 3)):
        with pytest.raises(O.CannotMake):
            MN.make("HALVING", a, b, R)


def test_times_eight_doubles_three_times():
    """13 × 8: 26, 52, 104 (H05). It names its strategy, never doubling's method, so it is H05's case alone."""
    it = MN.make("DOUBLE_THREE_TIMES", 13, 8, R)
    assert _steps(it) == [("13 × 2 =", "26"), ("13 × 4 =", "52"), ("13 × 8 =", "104")]
    assert it.spec["strategy"] == "DOUBLE_THREE_TIMES" and "method" not in it.spec
    assert taxonomy.matches(CASES["H05"]["match"], it.fmt, tags.derive(it))
    assert not taxonomy.matches(CASES["G06"]["match"], it.fmt, tags.derive(it))


def test_times_nine_is_ten_groups_less_one_and_times_eleven_ten_groups_and_one_more():
    """23 × 9: 230, then one 23 taken away (H02); 14 × 11: 140, then one more 14 (H03)."""
    nine = MN.make("TIMES_TEN_LESS_A_GROUP", 23, 9, R)
    assert _steps(nine) == [("23 × 10 =", "230"), ("23 × 9 =", "207")]
    assert "take away" in nine.stem.lower()
    eleven = MN.make("TIMES_TEN_AND_A_GROUP", 14, 11, R)
    assert _steps(eleven) == [("14 × 10 =", "140"), ("14 × 11 =", "154")]
    assert "add" in eleven.stem.lower()
    with pytest.raises(O.CannotMake):
        MN.make("TIMES_TEN_LESS_A_GROUP", 23, 8, R)


def test_double_one_and_halve_the_other():
    """16 × 5 = 8 × 10 and 35 × 4 = 70 × 2 (H04): the even number halved, the other doubled to a round one, each a box
    in the order the numbers are written, then the answer. Numbers that give no round double are refused."""
    assert _steps(MN.make("DOUBLE_ONE_HALVE_THE_OTHER", 16, 5, R)) == [
        ("16 ÷ 2 =", "8"),
        ("5 × 2 =", "10"),
        ("16 × 5 =", "80"),
    ]
    assert _steps(MN.make("DOUBLE_ONE_HALVE_THE_OTHER", 35, 4, R)) == [
        ("35 × 2 =", "70"),
        ("4 ÷ 2 =", "2"),
        ("35 × 4 =", "140"),
    ]
    for a, b in ((15, 7), (13, 6)):
        with pytest.raises(O.CannotMake):
            MN.make("DOUBLE_ONE_HALVE_THE_OTHER", a, b, R)


def test_times_twenty_five_is_a_hundred_groups_divided_by_four():
    """24 × 25: 2400, then divided by 4 (H06)."""
    it = MN.make("TIMES_HUNDRED_THEN_QUARTER", 24, 25, R)
    assert _steps(it) == [("24 × 100 =", "2400"), ("24 × 25 =", "600")]
    assert "divide" in it.stem.lower()


def test_the_five_built_shortcuts_draw_on_md_mentals_own_numbers():
    """× 5 as × 10 then halved, a number near a round one, a fact from a known fact, a fact scaled by ten and ÷ 5 as
    ÷ 10 then doubled draw on MD.MENTAL's levels, each a question of its case, every step's key the sum beside it."""
    for level, cases in LEVELS.items():
        for case in cases:
            if case in ("G06", "G25", "H02", "H03", "H04", "H05", "H06"):
                continue
            for c, it in _drawn(level, 4, cases=[case]):
                assert c == case and taxonomy.matches(CASES[case]["match"], it.fmt, tags.derive(it)), (
                    case,
                    it.spec,
                )
                for r in it.responses:
                    if SUM.match(r.label or ""):
                        assert r.answer == str(_worked(r.label)), (case, r.label, r.answer)


def test_each_level_holds_its_methods_at_the_grade_the_schools_objectives_give():
    """Easy at Grade 2 doubles and halves a 2-digit number (LO-G2-0496, LO-G2-0498); Medium and Hard are Grade 3's,
    Advance Grade 4's. Every question a level draws is one of its cases."""
    s = _mental()
    assert {lv: d["check"]["cases"] for lv, d in s["difficulty"].items()} == LEVELS
    assert s["level_band"] == {"Easy": "G2", "Medium": "G3", "Hard": "G3", "Advance": "G4"}
    for _, it in _drawn("Easy", 16):
        assert len(str(it.spec["a"])) == 2 and it.spec["b"] in (2, 4), it.spec


# ------------------------------------------------------------------------------- the mistakes


def test_stopping_a_step_short_is_named():
    """The answer box names the step before it, written as the answer: 14 × 4 doubled once, 28; 13 × 8 doubled twice,
    52; 96 ÷ 4 halved once, 48; 23 × 9 and 14 × 11 never put right, 230 and 140; 24 × 25 never divided by 4, 2400. The
    built shortcuts too: 46 × 5 never halved, 240 ÷ 5 never doubled, 19 × 6 never put right. One wrong answer names
    one mistake: 14 × 11 answered 140 is a step short here, not the table's row out."""
    for (method, a, b), short in (
        (("DOUBLING", 14, 4), 28),
        (("DOUBLE_THREE_TIMES", 13, 8), 52),
        (("HALVING", 96, 4), 48),
        (("TIMES_TEN_LESS_A_GROUP", 23, 9), 230),
        (("TIMES_TEN_AND_A_GROUP", 14, 11), 140),
        (("TIMES_HUNDRED_THEN_QUARTER", 24, 25), 2400),
    ):
        it = MN.make(method, a, b, R)
        assert _named(it, "M_MENTAL_STOPS_SHORT") == short, method
        assert [c for c, v in _answer(it).misconceptions.items() if v == short] == ["M_MENTAL_STOPS_SHORT"], (
            method
        )
    for level, case, short in (
        ("Medium", "H01", lambda a, b: a * 10),
        ("Advance", "H09", lambda a, b: a // 10),
        ("Hard", "H07", lambda a, b: (a + 5) // 10 * 10 * b),
    ):
        for _, it in _drawn(level, 6, cases=[case]):
            assert _named(it, "M_MENTAL_STOPS_SHORT") == short(it.spec["a"], it.spec["b"]), (case, it.spec)


def test_putting_the_answer_right_the_wrong_way_is_named():
    """23 × 9 as 230 + 23 = 253; 14 × 11 as 140 − 14 = 126; 19 × 6 from 20 × 6 as 120 + 6 = 126."""
    assert _named(MN.make("TIMES_TEN_LESS_A_GROUP", 23, 9, R), "M_MENTAL_WRONG_WAY") == 253
    assert _named(MN.make("TIMES_TEN_AND_A_GROUP", 14, 11, R), "M_MENTAL_WRONG_WAY") == 126
    for _, it in _drawn("Hard", 6, cases=["H07"]):
        a, b = it.spec["a"], it.spec["b"]
        r = (a + 5) // 10 * 10
        assert _named(it, "M_MENTAL_WRONG_WAY") == 2 * r * b - a * b, it.spec


def test_one_taken_away_or_added_for_a_group_is_named():
    """23 × 9 as 230 − 1 = 229; 14 × 11 as 140 + 1 = 141; 19 × 6 as 120 − 1 = 119, and 21 × 6 as 120 + 1 = 121."""
    assert _named(MN.make("TIMES_TEN_LESS_A_GROUP", 23, 9, R), "M_MENTAL_ONE_NOT_GROUP") == 229
    assert _named(MN.make("TIMES_TEN_AND_A_GROUP", 14, 11, R), "M_MENTAL_ONE_NOT_GROUP") == 141
    for _, it in _drawn("Hard", 6, cases=["H07"]):
        a, b = it.spec["a"], it.spec["b"]
        r = (a + 5) // 10 * 10
        assert _named(it, "M_MENTAL_ONE_NOT_GROUP") == r * b + (1 if a > r else -1), it.spec


def test_halving_each_digit_is_the_exchange_lost_already_a_row():
    """74 ÷ 2 halved digit by digit is 32: the ten left over from 7 tens never exchanged, which short division already
    names. The halving box names it; a number whose digits all halve has nothing to lose."""
    assert MN.make("HALVING", 74, 2, R).responses[0].misconceptions["M_DIV_EXCHANGE_LOST"] == 32
    assert MN.make("HALVING", 96, 4, R).responses[0].misconceptions["M_DIV_EXCHANGE_LOST"] == 43
    assert "M_DIV_EXCHANGE_LOST" not in MN.make("HALVING", 84, 2, R).responses[0].misconceptions
    assert {code for code, _ in VOCAB} >= {"M_DIV_EXCHANGE_LOST"}
    assert not any(code.startswith("M_HALVES") for code, _ in VOCAB)


def test_doubling_both_numbers_is_named():
    """16 × 5 worked as 32 × 10 = 320, and 35 × 4 as 70 × 8 = 560: both numbers doubled, four times the answer."""
    assert _named(MN.make("DOUBLE_ONE_HALVE_THE_OTHER", 16, 5, R), "M_MENTAL_DOUBLED_BOTH") == 320
    assert _named(MN.make("DOUBLE_ONE_HALVE_THE_OTHER", 35, 4, R), "M_MENTAL_DOUBLED_BOTH") == 560


# ------------------------------------------------------------------------------- the document, the skills


def test_the_document_gives_each_method_the_grade_the_schools_objectives_give():
    """The drafted document is corrected at its source: halving is Grade 2's with doubling (LO-G2-0498); a fact scaled
    by ten waits for Grade 3, as multiplying by a multiple of ten does; ÷ 5 as ÷ 10 then doubled for Grade 4, as
    dividing by 10 does; doubling is × 2 and × 4, since × 8 by doubling is H05's own case."""
    drafted = importlib.import_module("md_taxonomy")  # the drafted document, as Achal reads it
    code, _, grades, levels, _ = next(s for s in drafted.SKILLS if s[0] == "MD.MENTAL")
    assert grades == "G2 G3 G3 G4" and levels == LEVELS, (code, grades, levels)
    assert DOC["G06"]["label"] == "Doubling (×2, ×4 = double double)"
    registry = json.loads((SEED / "registry.json").read_text())["learning_objectives"]
    assert (
        next(lo for lo in registry if lo["code"] == "LO-G2-0498")["title"]
        == "Apply doubling and halving strategies"
    )


def test_a_right_answer_counts_for_mental_maths_and_the_operation_and_a_method_mistake_for_mental_maths():
    """A right answer counts for mental maths and for the operation the question works out (division for halving); a
    method's own mistake counts against mental maths; a slip in a step's sum against that sum's operation."""
    rung = next(r for r in json.loads((SEED / "rungs.json").read_text())["rungs"] if r["code"] == R)
    nine = MN.make("TIMES_TEN_LESS_A_GROUP", 23, 9, R)
    used = skills.used(nine.fmt, nine.spec, nine.stem, rung["skill_codes"], RULES)
    assert set(used) == {"NUM.OPS.05", "NUM.OPS.03", "NUM.PRB.03"}
    half = MN.make("HALVING", 96, 4, R)
    assert set(skills.used(half.fmt, half.spec, half.stem, rung["skill_codes"], RULES)) == {
        "NUM.OPS.05",
        "NUM.OPS.04",
        "NUM.PRB.03",
    }
    codes = ["M_MENTAL_STOPS_SHORT", "M_MENTAL_WRONG_WAY", "M_MENTAL_ONE_NOT_GROUP", "M_MUL_ROW_OUT"]
    assert skills.charges(nine.fmt, nine.spec, nine.stem, used, codes, VOCAB, RULES) == {
        "M_MENTAL_STOPS_SHORT": "NUM.OPS.05",
        "M_MENTAL_WRONG_WAY": "NUM.OPS.05",
        "M_MENTAL_ONE_NOT_GROUP": "NUM.OPS.05",
        "M_MUL_ROW_OUT": "NUM.OPS.03",
    }


# ------------------------------------------------------------------------------- printed, read and marked


def _all_methods():
    made = [
        MN.make("DOUBLING", 14, 4, R),
        MN.make("DOUBLING", 34, 2, R),
        MN.make("HALVING", 96, 4, R),
        MN.make("HALVING", 74, 2, R),
        MN.make("DOUBLE_THREE_TIMES", 13, 8, R),
        MN.make("TIMES_TEN_LESS_A_GROUP", 23, 9, R),
        MN.make("TIMES_TEN_AND_A_GROUP", 14, 11, R),
        MN.make("DOUBLE_ONE_HALVE_THE_OTHER", 16, 5, R),
        MN.make("TIMES_HUNDRED_THEN_QUARTER", 24, 25, R),
    ]
    return made + [it for level in LEVELS for _, it in _drawn(level, 4)]


def test_every_step_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of every method, printed through Chromium as a paper is: the key's geometry holds each box, as many as
    its key has digits, so the reader finds every step and the answer."""
    its = _all_methods()
    key = render.render_sheet(Sheet("CS00D4A0", "G3", "Medium", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        for r in it.responses:
            assert boxes[(it.item_id, r.rid)] == len(r.answer), (it.spec, r.rid)


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_every_step_is_marked_against_its_own_key():
    """Each box marked by itself: its own key is right, every key is the sum printed beside it, and each wrong value
    predicted for it names its mistake."""
    for it in _all_methods():
        for r in it.responses:
            if SUM.match(r.label or ""):
                assert r.answer == str(_worked(r.label)), (it.spec, r.label)
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _wrote(r.answer))[0] == "correct", (it.spec, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _wrote(str(wrong)))
                assert status == "wrong" and code in codes, (it.spec, r.rid, code, wrong)


def test_every_mistake_the_methods_name_is_a_row_and_on_md_mentals_list():
    """The methods' mistakes are rows of the vocabulary, each method's own counting against mental maths, and on
    MD.MENTAL's list."""
    rows = {code for code, _ in VOCAB}
    named = {c for it in _all_methods() for r in it.responses for c in r.misconceptions}
    assert named <= rows, named - rows
    assert named <= set(_mental()["misconception_codes"]), named - set(_mental()["misconception_codes"])
    for code in (
        "M_MENTAL_STOPS_SHORT",
        "M_MENTAL_WRONG_WAY",
        "M_MENTAL_ONE_NOT_GROUP",
        "M_MENTAL_DOUBLED_BOTH",
    ):
        assert code in named, code
        assert {VOCAB[k] for k in VOCAB if k[0] == code} == {("row", "NUM.OPS.05")}, code


def test_every_level_fills_each_case_as_often_as_it_asks():
    """A case is covered when the bank holds as many of it as its row asks (12 where it names none); each level, filled
    as the bank fills it, holds every case it lists that often, every question distinct."""
    for level, d in _mental()["difficulty"].items():
        got = _drawn(level, d["min_items"], seed=5)
        held = Counter(c for c, _ in got)
        assert len({it.item_id for _, it in got}) == len(got), level
        for c in d["check"]["cases"]:
            assert held[c] >= CASES[c].get("min_items", 12), (level, c, held[c])
