"""The written methods of multiplication, printed step by step (goals/md2d2-multiplication-methods.yaml).

Every calculation of MUL.2D1D, MUL.3D1D and MUL.2D2D's Easy to Hard levels is printed in each method its level lists,
in fair shares (assumption A1). Every step and total is worked out here from the question's own numbers — a place
part times a number, the parts added, the steps added without a carry — never read back from the code that made
it."""

import dataclasses
import json
import pathlib
import random
from collections import Counter

from engine.assess import draw, render, skills, tags, taxonomy, verify
from engine.assess import written_methods as WM
from engine.assess.pick import Sheet
from engine.w3_read import marking

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
CASES = {c["code"]: c for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]}
CONFIG = {c["key"]: c["value"] for c in json.loads((SEED / "config.json").read_text())["config"]}
RULES = {k.split(".", 1)[1]: v for k, v in CONFIG.items() if k.startswith("skills.")}
VOCAB = {
    (m["code"], m["op"]): (m.get("skill_from", "operation"), m.get("skill_code"))
    for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
COLUMNS = {"COLUMNS", "EXPANDED", "LONG_MULTIPLICATION"}  # in columns the longer number is written on top
SKILLS = ("MUL.2D1D", "MUL.3D1D", "MUL.2D2D")
STRAIGHT = ("Easy", "Medium", "Hard")


def _parts(n):
    """23 → [20, 3]; 302 → [300, 2]: a number partitioned by place, its zero places left out."""
    s = str(n)
    return [int(d) * 10 ** (len(s) - 1 - i) for i, d in enumerate(s) if d != "0"]


def _lead(p):
    """20 → 2, 300 → 3: a part with its tens or hundreds taken as ones."""
    return int(str(p)[0])


def _nocarry(xs):
    """The numbers added column by column, each column's last digit written and nothing carried."""
    width = max(len(str(x)) for x in xs)
    return int(
        "".join(str(sum(int(str(x).rjust(width, "0")[i]) for x in xs) % 10) for i in range(width)).lstrip("0")
        or "0"
    )


def _check(skill, level):
    return SETS[skill]["difficulty"][level]["check"]


def _matches(check):
    codes = [*check["cases"], *check.get("methods", [])]
    return {c: taxonomy.within(CASES[c]["match"], check.get("within")) for c in codes}


def _drawn(skill, level, n, seed=3, cases=None):
    """[(case, question)] of one level, drawn as the bank draws it."""
    check = _check(skill, level) | ({"cases": cases} if cases else {})
    got = draw.level(random.Random(seed), check, _matches(check), SETS[skill]["rung_code"], n)
    assert len(got) == n, (skill, level, len(got))
    return got


def _method(it):
    return tags.derive(it)["method"]


def _answers(it):
    return {r.rid: r for r in it.responses}


def _steps(it):
    """{the step as printed: its key}, every box but the total."""
    return {r.label.rstrip(" =") if r.label else r.rid: r.answer for r in it.responses if r.rid != "ans"}


def test_every_level_prints_each_calculation_in_every_method_it_lists():
    """A1: Easy to Hard print each calculation in every written method the document lists for the skill, in fair shares —
    each case's questions dealt evenly over the methods it can be printed in (a case about the 1-digit number coming
    first is never set out in columns, where the longer number goes on top); every question is still one of its
    level's cases. Two methods may print alike (in a line, and in a line with the 1-digit number first): each takes its
    own share."""
    listed = {s: SETS[s]["difficulty"]["Easy"]["check"].get("methods") for s in SKILLS}
    assert listed == {
        "MUL.2D1D": ["T02", "G07", "G08", "G10", "G11"],
        "MUL.3D1D": ["T13", "T14", "G10", "G11"],
        "MUL.2D2D": ["T22", "G09", "G12", "G13"],
    }
    for skill in SKILLS:
        for level in STRAIGHT:
            check = _check(skill, level)
            assert check.get("methods") == listed[skill], (skill, level)
            ways = [CASES[m]["match"]["method"] for m in check["methods"]]
            each = len(ways) * 2
            per_case = {c: Counter() for c in check["cases"]}
            for case, it in _drawn(skill, level, len(check["cases"]) * each):
                assert verify.dimension_problems(tags.derive(it), check, it.fmt, _matches(check)) == [], (
                    it.spec
                )
                per_case[case][_method(it)] += 1
            for case, counts in per_case.items():
                first = CASES[case]["match"].get("operand_order") == "SHORTER_FIRST"
                can = [w for w in ways if not (first and w in COLUMNS)]
                assert set(counts) == set(can), (skill, level, case, counts)
                low, high = each // len(can), -(-each // len(can))
                for way, k in Counter(can).items():
                    assert k * low <= counts[way] <= k * high, (skill, level, case, way, counts)


def test_partitioning_is_worked_part_by_part_then_added():
    """23 × 4 is 20 × 4 = □ and 3 × 4 = □, then 23 × 4 = □; the 1-digit number written first keeps its place."""
    it = WM.make("PARTITIONING", 23, 4, "R38")
    assert (it.fmt, it.spec["method"]) == ("break_apart", "PARTITIONING")
    assert _steps(it) == {"20 × 4": "80", "3 × 4": "12"}
    assert _answers(it)["ans"].answer == "92"
    assert _steps(WM.make("PARTITIONING", 3, 21, "R38")) == {"3 × 20": "60", "3 × 1": "3"}
    for a, b in ((47, 6), (302, 3), (9, 58)):
        it = WM.make("PARTITIONING", a, b, "R38")
        n, m = (a, b) if a >= b else (b, a)
        assert sorted(int(v) for v in _steps(it).values()) == sorted(p * m for p in _parts(n)), (a, b)
        assert _answers(it)["ans"].answer == str(a * b)


def test_a_grid_has_a_box_in_every_cell_then_the_total():
    """A cell for every part of one number times every part of the other, 2 × 1 and 2 × 2, then the cells added."""
    assert _steps(WM.make("GRID", 23, 4, "R38")) == {"20 × 4": "80", "3 × 4": "12"}
    it = WM.make("GRID", 34, 26, "R40")
    assert it.fmt == "grid_method"
    assert _steps(it) == {"30 × 20": "600", "4 × 20": "80", "30 × 6": "180", "4 × 6": "24"}
    assert _answers(it)["ans"].answer == "884"
    for a, b in ((57, 8), (68, 17), (40 + 9, 31)):
        cells = sorted(p * q for p in _parts(a) for q in _parts(b))
        it = WM.make("GRID", a, b, "R40")
        assert sorted(int(v) for v in _steps(it).values()) == cells, (a, b)
        assert int(_answers(it)["ans"].answer) == sum(cells) == a * b


def test_expanded_columns_write_each_product_in_full():
    """34 × 6 is 4 × 6 = 24 and 30 × 6 = 180, each in a row of its own, then added; 3 digits make three rows."""
    it = WM.make("EXPANDED", 34, 6, "R38")
    assert it.fmt == "expanded_columns"
    assert _steps(it) == {"4 × 6": "24", "30 × 6": "180"}
    assert _answers(it)["ans"].answer == "204"
    assert _steps(WM.make("EXPANDED", 357, 4, "R39")) == {"7 × 4": "28", "50 × 4": "200", "300 × 4": "1200"}
    assert _steps(WM.make("EXPANDED", 6, 125, "R39")) == {"5 × 6": "30", "20 × 6": "120", "100 × 6": "600"}


def test_a_lattice_has_a_box_in_every_cell_then_the_answer():
    """47 × 23: every digit of one number times every digit of the other, each written as two digits across the
    cell's diagonal (4 × 2 is 08), then the answer added along the diagonals."""
    it = WM.make("LATTICE", 47, 23, "R40")
    assert it.fmt == "lattice"
    assert _steps(it) == {"4 × 2": "08", "7 × 2": "14", "4 × 3": "12", "7 × 3": "21"}
    assert _answers(it)["ans"].answer == "1081"
    assert all(len(r.answer) == 2 for r in it.responses if r.rid != "ans"), "every cell is two digits"


def test_a_part_with_its_tens_taken_as_ones_is_named():
    """20 × 4 written 8 is a part multiplied with its tens taken as ones (M_PARTITION_TENS_AS_ONES), in every method that
    partitions; the total it makes (2 × 4 + 3 × 4 = 20) is named the same way."""
    for method in ("PARTITIONING", "GRID", "EXPANDED"):
        it = WM.make(method, 29, 7, "R38")
        for r in it.responses:
            if r.rid == "ans":
                assert r.misconceptions["M_PARTITION_TENS_AS_ONES"] == sum(_lead(p) * 7 for p in _parts(29))
            elif int(r.answer) >= 10 * 7 and int(r.answer) % 10 == 0:  # a tens part's step
                assert r.misconceptions["M_PARTITION_TENS_AS_ONES"] == int(r.answer) // 10, (method, r)
    it = WM.make("GRID", 34, 26, "R40")
    assert (
        _answers(it)[next(r.rid for r in it.responses if r.label == "30 × 20 =")].misconceptions[
            "M_PARTITION_TENS_AS_ONES"
        ]
        == 6
    )


def test_a_grid_added_without_its_ones_cell_is_named():
    """34 × 26's cells added without 4 × 6 make 860 (M_GRID_CELL_DROPPED); 23 × 4's without 3 × 4 make 80."""
    assert _answers(WM.make("GRID", 34, 26, "R40"))["ans"].misconceptions["M_GRID_CELL_DROPPED"] == 860
    assert _answers(WM.make("GRID", 23, 4, "R38"))["ans"].misconceptions["M_GRID_CELL_DROPPED"] == 80


def test_steps_added_without_a_carry_count_against_addition():
    """A11: the steps or rows added without a carry are addition's mistake (M_NOCARRY), on every method that adds them
    and on long multiplication (19 × 14: 76 + 190 written 166), and a wrong total showing it counts against addition,
    not multiplication. A total its steps make with no carry names nothing."""
    placed = {  # what each method adds, as place values: the parts' products, or a lattice's digits by their places
        "PARTITIONING": (29, 7, [p * 7 for p in _parts(29)]),
        "GRID": (34, 26, [p * q for p in _parts(34) for q in _parts(26)]),
        "EXPANDED": (34, 6, [p * 6 for p in _parts(34)]),
        "LATTICE": (47, 23, [p * q for p in _parts(47) for q in _parts(23)]),
    }
    for method, (a, b, added) in placed.items():
        it = WM.make(method, a, b, "R40")
        assert _answers(it)["ans"].misconceptions["M_NOCARRY"] == _nocarry(added) != a * b, method
        used = skills.used(it.fmt, it.spec, it.stem, ["NUM.OPS.03"], RULES)
        assert "NUM.OPS.01" in used, (method, used)
        charged = skills.charges(it.fmt, it.spec, it.stem, used, ["M_NOCARRY"], VOCAB, RULES)
        assert charged == {"M_NOCARRY": "NUM.OPS.01"}, method
    long = [
        it for _, it in _drawn("MUL.2D2D", "Hard", 8, cases=["T20"]) if _method(it) == "LONG_MULTIPLICATION"
    ]
    assert long, "Hard's rows carry when they are added"
    for it in long:
        a, b = it.spec["a"], it.spec["b"]
        rows = [a * int(d) * 10**i for i, d in enumerate(reversed(str(b)))]
        assert _answers(it)["ans"].misconceptions["M_NOCARRY"] == _nocarry(rows), it.spec
        used = skills.used(it.fmt, it.spec, it.stem, ["NUM.OPS.03"], RULES)
        assert (
            skills.charges(it.fmt, it.spec, it.stem, used, ["M_NOCARRY"], VOCAB, RULES)["M_NOCARRY"]
            == "NUM.OPS.01"
        )
    assert "M_NOCARRY" not in _answers(WM.make("PARTITIONING", 23, 4, "R38"))["ans"].misconceptions, (
        "80 + 12 carries nothing"
    )


def test_the_advance_holds_a_partitioning_to_find_the_mistake_in():
    """C06: 23 × 4 worked as 2 × 4 + 3 × 4 = 20; the child finds the mistake and writes the right answer, and the wrong
    total is the one the tens taken as ones make."""
    assert "C06" in _check("MUL.2D1D", "Advance")["cases"]
    for _, it in _drawn("MUL.2D1D", "Advance", 6, cases=["C06"]):
        a, b = it.spec["a"], it.spec["b"]
        n, m = (a, b) if a >= b else (b, a)
        assert (it.fmt, it.spec["planted"]) == ("find_mistake", "M_PARTITION_TENS_AS_ONES")
        wrong = sum(_lead(p) * m for p in _parts(n))
        assert it.spec["wrong"] == wrong != a * b
        assert _answers(it)["ans"].answer == str(a * b)
        assert _answers(it)["ans"].misconceptions == {"M_PARTITION_TENS_AS_ONES": wrong}
        assert str(wrong) in it.stem and " + " in it.stem, it.stem


def test_every_step_is_where_the_printed_key_says_it_is(tmp_path):
    """A sheet of every method, printed through Chromium as a paper is: the key's geometry holds each step's boxes and
    the total's, as many as its key has digits, so the reader finds every one (a lattice cell's two)."""
    its = [
        WM.make("PARTITIONING", 47, 6, "R38"),
        WM.make("GRID", 23, 4, "R38"),
        WM.make("GRID", 34, 26, "R40"),
        WM.make("EXPANDED", 357, 4, "R39"),
        WM.make("LATTICE", 47, 23, "R40"),
    ]
    key = render.render_sheet(Sheet("CS00D2D2", "G4", "Easy", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        for r in it.responses:
            assert boxes[(it.item_id, r.rid)] == len(r.answer), (it.fmt, r.rid)


def test_every_step_is_marked_against_its_own_key():
    """Each box marked by itself: its own key is right, and each wrong value predicted for it names its mistake."""
    for method, (a, b) in {
        "PARTITIONING": (29, 7),
        "GRID": (34, 26),
        "EXPANDED": (357, 4),
        "LATTICE": (47, 23),
    }.items():
        it = WM.make(method, a, b, "R40")
        for r in it.responses:
            stored = {"rid": r.rid, "kind": r.kind, "answer": r.answer, "misconceptions": r.misconceptions}
            assert marking.mark(it.spec, stored, _wrote(r.answer))[0] == "correct", (method, r.rid)
            for code, wrong in r.misconceptions.items():
                status, codes, _ = marking.mark(it.spec, stored, _wrote(str(wrong)))
                assert status == "wrong" and code in codes, (method, r.rid, code, wrong)


def _wrote(text):
    return {"child_answer": text, "answer_state": "written", "working_shown": "none"}


def test_a_long_multiplication_keyed_before_its_rows_mistake_had_a_name_leaves_the_bank():
    """A long multiplication stored before the rows added without a carry were named keeps a key that cannot name
    166 for 19 × 14: it is a key problem, so the refill retires it and draws another. One keyed today is not."""
    for _, it in _drawn("MUL.2D2D", "Hard", 8, cases=["T20"]):
        if _method(it) != "LONG_MULTIPLICATION":
            continue
        today = [dataclasses.asdict(r) for r in it.responses]
        assert verify.key_problems(it.fmt, it.spec, today) == []
        before = [
            r | {"misconceptions": {k: v for k, v in r["misconceptions"].items() if k != "M_NOCARRY"}}
            for r in today
        ]
        assert verify.key_problems(it.fmt, it.spec, before) == ["M_NOCARRY"]


def test_every_mistake_the_methods_name_is_a_row_and_on_its_skills_list():
    """The methods' mistakes are rows of the vocabulary and on the lists of the skills whose questions name them."""
    rows = {code for code, _ in VOCAB}
    for skill in SKILLS:
        named = set()
        for level in STRAIGHT:
            check = _check(skill, level)
            n = len(check["cases"]) * len(check["methods"])
            named |= {c for _, it in _drawn(skill, level, n) for r in it.responses for c in r.misconceptions}
        assert named <= rows, (skill, named - rows)
        assert named <= set(SETS[skill]["misconception_codes"]), (
            skill,
            named - set(SETS[skill]["misconception_codes"]),
        )
    assert {"M_PARTITION_TENS_AS_ONES", "M_GRID_CELL_DROPPED"} <= rows
