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
    html = _html(it) if layout == "horizontal" else answer_space._grid("S", "I", [a, b], op, ans)
    assert _boxes(html) == len(answer)


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
    old, l3, today = _layouts()
    it = I.bare_sum(__import__("random").Random(1), "R0", "Procedural", "+", 2, 2, {0, 1, 2})
    it.spec.update(a=23, b=45, op="+", layout="horizontal")
    ans = next(r for r in it.responses if r.rid == "ans")
    ans.answer, ans.cells = "68", 4
    sheet = Sheet("CS000000", "G2", "Easy", 1, "W1", [it])

    assert _boxes(render.render_item(sheet, it, 1, old)) == 4
    assert _boxes(render.render_item(sheet, it, 1, today)) == 2
    assert _boxes(answer_space._grid("S", "I", [23, 45], "+", ans, boxes=old["boxes"])) == 4

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
