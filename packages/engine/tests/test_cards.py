"""A kind of question is a row (goals/sf1-a-kind-of-question-is-a-row.yaml, ADR 0075).

A kind (`supabase/seed/question_formats.json`) holds its words with each number named, its answer and each mistake as
formulas of those numbers, and the examples it was made from; a level's rule (`skill_sets.json`) holds each number's
range and the answer's bounds, and names the kinds it uses. Nimish, 2026-10-15: an engine that "simply checks whether a
certain question belongs to a certain format". Every answer here is worked out by the test from the printed words, not
taken from the engine.
"""

import itertools
import json
import random
import re

import pytest

from engine.assess import cards
from engine.core import db

SEED = db.REPO_ROOT / "supabase" / "seed"
KINDS = {k["code"]: k for k in json.loads((SEED / "question_formats.json").read_text())["question_formats"]}
SKILLS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
ACHAL = ("MUL.THREE", "NUM.SEQUENCE", "MUL.NTH")


def _rule(code, level):
    return SKILLS[code]["difficulty"][level]["check"]


def _levels():
    """Every (skill, level, kind) Achal's skills hold."""
    return [
        (code, level, k)
        for code in ACHAL
        for level, band in SKILLS[code]["difficulty"].items()
        for k in band["check"]["cards"]
    ]


def _worked(code, text):
    """The answer worked from the printed words alone, as a child would: the product of three numbers, the next term
    of four in equal steps, the nth multiple, the first five multiples."""
    if code == "MUL.THREE" and "×" in text:
        a, b, c = map(int, re.findall(r"\d+", text))
        return str(a * b * c)
    if code == "MUL.THREE":  # a story: the three numbers in the order told
        a, b, c = map(int, re.findall(r"\d+", text))
        return str(a * b * c)
    if code == "NUM.SEQUENCE":
        t = [int(x) for x in re.findall(r"\d+", text)]
        steps = {y - x for x, y in itertools.pairwise(t)}
        assert len(steps) == 1, f"the steps are not equal: {text}"
        return str(t[-1] + steps.pop())
    n_k = re.search(r"the (\d+)\w\w multiple of (\d+)", text)
    if n_k:
        return str(int(n_k[1]) * int(n_k[2]))
    k = int(re.search(r"multiples of (\d+)", text)[1])
    return ", ".join(str(k * i) for i in range(1, 6))


def test_achals_kinds_and_levels_make_sense():
    """Every kind the three skills use is a row; each level's rule gives a range for every number its kinds name; no
    kind or level is refused."""
    for code, level, k in _levels():
        assert k in KINDS, f"{code} {level} names a kind no row holds: {k}"
        assert cards.problems(KINDS[k], _rule(code, level)) == [], (code, level, k)


@pytest.mark.parametrize(("code", "level", "kind"), _levels())
def test_a_question_belongs_to_a_kind_only_where_its_numbers_print_its_words(code, level, kind):
    """Each question drawn belongs to its kind at its level, and to no other level of its skill (a question in the bank
    has one level); its answer is the one worked from its printed words; and with its stored answer changed it belongs
    no longer."""
    k, rule = KINDS[kind], _rule(code, level)
    rng = random.Random(7)
    for _ in range(30):
        it = cards.draw(k, rule, rng, "R0", "Conceptual")
        assert it.template == kind and it.fmt == "card"
        assert cards.belongs(k, rule, it) == [], (kind, level, cards.sentence(it))
        (r,) = it.responses
        assert r.answer == _worked(code, cards.sentence(it)), (cards.sentence(it), r.answer)
        tampered = it.to_dict()
        tampered["responses"][0]["answer"] = "1"
        assert cards.belongs(k, rule, tampered), f"a changed answer still belongs: {cards.sentence(it)}"
    for other in SKILLS[code]["difficulty"]:
        if other != level and kind in _rule(code, other)["cards"]:
            both = [
                cards.sentence(it)
                for it in cards.every(k, rule, "R0", "Conceptual")
                if cards.find(k, _rule(code, other), cards.sentence(it)) is not None
            ]
            assert both == [], f"{code}: {level}'s questions belong to {other} too: {both[:3]}"


