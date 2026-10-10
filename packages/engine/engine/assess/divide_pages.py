"""Division's written methods as the child meets them on the page (`divide_methods`, ADR 0063): every step a box where
it is worked, set out as the school sets the method out. Pure: HTML fragments, read back by the key's geometry
(`render.render_sheet`), so the reader finds every box and marking marks each by itself. Partitioning prints as
multiplication's does (`written_pages.partitioning`), a remainder after "r" beside its part.

Chunking: the number divided at the top; for each place, a row with what is taken away and its lots beside it, and a
row with what is left, ruled under; then the lots added. Long division: the quotient's boxes over the number divided's
last digits, the divisor and its bracket, then each product, ruled under, and each number left with its digit brought
down, a row each, its boxes under the digits it is worked on."""

from collections.abc import Callable
from typing import Any

from engine.assess import divide_methods as DVM
from engine.assess.answer_space import with_remainder
from engine.assess.items import Response
from engine.assess.written_pages import digits

Boxes = Callable[[Response, bool], str]


def _steps(R: dict[str, Response]) -> list[Response]:
    return [r for rid, r in R.items() if rid.startswith("s")]


def _quotient(R: dict[str, Response], box: Boxes, big: bool) -> str:
    rem = R.get("rem")
    return with_remainder(box(R["ans"], big), box(rem, big) if rem else None)


def chunking(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    """96 ÷ 4: 96; − □□ (□□ × 4), □□ left; − □□ (□ × 4), □ left; 96 ÷ 4 = □□. Every number right-aligned by its ones
    under the number divided, so each box is where the child writes it."""
    a, b = sp["a"], sp["b"]
    steps, width = _steps(R), len(str(a))
    rows = f'<span></span><span class="xn">{digits(a, width)}</span><span></span>'
    for lots, chunk, left in zip(steps[0::3], steps[1::3], steps[2::3], strict=True):
        rows += (
            f'<span class="xop">−</span><span class="xn">{box(chunk, big)}</span>'
            f'<span class="lab">({box(lots, big)} × {b})</span>'
            f'<span></span><span class="xn sum">{box(left, big)}</span><span class="lab">left</span>'
        )
    total = f'<div class="row step"><span class="eq">{a} ÷ {b} =</span>{_quotient(R, box, big)}</div>'
    return f'<div class="chunk" style="--w:{width}">{rows}</div>{total}'


def long_division(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    """516 ÷ 4: the quotient's boxes over the 5, 1 and 6; 4 and its bracket over 516; then 4 under the 5, ruled; 11
    under the 5 and the 1; 8 under the 1, ruled; 36 under the 1 and the 6; 36, ruled; 0 under the 6. Each row starts
    where its last digit lands (`--at`, in columns from the number divided's first digit)."""
    a, b = sp["a"], sp["b"]
    width, turns = len(str(a)), DVM.cycles(a, b)
    # the digits the first number divided takes: 2 for 279 ÷ 3, whose 2 is too small to divide
    first = len(str(turns[0][0]))

    def at(r: Response, end: int, cls: str = "") -> str:
        return f'<div class="ld{cls}" style="--at:{end + 1 - len(r.answer)}">{box(r, big)}</div>'

    steps = _steps(R)
    rows = [
        f'<div class="ld" style="--at:{width - len(R["ans"].answer)}">{_quotient(R, box, big)}</div>',
        f'<div class="ld head"><span class="dv">{b}</span><span class="dd">{digits(a, width)}</span></div>',
    ]
    for j, (product, left) in enumerate(zip(steps[0::2], steps[1::2], strict=True)):
        end = first - 1 + j
        rows += [at(product, end, " sub"), at(left, end + 1 if j < len(turns) - 1 else end)]
    return f'<div class="longdiv">{"".join(rows)}</div>'


DRAW: dict[str, Callable[[dict[str, Any], dict[str, Response], Boxes, bool], str]] = {
    "chunking": chunking,
    "long_division": long_division,
}
