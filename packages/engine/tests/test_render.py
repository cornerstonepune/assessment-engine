"""How a question is drawn for the child (assess/render.py, goals/s15-answer-boxes.yaml). Pure: HTML only."""

import re

import pytest

from engine.assess import answer_space, render
from engine.assess import items as I
from engine.assess.pick import Sheet
from engine.assess.words import word_2step


def _html(it):
    return render.render_item(Sheet("CS000000", "G2", "Easy", 1, "W1", [it]), it, 1)


def _boxes(html, rid="ans"):
    return len(re.findall(rf'class="(?:g ans )?cell[^"]*"[^>]*data-r="{rid}"', html))


@pytest.mark.parametrize(
    "a,b,op,layout,answer",
    [
        (4, 3, "+", "horizontal", "7"),
        (23, 45, "+", "horizontal", "68"),
        (68, 47, "+", "horizontal", "115"),
        (23, 45, "+", "column", "68"),
        (68, 47, "+", "column", "115"),
        (105, 97, "-", "column", "8"),  # three columns to line the numbers up, one box to write in
    ],
)
def test_there_are_as_many_answer_boxes_as_the_answer_has_digits(a, b, op, layout, answer):
    """Nimish, 2026-09-23: "use the number of boxes for the number of digits in the answer" — four boxes for a
    one- or two-digit answer confused the children."""
    it = I.bare_sum(
        __import__("random").Random(1), "R0", "Procedural", op, len(str(a)), len(str(b)), {0, 1, 2}
    )
    it.spec.update(a=a, b=b, op=op, layout=layout)
    ans = next(r for r in it.responses if r.rid == "ans")
    ans.answer = answer
    html = _html(it) if layout == "horizontal" else answer_space._grid("S", "I", [a, b], op, ans)
    assert _boxes(html) == len(answer)


def test_a_question_of_two_steps_gets_the_most_room_to_work():
    it = word_2step(__import__("random").Random(3), "R0", "Application", 3)
    assert 'class="work h4"' in _html(it)
    heights = dict(re.findall(r"\.work\.(h\d) \{ min-height: (\d+)mm; \}", render.CSS))
    assert int(heights["h4"]) >= 34 and int(heights["h2"]) >= 20