def test_every_example_achal_gave_belongs_to_its_level():
    """The examples each kind was made from belong to the level he gave them for. His "100, 81, 72, 63" for counting
    back belongs to no level — its steps are 19, 9 and 9 — and "90, 81, 72, 63" to Hard."""
    seen = 0
    for kind in KINDS.values():
        for level, texts in kind.get("examples", {}).items():
            rule = _rule(kind["skill_set"], level)
            for text in texts:
                seen += 1
                assert cards.find(kind, rule, text) is not None, (kind["code"], level, text)
    assert seen >= 10, seen
    back = KINDS["SEQ.BACK"]
    for level in SKILLS["NUM.SEQUENCE"]["difficulty"]:
        rule = _rule("NUM.SEQUENCE", level)
        if "SEQ.BACK" in rule["cards"]:
            assert cards.find(back, rule, "100, 81, 72, 63, □") is None
    assert cards.find(back, _rule("NUM.SEQUENCE", "Hard"), "90, 81, 72, 63, □") == {"s": 90, "d": 9}
    assert cards.find(KINDS["MUL3.SUM"], _rule("MUL.THREE", "Easy"), "9 × 6 × 9 = □") is None, (
        "Advance's, not Easy's"
    )


def _brute_three(rule):
    lo, hi = rule["numbers"]["a"]
    alo, ahi = rule["answer_within"]
    return sum(1 for a, b, c in itertools.product(range(lo, hi + 1), repeat=3) if alo <= a * b * c <= ahi)


def test_a_level_counts_the_different_questions_it_can_make():
    """Each level counts the different questions it can make, and the count is the one a test works out by brute force
    from the level's own numbers: three numbers of 2 to 5 with a product up to 30 make 26, not 100."""
    for level in ("Easy", "Medium", "Hard", "Advance"):
        rule = _rule("MUL.THREE", level)
        assert cards.count(KINDS["MUL3.SUM"], rule) == _brute_three(rule), level
    assert cards.count(KINDS["MUL3.SUM"], _rule("MUL.THREE", "Easy")) == 26
    hard = _rule("MUL.NTH", "Hard")
    (klo, khi), (nlo, nhi) = hard["numbers"]["k"], hard["numbers"]["n"]
    assert cards.count(KINDS["MULT.NTH"], hard) == (khi - klo + 1) * (nhi - nlo + 1)
    on = _rule("NUM.SEQUENCE", "Easy")
    (slo, shi), (dlo, dhi), (_, top) = on["numbers"]["s"], on["numbers"]["d"], on["answer_within"]
    assert cards.count(KINDS["SEQ.ON"], on) == sum(
        1 for s in range(slo, shi + 1) for d in range(dlo, dhi + 1) if s + 4 * d <= top
    )


@pytest.mark.parametrize(("code", "level", "kind"), _levels())
def test_all_a_level_can_make_is_drawn_once_each_with_a_mistake_named(code, level, kind):
    """Every question a level can make, drawn once each: as many as it counts, no two the same, each naming at least
    one mistake by a wrong answer that is not the right one."""
    k, rule = KINDS[kind], _rule(code, level)
    every = cards.every(k, rule, "R0", "Conceptual")
    assert len(every) == cards.count(k, rule)
    assert len({it.item_id for it in every}) == len(every)
    assert len({cards.sentence(it) for it in every}) == len(every)
    for it in every:
        (r,) = it.responses
        assert r.misconceptions, cards.sentence(it)
        assert all(w != r.answer for w in r.misconceptions.values()), (cards.sentence(it), r.misconceptions)


def test_a_kind_that_cannot_work_is_refused():
    """A kind whose formula names a number no range gives, whose words name one, whose mistake always writes the right
    answer, or a level whose numbers make nothing — each is refused with its reason, before anything is drawn."""
    k = dict(KINDS["MUL3.SUM"])
    rule = _rule("MUL.THREE", "Easy")
    assert any("z" in p for p in cards.problems({**k, "answer": "a*b*z"}, rule))
    assert any("z" in p for p in cards.problems({**k, "text": "{a} × {z} = □"}, rule))
    assert any("M_SAME" in p for p in cards.problems({**k, "also": {"M_SAME": "c*b*a"}}, rule))
    assert any("nothing" in p for p in cards.problems(k, {**rule, "answer_within": [1000, 2000]}))
    with pytest.raises(ValueError):
        cards.every(k, {**rule, "answer_within": [1000, 2000]}, "R0", "Conceptual")
