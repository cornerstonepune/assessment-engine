"""Every wrong answer the drafted document names for a division a child works, predicted from the question's own numbers
(goals/md3a-straight-division.yaml), as each column mistake of addition, subtraction and multiplication is.

A division's answer is two boxes when it leaves a remainder: the quotient's and the remainder's. A mistake is named in
the box it shows in, at the value a child making it writes there, worked here by hand from the digits, never read back
from the code that made the question."""

import json
import pathlib

import pytest

from engine.assess import div_mistakes as DM
from engine.assess import verify

ROOT = pathlib.Path(__file__).resolve().parents[3]
SEED = ROOT / "supabase/seed"
ROWS = {
    (m["code"], m["op"]) for m in json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
}
SETS = {s["code"]: s for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]}
FOUR = ["DIV.FACTS", "DIV.TENS", "DIV.2D1D", "DIV.3D1D"]


def _digits(n):
    return [int(x) for x in str(n)]


def _tz(n):
    return len(str(n)) - len(str(n).rstrip("0")) if n else 0


def _zeros_extra(a, b):
    """A round number by one digit: the fact borrows one of its zeros (20 ÷ 4 = 5), then every zero is written back."""
    core = a // 10 ** _tz(a)
    return (core * 10 // b if core < b else core // b) * 10 ** _tz(a)


# (quotient, remainder) a child making each mistake writes; the remainder is the right one where the mistake is the
# quotient's alone, None where the mistake leaves no remainder to write
BY_HAND = {
    "M_DIV_QUOTIENT_ZERO_DROPPED": lambda a, b: (int(str(a // b).replace("0", "") or 0), a % b),
    "M_DIV_EXCHANGE_LOST": lambda a, b: (int("".join(str(x // b) for x in _digits(a))), _digits(a)[-1] % b),
    "M_DIV_REMAINDER_ADDED": lambda a, b: _remainder_added(a, b),
    "M_DIV_LEAD_DROPPED": lambda a, b: divmod(int(str(a)[1:]), b),
    "M_DIV_BRING_DOWN_MISSED": lambda a, b: divmod(a // 10, b),
    "M_DIV_REMAINDER_TOO_BIG": lambda a, b: (a // b - 1, a % b + b),
    "M_DIV_REMAINDER_AS_DIGIT": lambda a, b: (int(f"{a // b}{a % b}"), None),
    "M_DIV_SWAPPED": lambda a, b: (a % b, a // b),
    "M_DIV_BIGGER_BY_SMALLER": lambda a, b: divmod(b, a),
    "M_DIV_SELF_AS_ZERO": lambda a, b: (0, None),
    "M_DIV_ZERO_DIVIDED": lambda a, b: (b, None),
    "M_DIV_TENS_ZERO_LEFT": lambda a, b: (a // b * 10, None),
    "M_DIV_TENS_ZERO_EXTRA": lambda a, b: (_zeros_extra(a, b), None),
    "M_WRONG_OP": lambda a, b: (a * b, None),
    "M_DIV_SUBTRACTED": lambda a, b: (a - b, None),
}


def _remainder_added(a, b):
    """The remainder added to the next digit (3 + 2), where it should make tens of it (30 + 2)."""
    q, r = "", 0
    for x in _digits(a):
        q, r = q + str((r + x) // b), (r + x) % b
    return int(q), r


def _steps(a, b):
    """The remainder each digit passes on, short division from the left."""
    steps, rem = [], 0
    for x in _digits(a):
        rem = (rem * 10 + x) % b
        steps.append(rem)
    return steps


# Where each mistake can be made: a zero in the quotient, a digit whose remainder moves on, a first digit smaller than
# the divisor, more than one digit, a remainder, a number divided smaller than its divisor, ÷ itself, 0 divided, ÷ 10,
# 100 or 1000, a round number by one digit; the two the operation itself invites, always. Not where a more particular
# mistake is the same act on these numbers: an exchange lost that is only the first digit's, smaller than the divisor,
# is that digit skipped (17 ÷ 5 → 1 r 2); stopping before the last digit of an exact division whose only zero ends the
# quotient is that zero left out (840 ÷ 4 → 21); a number taken from itself is ÷ itself read as nothing left.
def _can(code, a, b):
    q, r = divmod(a, b)
    steps = _steps(a, b)
    only_the_first = _digits(a)[0] < b and not any(_steps(int(str(a)[1:] or 0), b)[:-1])
    zero_last = r == 0 and q % 10 == 0 and "0" not in str(q // 10)
    return {
        "M_DIV_QUOTIENT_ZERO_DROPPED": "0" in str(q) and q >= 10,
        "M_DIV_EXCHANGE_LOST": len(str(a)) >= 2 and any(steps[:-1]) and b < 10 and not only_the_first,
        "M_DIV_REMAINDER_ADDED": len(str(a)) >= 2 and any(steps[:-1]) and b < 10,
        "M_DIV_LEAD_DROPPED": len(str(a)) >= 2 and _digits(a)[0] < b < 10,
        "M_DIV_BRING_DOWN_MISSED": len(str(a)) >= 2 and q >= 10 and b < 10 and not zero_last,
        "M_DIV_REMAINDER_TOO_BIG": r > 0 and q >= 1,
        "M_DIV_REMAINDER_AS_DIGIT": r > 0,
        "M_DIV_SWAPPED": r > 0,
        "M_DIV_BIGGER_BY_SMALLER": 0 < a < b,
        "M_DIV_SELF_AS_ZERO": a == b > 0,
        "M_DIV_ZERO_DIVIDED": a == 0 < b,
        "M_DIV_TENS_ZERO_LEFT": b in (10, 100, 1000) and r == 0,
        "M_DIV_TENS_ZERO_EXTRA": b < 10 and _tz(a) >= 1 and r == 0 and a // 10 ** _tz(a) < b,
        "M_WRONG_OP": b > 1,
        "M_DIV_SUBTRACTED": b > 0 and a > b,
    }[code]


# The document's own examples (docs/design/multiplication-division-taxonomy.md, the named mistakes), and their wrong
# answers as the document writes them
EXAMPLES = {
    "M_DIV_QUOTIENT_ZERO_DROPPED": (804, 4, (21, 0)),
    "M_DIV_EXCHANGE_LOST": (72, 4, (10, 2)),
    "M_DIV_REMAINDER_ADDED": (72, 4, (11, 1)),
    "M_DIV_LEAD_DROPPED": (156, 4, (14, 0)),
    "M_DIV_BRING_DOWN_MISSED": (516, 4, (12, 3)),
    "M_DIV_REMAINDER_TOO_BIG": (85, 4, (20, 5)),
    "M_DIV_REMAINDER_AS_DIGIT": (85, 4, (211, None)),
    "M_DIV_SWAPPED": (17, 5, (2, 3)),
    "M_DIV_BIGGER_BY_SMALLER": (3, 5, (1, 2)),
    "M_DIV_SELF_AS_ZERO": (7, 7, (0, None)),
    "M_DIV_ZERO_DIVIDED": (0, 5, (5, None)),
    "M_DIV_TENS_ZERO_LEFT": (4500, 100, (450, None)),
    "M_DIV_TENS_ZERO_EXTRA": (200, 4, (500, None)),
    "M_WRONG_OP": (84, 4, (336, None)),
    "M_DIV_SUBTRACTED": (84, 4, (80, None)),
}


def _sample():
    """Every division a straight level of the four prints, thinned where the numbers run past a thousand."""
    out = {(q * d + r, d) for d in range(1, 13) for q in range(13) for r in range(d) if q <= 9 or r == 0}
    out |= {(a, d) for a in range(10, 1000) for d in range(2, 10)}
    out |= {(a, d) for d in (10, 100, 1000) for a in range(d, 10000, 7)}
    out |= {(a, d) for a in range(10, 10000, 10) for d in range(2, 10)}
    return sorted(out)


def test_every_division_mistake_a_calculation_shows_is_predicted():
    """The fourteen the document names for a division a child works, and × in place of ÷: each predicted at its own
    example's wrong answer, and across every division a straight level prints, wherever it can be made and changes the
    answer, at the value worked here by hand: every one, so two that meet by chance on one answer are both named, as
    marking names every match. A story's mistake (a remainder not rounded up) is a story's (M3b)."""
    assert set(BY_HAND) == set(EXAMPLES)
    for code, (a, b, wrong) in EXAMPLES.items():
        assert BY_HAND[code](a, b) == wrong, code  # the hand-worked rule is the document's own
        assert DM.predict(a, b).get(code) == wrong, (code, a, b)
    for a, b in _sample():
        right = divmod(a, b)
        got = DM.predict(a, b)
        # wrong where its quotient differs, or a remainder it writes does: 0 × 5 written for 0 ÷ 5 is 0, and right
        want = {
            c: f(a, b)
            for c, f in BY_HAND.items()
            if _can(c, a, b)
            and f(a, b)[0] >= 0
            and (f(a, b)[0] != right[0] or f(a, b)[1] not in (None, right[1]))
        }
        assert got == want, (
            a,
            b,
            {c: (got.get(c), want.get(c)) for c in got.keys() | want.keys() if got.get(c) != want.get(c)},
        )


def test_a_mistake_is_named_in_the_box_it_shows_in():
    """85 ÷ 4 answered 20 r 5 shows the remainder too big in both boxes; 17 ÷ 5 answered 2 r 3, the two swapped, in both;
    804 ÷ 4 answered 21, its zero left out, in the quotient's only, since it has no remainder; 813 ÷ 4 answered 23 r 1
    names the zero in the quotient's box and leaves the right remainder unnamed. A box is marked by itself, so it names
    every mistake that writes its value there: 17 ÷ 5's quotient written 2 is the two swapped or one group short."""
    boxes = {r.rid: r for r in verify.division(85, 4, "R44").responses}
    assert (boxes["ans"].answer, boxes["rem"].answer) == ("21", "1")
    assert boxes["ans"].misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 20
    assert boxes["rem"].misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 5
    swapped = {r.rid: r for r in verify.division(17, 5, "R42").responses}
    assert (
        swapped["ans"].misconceptions["M_DIV_SWAPPED"],
        swapped["rem"].misconceptions["M_DIV_SWAPPED"],
    ) == (2, 3)
    exact = verify.division(804, 4, "R45")
    assert [r.rid for r in exact.responses] == ["ans"]
    assert exact.responses[0].misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 21
    zero = {r.rid: r for r in verify.division(813, 4, "R45").responses}
    assert zero["ans"].misconceptions["M_DIV_QUOTIENT_ZERO_DROPPED"] == 23
    assert "M_DIV_QUOTIENT_ZERO_DROPPED" not in zero["rem"].misconceptions
    assert swapped["ans"].misconceptions["M_DIV_REMAINDER_TOO_BIG"] == 2
    for a, b in _sample()[::37]:
        q, r = divmod(a, b)
        for box in verify.division(a, b, "R44").responses:
            i, right = (0, q) if box.rid == "ans" else (1, r)
            want = {c: v[i] for c, v in BY_HAND_ALL(a, b).items() if v[i] is not None and v[i] != right}
            assert box.misconceptions == want, (a, b, box.rid)


def BY_HAND_ALL(a, b):  # noqa: N802  every mistake that can be made on a ÷ b and changes its answer, worked by hand
    right = divmod(a, b)
    return {
        c: f(a, b)
        for c, f in BY_HAND.items()
        if _can(c, a, b)
        and f(a, b)[0] >= 0
        and (f(a, b)[0] != right[0] or f(a, b)[1] not in (None, right[1]))
    }


@pytest.mark.parametrize(
    "a, b, named, not_named",
    [
        (
            17,
            5,
            "M_DIV_LEAD_DROPPED",
            "M_DIV_EXCHANGE_LOST",
        ),  # the only exchange is the 1's: skipping it is losing it
        (840, 4, "M_DIV_QUOTIENT_ZERO_DROPPED", "M_DIV_BRING_DOWN_MISSED"),  # the last step is the zero
        (7, 7, "M_DIV_SELF_AS_ZERO", "M_DIV_SUBTRACTED"),  # 7 taken from 7 is 7 ÷ 7 read as nothing left
    ],
)
def test_one_wrong_answer_names_one_mistake_where_two_would_be_the_same_act(a, b, named, not_named):
    """Two mistakes that write one answer on every such question, by what they are, name the more particular one, as
    multiplication's do; two that meet by chance are both named (7 ÷ 3 written 21: the remainder as a digit, or ×)."""
    got = DM.predict(a, b)
    assert named in got and not_named not in got, got
    assert {"M_DIV_REMAINDER_AS_DIGIT", "M_WRONG_OP"} <= set(DM.predict(7, 3))


def test_every_division_mistake_is_a_row_and_on_the_lists_of_the_skills_that_show_it():
    """Each is a row of the vocabulary under ÷, and on the list of every one of the four whose questions name it."""
    assert {(c, "÷") for c in BY_HAND} <= ROWS
    for code in FOUR:
        named = set(SETS[code]["misconception_codes"])
        shows = {c for c, (a, b, _) in EXAMPLES.items() if _home(a, b) == code}
        assert shows <= named, (code, shows - named)


def _home(a, b):
    from engine.assess import placing, tags
    from engine.assess.items import Item

    sp = {"a": a, "b": b, "op": "÷", "layout": "horizontal"}
    t = tags.derive(Item("x", "x", "R9", [], "P", "bare_sum", False, "", sp, []))
    cases = {
        c["code"]: c["match"]
        for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]
    }
    got = placing.place("bare_sum", t, [SETS[s] for s in FOUR], cases)
    return got[0]["code"] if got else None
