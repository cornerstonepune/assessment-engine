"""How a question is drawn for the child (assess/render.py, goals/s15-answer-boxes.yaml). Pure: HTML only."""

import json
import re

import pytest

from engine.assess import answer_space, render
from engine.assess import items as I
from engine.assess.pick import Sheet
from engine.assess.words import word_2step
from engine.core import db


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
    html = _html(it) if layout == "horizontal" else answer_space.grid("S", "I", [a, b], op, ans)
    assert _boxes(html) == len(answer)


@pytest.mark.parametrize(
    "a, b, rows",
    [(68, 17, 2), (47, 23, 2), (213, 12, 2), (17, 68, 2), (68, 7, 0), (7, 68, 0), (23, 40, 0), (45, 10, 0)],
)
def test_a_long_multiplication_prints_a_row_for_each_digit_of_its_multiplier(a, b, rows):
    """Set out as the school writes it (goals/md2a-straight-multiplication.yaml, G12): a row for each digit of the
    multiplier, the last with its + sign, then the answer. A 1-digit multiplier, or one whose ones are 0 (23 × 40 is
    one row), writes its answer straight under the line. The rows are room to work: only the answer's boxes are read."""
    ans = I.Response("ans", "digits", str(a * b), cells=len(str(a * b)) + 1)
    html = answer_space.grid("S", "I", [a, b], "×", ans)
    assert html.count('class="g op"') - 2 == rows  # two numbers' rows, then the rows worked
    assert ('<div class="g op">+</div>' in html) == bool(rows)
    assert not re.search(r'class="g worked"[^>]*data-', html)  # no answer box among them
    assert _boxes(html) == len(str(a * b))


def _times_item(a, b):
    from engine.assess import verify

    return verify.to_item(
        {
            "format": "column_grid",
            "op": "×",
            "a": a,
            "b": b,
            "answer": a * b,
            "stem": "",
            "missing": None,
            "misconceptions": [],
        },
        "R40",
    )


def test_a_long_multiplications_rows_are_working_the_reader_never_reads_as_its_answer(tmp_path):
    """Rule 5's third signal stays its own: the rows are one working space, and none of it reaches an answer box once
    the reader's own inset is taken (`w3_read/boxes.py` WORK_INSIDE). A worksheet printed before the rows (layout
    2026-09-24) re-renders as it printed, with no rows and no extra working space (second reader, 2026-10-09)."""
    from playwright.sync_api import sync_playwright

    from engine.w3_read.boxes import WORK_INSIDE

    it = _times_item(68, 17)
    old = next(r for r in _layouts() if r["name"] == "2026-09-24")
    with sync_playwright() as pw:
        today = render.render_sheet(Sheet("CS0000A1", "G4", "Easy", 1, "W1", [it]), tmp_path, pw=pw)
        before = render.render_sheet(
            Sheet("CS0000A2", "G4", "Easy", 1, "W1", [it]), tmp_path, pw=pw, layout=old
        )
    mine = [g for g in today["geometry"] if g["item"] == it.item_id]
    digits = [g for g in mine if g["kind"] == "digit"]
    works = [g for g in mine if g["kind"] == "work"]
    assert (
        len(digits) == 4 and len(works) == 1
    )  # the answer's four boxes; the rows, the question's one working space
    for w in works:
        x0, y0, x1, y1 = (
            w["x"] + WORK_INSIDE,
            w["y"] + WORK_INSIDE,
            w["x"] + w["w"] - WORK_INSIDE,
            w["y"] + w["h"] - WORK_INSIDE,
        )
        for d in digits:
            apart = d["x"] + d["w"] <= x0 or d["x"] >= x1 or d["y"] + d["h"] <= y0 or d["y"] >= y1
            assert apart, (w, d)
    assert [g for g in before["geometry"] if g["item"] == it.item_id and g["kind"] == "work"] == []
    assert "worked" not in render.render_item(Sheet("S", "G4", "Easy", 1, "W1", [it]), it, 1, old)


