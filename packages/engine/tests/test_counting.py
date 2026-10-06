"""Grade 1's tally marks and equal groups (engine/assess/counting.py, drawn by engine/assess/pictures.py), against
the skill sets the seed holds for them (goals/g1-taught-till-september.yaml). Pure: no database.

Each answer is counted again from the printed page, never read back from the generator: a tally's lines, a picture's
rings and dots, a sum's addends.
"""

import json
import pathlib
import random
import re

import pytest

from engine.assess import bands, counting
from engine.assess.pick import Sheet
from engine.assess.render import render_item
from engine.w3_read import marking

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase/seed"
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
VOCAB = {
    (m["code"], m["op"]) for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
LEVELS = [(code, d) for code in ("DATA.TALLY", "MUL.GROUPS") for d in SETS[code]["difficulty"]]
VERTICAL = re.compile(r'<line x1="(\d+)" y1="4" x2="\1" y2="28"/>')


def _printed(it):
    return render_item(Sheet("CS000000", "G1", "Easy", 1, "test", [it]), it, 1)


def _draws(code, difficulty, n=60, seed=7):
    """Up to `n` questions of one level, made from its own rule in the seed as the bank makes them."""
    rng, check, out = random.Random(seed), SETS[code]["difficulty"][difficulty]["check"], []
    for _ in range(n * 4):
        try:
            out.append(bands.native_item(check["format"], check, rng, "R34", "Conceptual"))
        except RuntimeError:
            continue
        if len(out) == n:
            break
    return out


@pytest.mark.parametrize("n", range(1, 21))
def test_a_tally_shows_as_many_lines_as_its_answer_in_bundles_of_five(n):
    """A tally of n prints n lines: a bundle of four upright lines crossed by a fifth for every five, then the rest
    upright — and the key is the number the lines make."""
    it = counting.tally(random.Random(n), "R34", "Conceptual", {"shape": "READ", "lo": n, "hi": n})
    page = _printed(it)
    assert page.count("<line") == n
    assert len(VERTICAL.findall(page)) == n - n // 5, "every fifth line is the one across a bundle"
    assert it.responses[0].answer == str(n)


def test_two_tallies_are_put_together_or_compared_by_the_lines_they_show():
    """Advance: two tallies, one a row. The answer is the lines of both together, or how many more the first shows
    than the second — counted off the page."""
    for it in _draws("DATA.TALLY", "Advance"):
        shown = [row.count("<line") for row in _printed(it).split("<tr>")[1:]]
        assert shown == [it.spec["a"], it.spec["b"]]
        want = shown[0] + shown[1] if it.spec["shape"] == "ALTOGETHER" else shown[0] - shown[1]
        assert want > 0 and it.responses[0].answer == str(want)


@pytest.mark.parametrize("groups", range(2, 6))
@pytest.mark.parametrize("size", range(2, 7))
def test_equal_groups_are_added_again_and_drawn_as_many_as_asked(groups, size):
    """Grade 1's start of multiplication: groups of the same size, how many in all — written as the same number
    added again, drawn as rings of dots, or told as a story — and the key is what the page adds up to."""
    rule = {"groups": [groups, groups], "size": [size, size]}
    rng = random.Random(groups * 10 + size)
    as_sum = counting.equal_groups(rng, "R35", "Conceptual", {**rule, "shape": "SUM"})
    line = re.search(r'<span class="eq">([\d +]+) =</span>', _printed(as_sum))
    assert line, "the sum is printed"
    addends = [int(x) for x in line.group(1).split("+")]
    assert addends == [size] * groups and as_sum.responses[0].answer == str(sum(addends))
    picture = _printed(counting.equal_groups(rng, "R35", "Conceptual", {**rule, "shape": "PICTURE"}))
    assert picture.count('class="group"') == groups and picture.count('class="dot"') == groups * size
    story = counting.equal_groups(rng, "R35", "Conceptual", {**rule, "shape": "STORY"})
    assert re.findall(r"\d+", story.stem) == [str(groups), str(size)]
    assert story.responses[0].answer == str(groups * size)


@pytest.mark.parametrize("code,difficulty", LEVELS, ids=[f"{c} {d}" for c, d in LEVELS])
def test_every_counting_question_marks_right_and_names_its_mistakes(code, difficulty):
    """The marker papers go through marks the key right, and every wrong answer the question predicts wrong with
    the mistake it names — a mistake the vocabulary holds for the question's operation or for any. Every question
    has one at least, so a wrong answer is a diagnosis and not only a cross."""
    for it in _draws(code, difficulty):
        assert it.fmt in SETS[code]["formats"]
        page = _printed(it)
        r = it.responses[0]
        assert f'data-item="{it.item_id}"' in page and f'data-r="{r.rid}"' in page
        right = marking.mark(
            {"kind": "bare"}, vars(r), {"child_answer": r.answer, "answer_state": "answered"}
        )
        assert right[0] == "correct", (it.spec, r.answer)
        assert r.misconceptions, f"{it.spec}: nothing to diagnose a wrong answer by"
        for mistake, wrong in r.misconceptions.items():
            assert (mistake, it.spec.get("op", "any")) in VOCAB or (mistake, "any") in VOCAB, mistake
            assert mistake in SETS[code]["misconception_codes"], mistake
            status, codes, _ = marking.mark(
                {"kind": "bare"}, vars(r), {"child_answer": str(wrong), "answer_state": "answered"}
            )
            assert status == "wrong" and codes == [mistake], (it.spec, mistake, wrong, codes)


@pytest.mark.parametrize("code,difficulty", LEVELS, ids=[f"{c} {d}" for c, d in LEVELS])
def test_each_level_holds_as_many_different_questions_as_it_promises(code, difficulty):
    """A level's `min_items` is a promise the bank must keep with different questions: a worksheet of twelve needs
    at least twelve, and the bank tops the level up to its promise."""
    level = SETS[code]["difficulty"][difficulty]
    made = {it.item_id for it in _draws(code, difficulty, n=400, seed=1)}
    assert len(made) >= level["min_items"] >= 12
    assert bands.unread_keys(level["check"]) == [], "every key of the rule is one the generator reads"
