"""Equality, inverse and checking (taxonomy §7): the equals sign read as "is the same as".

Three kinds of question, each deterministic given an RNG:
- `equation` — one line with = in the middle and something missing: a sign, a number on either side, the
  same number in two boxes, or nothing missing but the claim "these are equal" to judge;
- `fact_family` — three facts that follow from one;
- `inverse_check` — an answer checked with the other operation.
The wrong answers each one predicts are the equality mistakes the vocabulary names: reading = as "the
answer comes next", adding every number in sight, turning a subtraction round.
"""

from .items import Response, _cells, _item

MINUS = "−"
UNFIT = "these numbers do not make this question; draw again"


def _sign(op):
    return MINUS if op == "-" else "+"


def _missing_sign(rng, rung, n_signs):
    if n_signs == 1:
        a, b = rng.randint(6, 18), rng.randint(2, 9)
        op = rng.choice("+-")
        c = a + b if op == "+" else a - b
        text = f"{a} □ {b} = {c}"
        rs = [
            Response(
                "s1",
                "tick",
                _sign(op),
                options=["+", MINUS],
                label="the sign",
                misconceptions={"M_WRONG_OP": _sign("-" if op == "+" else "+")},
            )
        ]
        return text, rs, [op]
    a, b, c = rng.randint(9, 20), rng.randint(2, 9), rng.randint(2, 9)
    ops = [rng.choice("+-"), rng.choice("+-")]
    total = a
    for op, x in zip(ops, (b, c)):
        total = total + x if op == "+" else total - x
    if total < 0 or b == c or (ops[0] == ops[1] and rng.random() < 0.5):
        raise RuntimeError(UNFIT)  # b == c would let two different pairs of signs both be right
    text = f"{a} □ {b} □ {c} = {total}"
    rs = [
        Response(
            f"s{i + 1}",
            "tick",
            _sign(op),
            options=["+", MINUS],
            label=f"sign {i + 1}",
            misconceptions={"M_WRONG_OP": _sign("-" if op == "+" else "+")},
        )
        for i, op in enumerate(ops)
    ]
    return text, rs, ops