def test_a_question_of_two_steps_gets_the_most_room_to_work():
    it = word_2step(__import__("random").Random(3), "R0", "Application", 3)
    assert 'class="work h4"' in _html(it)
    heights = dict(re.findall(r"\.work\.(h\d) \{ min-height: (\d+)mm; \}", render.CSS))
    assert int(heights["h4"]) >= 34 and int(heights["h2"]) >= 20


def _layouts():
    rows = json.loads((db.REPO_ROOT / "supabase" / "seed" / "config.json").read_text(encoding="utf-8"))[
        "config"
    ]
    return next(r["value"] for r in rows if r["key"] == "render.layouts")


def test_a_worksheet_draws_in_each_layout_the_school_has_printed():
    """Nimish, 2026-09-28, of the 23 Sep papers printed before L3: "Recover layout". The renderer draws a question
    in any layout a paper has printed in: before L3 an answer had the room its question set (four boxes for 68),
    from L3 as many boxes as the answer has digits, with taller working space and a stronger QR."""
    old, l3, *_, today = _layouts()
    it = I.bare_sum(__import__("random").Random(1), "R0", "Procedural", "+", 2, 2, {0, 1, 2})
    it.spec.update(a=23, b=45, op="+", layout="horizontal")
    ans = next(r for r in it.responses if r.rid == "ans")
    ans.answer, ans.cells = "68", 4
    sheet = Sheet("CS000000", "G2", "Easy", 1, "W1", [it])

    assert _boxes(render.render_item(sheet, it, 1, old)) == 4
    assert _boxes(render.render_item(sheet, it, 1, today)) == 2
    assert _boxes(answer_space.grid("S", "I", [23, 45], "+", ans, boxes=old["boxes"])) == 4

    page = render.sheet_html(sheet, layout=old)
    assert ".work { min-height: 11mm; }" in page and ".work.h4 { min-height: 26mm; }" in page
    assert ".rowgroup .item .work { min-height: 9mm; }" in page
    # the QR as printed: the same code, drawn with the error correction of its day
    assert render.sheet_html(sheet, layout=old) != render.sheet_html(sheet, layout=l3)


def test_todays_layout_is_the_last_row_and_what_the_renderer_draws_with_none():
    """The page's own CSS and the last layout row are one thing: a row added without the renderer, or the
    renderer changed without a row, would print papers no row describes."""
    today = _layouts()[-1]
    heights = dict(re.findall(r"\.work(?:\.(h\d))? \{ [^}]*min-height: (\d+)mm;", render.CSS))
    assert [int(heights[k]) for k in ("", "h2", "h3", "h4")] == today["work_mm"]
    assert re.search(rf"\.rowgroup \.item \.work {{ min-height: {today['paired_work_mm']}mm; }}", render.CSS)
    sheet = Sheet("CS000000", "G2", "Easy", 1, "W1", [])
    assert render.sheet_html(sheet) == render.sheet_html(sheet, layout=today)


def test_a_batch_shares_one_browser_however_many_papers_it_renders(tmp_path):
    """A batch passes its one Playwright to every paper (the maker, a class's pack). Each paper still launched a
    browser of its own, so a class-sized batch could outlive the website's 30 s wait while the engine went on making
    every paper (code review, 2026-09-30; goals/p0-the-maker-makes-what-it-shows.yaml)."""
    from playwright.sync_api import sync_playwright

    it = I.bare_sum(__import__("random").Random(1), "R0", "Procedural", "+", 2, 2, {0, 1, 2})
    with sync_playwright() as pw:
        launches, real = [], pw.chromium.launch
        pw.chromium.launch = lambda *a, **k: launches.append(1) or real(*a, **k)
        for n in range(3):
            render.render_sheet(Sheet(f"CS00000{n}", "G2", "Easy", 1, "W1", [it]), tmp_path, pw=pw)
    assert len(launches) == 1
    assert sorted(p.name for p in tmp_path.glob("*.pdf")) == ["CS000000.pdf", "CS000001.pdf", "CS000002.pdf"]


