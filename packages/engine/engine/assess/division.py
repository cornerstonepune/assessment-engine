"""A division's answer boxes (goals/md3a-straight-division.yaml): the quotient's, and the remainder's after "r" only
where there is one (ADR 0056), each keyed by the value every mistake `div_mistakes` predicts a child writes in it. In a
line 85 ÷ 4 reads "85 ÷ 4 = □ r □"; in the division layout the quotient's boxes stand over the number divided, one to
a digit (`answer_space.divided`), and each remainder exchanged into the next digit is written small, in a box of its
own (`exchanges`, goals/md3d-division-methods.yaml). Pure: no I/O."""

from . import div_mistakes as DM
from . import operations as O
from .items import Response, cells

PLACES = ("ones", "tens", "hundreds", "thousands")


def boxes(a: int, b: int, layout: str | None = "horizontal") -> list[Response]:
    """The quotient's box, then the remainder's where a ÷ b leaves one: 85 ÷ 4 is 21 and 1, 84 ÷ 4 is 21 alone. In the
    division layout ("column"), each exchange's box after them."""
    q, r = O.divide(a, b)
    out = [Response("ans", "digits", str(q), cells=cells(max(q, a)), misconceptions=DM.in_box(a, b, 0))]
    if r:
        out.append(
            Response("rem", "digits", str(r), cells=cells(b), misconceptions=DM.in_box(a, b, 1), label="r")
        )
    return out + (exchanges(a, b) if layout == "column" else [])


def _carried(a: int, b: int) -> list[tuple[int, int, int]]:
    """(the place, from the left, of the digit an exchange is written before; the number divided there; the remainder
    it leaves) for each exchange, divided from the left. Only a 1-digit divisor is divided digit by digit."""
    s, r = str(a), 0
    out: list[tuple[int, int, int]] = []
    if 2 <= b <= 9:
        for i, d in enumerate(s[:-1]):
            partial = r * 10 + int(d)
            r = partial % b
            if r:
                out.append((i + 1, partial, r))
    return out


def exchanges(a: int, b: int) -> list[Response]:
    """Short division's exchanges (G23), each the remainder one digit leaves, written small before the next digit:
    72 ÷ 4 exchanges 3 into the ones; 156 ÷ 4 exchanges the 1 it could not divide into the tens, then 3 into the ones;
    a digit that divides exactly exchanges nothing. Each is the remainder of the number divided at that step, so its
    box names that small division's remainder slips (7 ÷ 4: the 7 carried whole, its quotient written instead)."""
    places = len(str(a)) - 1
    return [
        Response(
            f"x{k}",
            "digits",
            str(r),
            cells=1,
            misconceptions=DM.in_box(partial, b, 1),
            label=f"exchanged into the {PLACES[places - at]}",
        )
        for k, (at, partial, r) in enumerate(_carried(a, b), start=1)
    ]


def exchanged(a: int, b: int) -> list[int]:
    """The places, from the left, of the digits a remainder is exchanged into: 72 ÷ 4 [1], 588 ÷ 3 [1, 2]."""
    return [at for at, _, _ in _carried(a, b)]
