"""A division's answer boxes (goals/md3a-straight-division.yaml): the quotient's, and the remainder's after "r" only
where there is one (ADR 0056), each keyed by the value every mistake `div_mistakes` predicts a child writes in it. In a
line 85 ÷ 4 reads "85 ÷ 4 = □ r □"; in the division layout the quotient's boxes stand over the number divided, one to
a digit (`answer_space.divided`). Pure: no I/O."""

from . import div_mistakes as DM
from . import operations as O
from .items import Response, cells


def boxes(a: int, b: int) -> list[Response]:
    """The quotient's box, then the remainder's where a ÷ b leaves one: 85 ÷ 4 is 21 and 1, 84 ÷ 4 is 21 alone."""
    q, r = O.divide(a, b)
    out = [Response("ans", "digits", str(q), cells=cells(max(q, a)), misconceptions=DM.in_box(a, b, 0))]
    if r:
        out.append(
            Response("rem", "digits", str(r), cells=cells(b), misconceptions=DM.in_box(a, b, 1), label="r")
        )
    return out