def equation(rng, rung, signal, shape, hi=50):
    """One equation of the given shape (§7). Raises RuntimeError when this draw's numbers do not make it."""
    if shape in ("MISSING_SIGN", "MISSING_SIGNS"):
        text, rs, ops = _missing_sign(rng, rung, 1 if shape == "MISSING_SIGN" else 2)
        stem = "Write + or − in each box to make it true."
    elif shape in ("BALANCE_SAME_OP", "BALANCE_TWO_OPS"):
        a, b = rng.randint(11, hi), rng.randint(3, hi // 2)
        left_op = "+" if shape == "BALANCE_SAME_OP" else rng.choice("+-")
        right_op = "+" if shape == "BALANCE_SAME_OP" else ("-" if left_op == "+" else "+")
        if left_op == "-" and b >= a:
            raise RuntimeError(UNFIT)
        left = a + b if left_op == "+" else a - b
        known = rng.randint(2, max(3, left - 2))
        ans = left - known if right_op == "+" else left + known
        if ans <= 0 or (right_op == "+" and ans == known):
            raise RuntimeError(UNFIT)
        text = f"{a} {_sign(left_op)} {b} = □ {_sign(right_op)} {known}"
        wrong = {"M_EQUALS_MEANS_ANSWER": left, "M_ADD_ALL": a + b + known}
        rs = [
            Response(
                "ans",
                "digits",
                str(ans),
                cells=_cells(max(left, ans)),
                misconceptions={k: v for k, v in wrong.items() if v != ans},
            )
        ]
        ops = [left_op, right_op] if left_op != right_op else [left_op]
        stem = "Write the number that makes both sides equal."
    elif shape == "SAME_BOTH_SIDES":
        x, add = rng.randint(3, 20), rng.randint(2, 15)
        total = 2 * x + add
        text = f"□ + {add} = {total} − □"
        rs = [
            Response(
                "ans",
                "digits",
                str(x),
                cells=_cells(total),
                misconceptions={"M_ADD_INSTEAD": add + total, "M_EQUALS_MEANS_ANSWER": total - add},
            )
        ]
        ops, stem = ["+", "-"], "The same number goes in both boxes. What is it?"
    elif shape == "TRUE_FALSE":
        a, b = rng.randint(12, hi), rng.randint(12, hi)
        shift = rng.choice([1, 2, 3, 5, 10])
        true = rng.random() < 0.5
        c, d = (a + shift, b - shift) if true else (a + shift, b)
        if d <= 0:
            raise RuntimeError(UNFIT)
        text = f"{a} + {b} = {c} + {d}"
        rs = [
            Response(
                "tf",
                "tick",
                "true" if true else "false",
                options=["true", "false"],
                label="true or false",
                misconceptions={"M_REVERSES_CLAIM_TRUTH": "false" if true else "true"},
            )
        ]
        ops, stem = ["+"], "Is this true or false? Decide without working out both sides."
    elif shape == "COMPARE":
        a, b = rng.randint(150, 480), rng.randint(20, 90)
        shift = rng.choice([1, 2, 3])
        c, d = a + shift, b - rng.choice([shift - 1, shift, shift + 1])
        if d <= 0:
            raise RuntimeError(UNFIT)
        left, right = a + b, c + d
        sign = "<" if left < right else (">" if left > right else "=")
        text = f"{a} + {b} □ {c} + {d}"
        flipped = {"<": ">", ">": "<", "=": "<"}[sign]
        rs = [
            Response(
                "cmp",
                "tick",
                sign,
                options=["<", "=", ">"],
                label="<, = or >",
                misconceptions={"M_COMPARE_REVERSED": flipped} if sign != "=" else {},
            )
        ]
        ops, stem = ["+"], "Write <, = or > without working out both sums."
    else:
        raise ValueError(f"no equation shape {shape!r}")
    spec = dict(text=text, shape=shape, ops=ops)
    return _item(f"EQ.{shape}", rung, signal, "equation", stem, spec, rs, working_lines=1)


def fact_family(rng, rung, signal, shape, hi=20):
    """Three facts from one (§7): 7 + 5 = 12 gives 5 + 7, 12 − 7 and 12 − 5; 14 − 6 = 8 gives 8 + 6."""
    a, b = rng.randint(3, hi - 3), rng.randint(2, hi // 2)
    if a == b:
        raise RuntimeError(UNFIT)
    if shape == "FROM_ADDITION":
        c = a + b
        given = f"{a} + {b} = {c}"
        parts = [
            (f"{b} + {a} = □", c, {"M_FACT_PM1": c + 1}),
            (f"{c} − {a} = □", b, {"M_ADD_INSTEAD": c + a}),
            (f"{c} − {b} = □", a, {"M_ADD_INSTEAD": c + b}),
        ]
    else:
        if b >= a:
            a, b = b, a
        c = a - b
        given = f"{a} − {b} = {c}"
        parts = [
            (f"{c} + {b} = □", a, {"M_SUB_INSTEAD": abs(c - b)}),
            (f"{a} − {c} = □", b, {"M_ADD_INSTEAD": a + c}),
        ]
    rs = [
        Response(
            f"f{i + 1}",
            "digits",
            str(ans),
            cells=_cells(max(ans, c, a)),
            label=text,
            misconceptions={k: v for k, v in mis.items() if v != ans and v >= 0},
        )
        for i, (text, ans, mis) in enumerate(parts)
    ]
    spec = dict(
        given=given,
        facts=[t for t, _, _ in parts],
        shape=shape,
        a=a,
        b=b,
        op="+" if shape == "FROM_ADDITION" else "-",
        ops=["+", "-"],
    )
    return _item(
        "FACTS",
        rung,
        signal,
        "fact_family",
        f"{given}. Use it to finish these facts.",
        spec,
        rs,
        working_lines=0,
    )


def inverse_check(rng, rung, signal, op, digits=3):
    """An answer checked with the other operation (§7): 347 + 258 = 605? 605 − 258 = □. Right or not?"""
    lo, hi = 10 ** (digits - 1), 10**digits - 1
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    if op == "-" and b >= a:
        a, b = b, a
    if a == b or a % 10 == 0 or b % 10 == 0:
        raise RuntimeError(UNFIT)
    exact = a + b if op == "+" else a - b
    claimed = exact if rng.random() < 0.5 else exact + rng.choice([-10, 10, -1, 1, 100])
    if claimed <= 0:
        raise RuntimeError(UNFIT)
    # the check: an addition is checked by taking one number from the claimed total; a subtraction by
    # adding the claimed answer back to the number taken away
    check_text = f"{claimed} − {b} = □" if op == "+" else f"{claimed} + {b} = □"
    check_value = claimed - b if op == "+" else claimed + b
    right = claimed == exact
    rs = [
        Response(
            "check",
            "digits",
            str(check_value),
            cells=_cells(max(check_value, claimed)),
            label=check_text,
            misconceptions={"M_ADD_INSTEAD": claimed + b}
            if op == "+"
            else {"M_SUB_INSTEAD": abs(claimed - b)},
        ),
        Response(
            "right",
            "tick",
            "yes" if right else "no",
            options=["yes", "no"],
            label="Is the answer right?",
            misconceptions={"M_REVERSES_CLAIM_TRUTH": "no" if right else "yes"},
        ),
    ]
    shown = f"{a} {_sign(op)} {b} = {claimed}"
    other = "a subtraction" if op == "+" else "an addition"
    spec = dict(
        a=a, b=b, op=op, claimed=claimed, shown=shown, check=check_text, ops=[op, "-" if op == "+" else "+"]
    )
    return _item(
        "CHECK", rung, signal, "inverse_check", f"Check {shown} with {other}.", spec, rs, working_lines=2
    )
