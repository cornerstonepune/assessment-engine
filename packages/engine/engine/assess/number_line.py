"""The number line, one kind of question drawn three ways (goals/md2d1-multiplication-models.yaml,
goals/md3c-division-models.yaml): an addition or a subtraction as two jumps from a number (`two_jumps`), a
multiplication as equal jumps from 0 (`equal_jumps`), a division as jumps back to 0 (`divide_models.jumps_back`). A
level's rule reaches it through `number_line`, which reads the operation and hands on. Pure, no I/O.
"""

from random import Random
from typing import Any

from . import divide_models as DMOD
from . import misconceptions as M
from . import operations as O
from .counting import one_of
from .items import Item, Response, cells, item
from .misconceptions import named


def number_line(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """A number line drawn from a level's rule: × as equal jumps from 0, ÷ as jumps back to 0
    (`divide_models.jumps_back`); + and − as two jumps within the level's `hi`."""
    op = O.sign(one_of(rule["op"], rng))
    if op == "×":
        return equal_jumps(rng, rung, signal, rule)
    if op == "÷":
        return DMOD.jumps_back(rng, rung, signal, rule)
    return two_jumps(rng, rung, signal, op, rule["hi"])


def equal_jumps(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """4 jumps of 3 from 0 land on 12: `a` jumps (`groups`) of `b` (`size`), drawn on the line, the landing asked. The
    numbers added, one jump, and one jump fewer — the start counted as a jump — are the mistakes it names."""
    groups: list[int] = rule.get("groups") or [2, 5]
    size: list[int] = rule.get("size") or [2, 5]
    a, b = rng.randint(int(groups[0]), int(groups[-1])), rng.randint(int(size[0]), int(size[-1]))
    mis = named(a * b, [("M_WRONG_OP", a + b), ("M_ONE_GROUP", b), ("M_GROUP_MISSED", (a - 1) * b)])
    r = Response("ans", "digits", str(a * b), cells=cells(a * b), misconceptions=mis)
    spec = {"a": a, "b": b, "op": "×", "method": "NUMBER_LINE"}
    stem = f"Make {a} jumps of {b} from 0. Where does the last jump land?"
    return item("NLINE.TIMES", rung, signal, "number_line_jumps", stem, spec, [r], working_lines=0)


def _bridge_jump(rng: Random, op: str, hi: int, tries: int = 200) -> tuple[int, int, int]:
    """A jump that crosses exactly one ten, for a small range: the first hop lands on the ten,
    the second finishes. That bridge is the strategy R2 ("within 20, crossing ten") teaches.
    Returns (a, b, land1)."""
    if hi < 12:
        raise RuntimeError(f"no bridging jump below hi=12; got {hi}")
    for _ in range(tries):
        if op == "+":
            a = rng.randint(3, min(hi - 3, 18))
            if a % 10 == 0:
                continue
            to_ten = 10 - (a % 10)
            hi_b = min(9, hi - a)
            if hi_b <= to_ten:
                continue
            return a, rng.randint(to_ten + 1, hi_b), a + to_ten
        a = rng.randint(11, hi)
        ones = a % 10
        if ones in (0, 9):
            continue  # ones == 9 leaves no b that both crosses the ten and stays single-digit
        b = rng.randint(ones + 1, 9)
        if a - b < 1:
            continue
        return a, b, a - ones
    raise RuntimeError(f"no bridging jump within hi={hi}")


def two_jumps(rng: Random, rung: str, signal: str, op: str | None, hi: int) -> Item:
    """a ± b shown as two jumps. Landing boxes + answer are responses.

    Above hi=54 the jump splits into tens then ones. Below it there is no room for an 11-39
    second jump, so the jump bridges the next ten instead — the same picture at the scale a
    "within 20" rung actually works at."""
    op = O.require("number_line_jumps", op)
    if hi < 54:
        a, b, land1 = _bridge_jump(rng, op, hi)
        ans = a + b if op == "+" else a - b
        first = abs(land1 - a)
        rs = [
            Response(
                "land1",
                "digits",
                str(land1),
                cells=cells(hi),
                label=f"after {op}{first}",
                misconceptions={"M_FACT_PM1": land1 + (1 if op == "+" else -1)},
            ),
            Response("ans", "digits", str(ans), cells=cells(hi), misconceptions=M.predict(op, a, b)),
        ]
        # `tens`/`ones` are the renderer's names for the two jump sizes, whatever their place value.
        return item(
            "NLINE.BRIDGE",
            rung,
            signal,
            "number_line_jumps",
            f"Complete {a} {op} {b}. Use the number line to help you.",
            dict(a=a, b=b, op=op, tens=first, ones=b - first),
            rs,
            scaffolded=True,
            working_lines=0,
        )
    if op == "+":
        a = rng.randint(hi // 4, hi - 40)
        b = rng.randint(11, 39)
        while b % 10 == 0:
            b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a + tens
        ans = a + b
    else:
        a = rng.randint(hi // 2, hi - 1)
        b = rng.randint(11, 39)
        while b % 10 == 0 or b >= a:
            b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a - tens
        ans = a - b
    rs = [
        Response(
            "land1",
            "digits",
            str(land1),
            cells=cells(hi),
            misconceptions={"M_FACT_PM10": land1 + (10 if op == "+" else -10)},
            label=f"after {op}{tens}",
        ),
        Response("ans", "digits", str(ans), cells=cells(hi), misconceptions=M.predict(op, a, b)),
    ]
    return item(
        "NLINE",
        rung,
        signal,
        "number_line_jumps",
        f"Complete {a} {op} {b}. Use the number line to help you.",
        dict(a=a, b=b, op=op, tens=tens, ones=ones),
        rs,
        scaffolded=True,
        working_lines=0,
    )