def test_a_question_asked_in_words_prints_its_sentence_and_one_with_an_instruction_its_numbers():
    """ "How many 6s make 42?" prints the sentence alone, never the ÷ that gives it away; a sum whose sentence is only an
    instruction ("Add them in the easiest order.") still prints its numbers under it. The one carries its printed
    sentence (`text`), as a missing number does; the other only a stem."""
    from engine.assess import verify

    def text(it):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", _html(it)))

    worded = verify.division(42, 6, "R42", shape="HOW_MANY_GROUPS")
    assert "How many 6s make 42?" in text(worded) and "÷" not in text(worded)
    pairs = I.multi_add(__import__("random").Random(3), "R0", "Procedural", xs=[37, 48, 63], layout="horizontal",
                        shape="FRIENDLY_PAIRS")  # fmt: skip
    assert "Add them in the easiest order." in text(pairs) and "37 + 48 + 63 =" in text(pairs), text(pairs)


@pytest.mark.parametrize("a,b", [(84, 4), (156, 4), (85, 4), (804, 4)])
def test_a_division_in_the_division_layout_has_its_quotient_above_the_number_divided(a, b):
    """The division layout as the school writes it (D01, 84 ÷ 4): the quotient's boxes on top, one over each digit of
    the number divided, so 156 ÷ 4 = 39 is written over its 5 and 6 and the box over the 1 stays empty; then the divisor
    and the number divided under its bar; a remainder's box after "r" where there is one (goals/md3a-straight-division).
    A small box stands before every digit but the first, read where a remainder is exchanged into it (156 ÷ 4: the 1
    into the tens, 3 into the ones; goals/md3d-division-methods.yaml)."""
    from engine.assess import verify

    it = verify.division(a, b, "R45", layout="column")
    html = _html(it)
    assert it.fmt == "column_grid" and _boxes(html) == len(str(a))
    divided = re.findall(r'class="g dd[^"]*">(?:<span class="xc"[^>]*></span>)?(\d)<', html)
    assert divided == list(str(a)) and re.findall(r'class="g dv">(\d+)<', html) == [str(b)]
    assert html.index('data-r="ans"') < html.index('class="g dv"') < html.index('class="g dd')
    assert _boxes(html, "rem") == (len(str(a % b)) if a % b else 0)
    assert html.count('class="xc"') == len(str(a)) - 1
    exchanged = [r.rid for r in it.responses if r.rid.startswith("x")]
    assert [len(re.findall(rf'class="xc" [^>]*data-r="{x}"', html)) for x in exchanged] == [1] * len(
        exchanged
    )


def test_a_divisions_boxes_are_where_the_printed_key_says_they_are(tmp_path):
    """A sheet of divisions, in a line and in the division layout, with and without a remainder, printed through
    Chromium as a paper is: the key's geometry holds each answer's boxes, the quotient's and the remainder's, so the
    reader finds every one and marking marks each by itself."""
    from collections import Counter

    from engine.assess import verify

    its = [
        verify.division(84, 4, "R44"),
        verify.division(85, 4, "R44"),
        verify.division(156, 4, "R45", layout="column"),
        verify.division(457, 3, "R45", layout="column"),
        verify.division(4567, 100, "R43"),
    ]
    key = render.render_sheet(Sheet("CS00D3A1", "G4", "Hard", 1, "W1", its), tmp_path)
    boxes = Counter((g["item"], g["resp"]) for g in key["geometry"] if g["kind"] == "digit")
    for it in its:
        laid = it.fmt == "column_grid"
        for r in it.responses:
            want = len(str(it.spec["a"])) if laid and r.rid == "ans" else len(r.answer)
            assert boxes[(it.item_id, r.rid)] == want, (it.spec, r.rid, boxes[(it.item_id, r.rid)])
