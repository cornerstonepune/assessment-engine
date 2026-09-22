"""The geometry that turns OCR words into a child's answers. No network: the cases here are the
ones a real page produced, written down as boxes.

Measured on that page after these rules: 14 of 14 ordinary answer boxes read exactly right, against
9 of 14 for the vision model it replaced.
"""

from engine.adapters import ocr

ROW_BAND = ocr.DEFAULTS["row_band"]


def w(text, x, y, hand=True, conf=99.0, h=0.012, width=0.04, line="", mixed=True):
    """A word as `assemble` builds it: it knows the line it sits on and whether that line mixes the
    paper's printed text with the child's handwriting."""
    return {
        "text": text,
        "x": x,
        "y": y,
        "w": width,
        "h": h,
        "hand": hand,
        "confidence": conf,
        "mixed_line": mixed,
        "line_text": line,
    }


def page(words, lines):
    return {"words": words, "lines": lines}


def box(anchor, bottom=None):
    """The region `answers_for` builds around a question with one part."""
    return {
        "top": anchor["y"] - anchor["h"],
        "bottom": bottom if bottom is not None else anchor["y"] + 0.095,
        "left": anchor["x"] - 0.085,
        "right": anchor["x"] + max(anchor["w"], 0.085) + 0.085,
    }


def test_a_printed_number_is_never_the_childs_answer():
    """Q5 prints "452 = 400 + [ ] + 12". The 452 and the 12 are the paper's; only the 0 is the
    child's. Before Textract's handwriting flag was used, the printed 452 was returned as the
    answer."""
    anchor = w("452 = 400 +", 0.13, 0.72, hand=False, width=0.30)  # an inline line is wide
    p = page([w("452", 0.14, 0.75, hand=False), w("0", 0.26, 0.75)], [anchor])
    assert [c["text"] for c in ocr._handwriting_near(p, box(anchor))] == ["0"]


def test_the_neighbouring_boxs_answer_is_not_a_candidate():
    """Four boxes across a page sit about 0.19 apart. At a 0.13 column tolerance question 1a's
    answer was a candidate for 1b and won on a rounding tie, which is how 245 became 155."""
    anchor = w("236 + 9 =", 0.313, 0.239, hand=False)
    p = page([w("155", 0.186, 0.313), w("245", 0.378, 0.310)], [anchor])
    assert [c["text"] for c in ocr._handwriting_near(p, box(anchor))] == ["245"]


def test_the_labelled_answer_box_beats_a_number_left_in_the_working():
    """On 4c the working shows 284 and the answer line 384. The paper's own "Answer:" label says
    which one the child is standing behind."""
    anchor = w("342 - 58 =", 0.51, 0.62, hand=False)
    label = w("Answer: 384", 0.51, 0.70, hand=False)
    p = page([w("284", 0.52, 0.66, line="284"), w("384", 0.56, 0.70, line="Answer: 384")], [anchor, label])
    assert [c["text"] for c in ocr._handwriting_near(p, box(anchor))] == ["384"]


def test_slots_sharing_a_line_take_the_handwriting_in_reading_order():
    anchor = w("452 = 400 +", 0.13, 0.72, hand=False, width=0.30)  # an inline line is wide
    p = page([w("0", 0.26, 0.75), w("52", 0.33, 0.75)], [anchor])
    got = ocr.answers_for(p, {"5a": "452 = 400 +", "5b": "452 = 400 +"})
    assert [got["5a"]["child_answer"], got["5b"]["child_answer"]] == ["0", "52"]


def test_a_region_that_does_not_add_up_goes_to_a_person_rather_than_being_guessed():
    """Three printed boxes and two numbers found means the region was not understood. Assigning
    positionally would give a child's graph an answer chosen by an off-by-one; the bar
    `silently_wrong_at_most` says a flagged unknown is cheaper than a confident guess."""
    anchor = w("452 = 400 +", 0.13, 0.72, hand=False, width=0.30)  # an inline line is wide
    p = page([w("0", 0.26, 0.75), w("52", 0.33, 0.75)], [anchor])
    got = ocr.answers_for(p, {"5a": "452 = 400 +", "5b": "452 = 400 +", "5c": "452 = 400 +"})
    assert {g["answer_state"] for g in got.values()} == {"illegible"}
    assert all(g["child_answer"] == "" for g in got.values())


def test_a_slot_whose_question_is_not_on_the_page_says_so():
    """Never silently missing: that defect lost three answers per child on every sheet of a paper."""
    p = page([], [w("something else entirely", 0.1, 0.1, hand=False)])
    got = ocr.answers_for(p, {"9": "Zara says 358 + 199 gives the same total"})
    assert got["9"]["answer_state"] == "not_found"


def test_a_question_is_found_despite_ocr_spacing():
    """'148 + 7 =' comes back as '148 +7 = 148' — the child's answer runs into the printed line."""
    lines = [w("148 +7 = 148", 0.12, 0.238, hand=False), w("236 + 9 =", 0.31, 0.239, hand=False)]
    assert ocr.find_question(lines, "148 + 7 =")["x"] == 0.12


def test_the_childs_rough_working_is_not_mistaken_for_an_answer():
    """Question 5's region holds the child's box-fills AND their scribbled working, which on this
    page included a second 52 and a second 72. A fill-in box sits on a line that mixes the paper's
    printed text with the child's writing; working stands on a line of its own."""
    anchor = w("452 = 400 +", 0.13, 0.72, hand=False, width=0.30)
    p = page(
        [
            w("0", 0.259, 0.750, line="452 = 400 + 0 + 52"),
            w("52", 0.316, 0.748, line="452 = 400 + 0 + 52"),
            w("52", 0.438, 0.789, line="52", mixed=False),  # working
            w("236", 0.413, 0.730, line="236", mixed=False),  # working
        ],
        [anchor],
    )
    assert [c["text"] for c in ocr._handwriting_near(p, box(anchor))] == ["0", "52"]


def test_a_line_of_pure_handwriting_is_working_and_a_mixed_line_is_an_answer():
    line = [
        {
            "Id": "L",
            "BlockType": "LINE",
            "Text": "452 = 400 + 0",
            "Confidence": 99.0,
            "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.7, "Width": 0.2, "Height": 0.01}},
            "Relationships": [{"Type": "CHILD", "Ids": ["w1", "w2"]}],
        }
    ]
    words = [
        {
            "Id": "w1",
            "BlockType": "WORD",
            "Text": "452",
            "TextType": "PRINTED",
            "Confidence": 99.0,
            "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.7, "Width": 0.03, "Height": 0.01}},
        },
        {
            "Id": "w2",
            "BlockType": "WORD",
            "Text": "0",
            "TextType": "HANDWRITING",
            "Confidence": 98.0,
            "Geometry": {"BoundingBox": {"Left": 0.25, "Top": 0.7, "Width": 0.02, "Height": 0.01}},
        },
    ]
    page_ = ocr.assemble(line + words)
    assert page_["lines"][0]["mixed"] is True
    assert {x["text"]: x["mixed_line"] for x in page_["words"]} == {"452": True, "0": True}


def test_a_skewed_scan_does_not_hand_a_child_their_neighbours_answer():
    """Four answers printed on one line came back at y = 0.302, 0.306, 0.310, 0.313 because the page
    sits a degree off square. Rounding y split them across two rows and put the rightmost first, so
    every child in that row got the next child's answer — silently, and at high confidence."""
    got = ocr._reading_order(
        [
            w("431", 0.696, 0.302),
            w("365", 0.507, 0.306),
            w("245", 0.317, 0.310),
            w("155", 0.124, 0.313),
        ],
        ROW_BAND,
    )
    assert [x["text"] for x in got] == ["155", "245", "365", "431"]


def test_a_genuine_second_row_is_still_a_second_row():
    got = ocr._reading_order([w("b", 0.30, 0.42), w("a", 0.12, 0.40), w("c", 0.12, 0.50)], ROW_BAND)
    assert [x["text"] for x in got] == ["a", "b", "c"]


def test_a_question_with_no_handwriting_is_blank_not_unreadable():
    """Rule 5: "the child wrote nothing" and "there is writing I cannot make out" are different
    facts everywhere, and a blank never counts as an attempt. Reporting a blank as unreadable sends
    a teacher to look at an empty box and turns "did not answer" into "could not be read"."""
    anchor = w("Zara says 358 + 199 gives the same", 0.12, 0.40, hand=False, width=0.60)
    got = ocr.answers_for(page([], [anchor]), {"9": "Zara says 358 + 199 gives the same"})
    assert got["9"]["answer_state"] == "blank"
    assert got["9"]["child_answer"] == ""


def test_geometry_comes_from_rows_not_from_the_code():
    """Rule 1: nothing structural lives in Python. Every number the transcriber was tuned on is a
    property of how a PAPER is laid out, so the next paper changes a row rather than a file."""
    assert set(ocr.DEFAULTS) == {
        "min_confidence",
        "answer_column",
        "answer_drop",
        "row_band",
        "first_page_mask",
        "box_min_width",
        "box_min_height",
        "box_max_width",
        "box_ink_blank",
        "red_pen_mask",
        "reread_dpi",
        "reread_pad",
        "stencil_min_inliers",
        "stencil_empty",
    }
    assert ocr.settings(None) == ocr.DEFAULTS  # no database: the measured defaults


def test_a_question_matches_despite_a_token_the_page_lost():
    """Textract read the printed "234 + 178" as "234 + 78" — the child's own "No." loops over the
    1. Advancing only on a hit stopped counting at the first token it could not find, so the
    question scored 3 of 8 against a 0.6 bar, never anchored, and a correct answer was lost."""
    line = w("15. Aryan solved 234 + 78 and got 302. Is he correct?", 0.14, 0.10, hand=False, width=0.6)
    found = ocr.find_question(
        [line], "Aryan solved 234 + 178 and got 302. Is he correct? If not, write the correct answer."
    )
    assert found is line


def test_the_answer_need_not_be_the_last_thing_on_the_line():
    """The child's 412 came back from Textract as "412-": the printed answer line runs into the
    digits. An end-anchored match found no number there at all, and a page holding a correct answer
    was recorded as blank."""
    assert ocr.value_of("412-") == "412"
    assert ocr.value_of("ans=43") == "43"
    assert ocr.value_of("No.") is None


def test_an_answer_that_is_not_a_number_goes_to_a_person_rather_than_being_called_blank():
    """ "Compare using >, <, or =: 456 [ ] 465" is answered with a symbol. This reader reads numbers,
    so it cannot tell a child who wrote "<" from one who wrote nothing — and `blank` is not a flag,
    it is a claim that the child did not attempt the skill. That claim went into a Grade 3 graph on
    a question the child got right."""
    anchor = w("13. Compare using >, <, or =: 456", 0.10, 0.73, hand=False, width=0.31)
    p = page([w("<", 0.35, 0.73, conf=55.7, line="13. Compare using >, <, or =: 456 < 465")], [anchor])
    q = {"13": "Compare using >, <, or =: 456 ___ 465"}
    # The paper row knows its answer is not a number, so this slot can never be read at all.
    assert ocr.answers_for(p, q, symbolic={"13"})["13"]["answer_state"] == "illegible"
    # Untold, a one-character mark on the line reads as an educator's cross and the slot as blank —
    # which is exactly why a symbolic slot is named in the paper row and never left to inference.
    assert ocr.answers_for(p, q)["13"]["answer_state"] == "blank"


def test_writing_on_the_papers_own_line_is_never_reported_as_a_blank():
    """A child wrote "40" and Textract read the word `to`. With no number in the region that came
    back BLANK at full confidence — the engine asserting the child did not attempt the skill."""
    anchor = w("3. 31 + 26 =", 0.076, 0.608, hand=False, width=0.30)
    p = page([w("to", 0.451, 0.608, conf=99, line="3. 31 + 26 = to")], [anchor])
    assert ocr.answers_for(p, {"3": "31 + 26 ="})["3"]["answer_state"] == "illegible"


def test_an_educators_cross_beside_an_empty_answer_leaves_it_blank():
    """The other half of the same rule, and the one that must not regress: every Grade 3 answer
    carries a tick or a cross beside it, and a cross over an empty line is a blank. An educator
    marks in the margin, on a line of their own; a child writes into the paper's line."""
    anchor = w("2. What is the value of the digit 5 in 458?", 0.151, 0.191, hand=False, width=0.239)
    mark = w("X", 0.445, 0.192, conf=73, line="X x", mixed=False)
    p = page([mark], [anchor, w("X x", 0.445, 0.192, hand=False, width=0.045)])
    assert (
        ocr.answers_for(p, {"2": "What is the value of the digit 5 in 458?"})["2"]["answer_state"] == "blank"
    )


def test_every_reading_says_where_on_the_page_it_came_from():
    """The approval screen shows a teacher that patch of the photograph beside what the reader made
    of it. Without the region there is nothing to show but the whole page."""
    anchor = w("342 + 579 =", 0.13, 0.38, hand=False)
    p = page([w("763", 0.23, 0.39)], [anchor])
    got = ocr.answers_for(p, {"6": "342 + 579 ="})["6"]
    assert len(got["box"]) == 4
    assert got["box"][0] < 0.23 < got["box"][2]


def _page_with_boxes(rects, size=(800, 1000)):
    """A blank page with printed rectangles on it, as a scanner would hand it over."""
    import cv2
    import numpy as np

    img = np.full((size[1], size[0]), 255, np.uint8)
    for x0, y0, x1, y1 in rects:
        cv2.rectangle(
            img, (int(x0 * size[0]), int(y0 * size[1])), (int(x1 * size[0]), int(y1 * size[1])), 0, 2
        )
    return cv2.imencode(".jpg", img)[1].tobytes()


def test_the_paper_says_where_its_fields_are():
    """Every paper in the corpus prints its answer fields as rectangles. Finding them turns a
    recognition problem into a cropping problem, which is how forms have been read for decades."""
    rects = [(0.10, 0.20, 0.30, 0.30), (0.40, 0.20, 0.60, 0.30), (0.10, 0.50, 0.40, 0.58)]
    found = ocr.printed_boxes(_page_with_boxes(rects))
    assert len(found) == 3
    for want, got in zip(sorted(rects, key=lambda b: (b[1], b[0])), found):
        assert all(abs(a - b) < 0.01 for a, b in zip(want, got[:4]))
        assert got[4] < 0.002  # nothing written in it


def test_a_grids_outer_frame_is_not_a_field_but_its_cells_are():
    cells = [(0.1, 0.2, 0.3, 0.3), (0.3, 0.2, 0.5, 0.3)]
    found = ocr.printed_boxes(_page_with_boxes(cells + [(0.1, 0.2, 0.5, 0.3)]))
    assert len(found) == 2


def test_one_printed_box_is_one_answer_and_the_count_cannot_be_wrong():
    """Level D prints four boxes for four sums, and the child wrote each answer twice — once in the
    box and once on the Answer line. The region held eight numbers for four slots and all four went
    to a person. With the boxes known, each slot reads what is inside its own box."""
    anchors = [
        w(q, x, 0.24, hand=False)
        for q, x in (("4 + 3 =", 0.10), ("6 + 2 =", 0.32), ("5 + 4 =", 0.54), ("3 + 5 =", 0.76))
    ]
    boxes = [
        (0.08, 0.22, 0.28, 0.32),
        (0.30, 0.22, 0.50, 0.32),
        (0.52, 0.22, 0.72, 0.32),
        (0.74, 0.22, 0.94, 0.32),
    ]
    words = [
        w("55", 0.20, 0.24, line="4 + 3 = 55"),
        w("55", 0.14, 0.30, line="Answer: 55"),
        w("45", 0.42, 0.24, line="6 + 2 = 45"),
        w("45", 0.36, 0.30, line="Answer: 45"),
        w("35", 0.64, 0.24, line="5 + 4 = 35"),
        w("35", 0.58, 0.30, line="Answer: 35"),
        w("61", 0.86, 0.24, line="3 + 5 = 61"),
        w("61", 0.80, 0.30, line="Answer: 61"),
    ]
    slots = {"1a": "4 + 3 =", "1b": "6 + 2 =", "1c": "5 + 4 =", "1d": "3 + 5 ="}
    got = ocr.answers_for(page(words, anchors), slots, boxes=boxes)
    assert [got[k]["child_answer"] for k in ("1a", "1b", "1c", "1d")] == ["55", "45", "35", "61"]
    assert all(got[k]["answer_state"] == "written" for k in slots)


def test_a_box_holding_only_printed_words_is_the_paper_not_a_field():
    """The pans of a balance scale print 40 and 30 in boxes; only the empty pan is the answer."""
    anchor = w("2 Write the missing number so that the scales balance.", 0.08, 0.40, hand=False, width=0.5)
    boxes = [
        (0.10, 0.42, 0.20, 0.47),
        (0.20, 0.42, 0.30, 0.47),
        (0.55, 0.42, 0.65, 0.47),
        (0.65, 0.42, 0.75, 0.47),
    ]
    words = [
        w("40", 0.14, 0.44, hand=False),
        w("30", 0.24, 0.44, hand=False),
        w("50", 0.59, 0.44),
        w("20", 0.69, 0.44, hand=False),
    ]
    got = ocr.answers_for(
        page(words, [anchor]), {"2": "Write the missing number so that the scales balance."}, boxes=boxes
    )
    assert (got["2"]["child_answer"], got["2"]["answer_state"]) == ("50", "written")


def test_working_above_an_answer_in_one_box_is_read_as_the_answer():
    """Two numbers in one box are the child's working and their answer, and the answer comes
    last — the rule a single-answer region has used since it was measured. Its known limit is a
    self-correction written beside the first attempt on the same row: the rightmost wins, which
    is a coin toss the confidence floor and the approval screen both stand behind."""
    anchor = w("1 Complete each addition.", 0.08, 0.20, hand=False, width=0.3)
    words = [w("55", 0.20, 0.24, line="4 + 3 = 55"), w("58", 0.14, 0.30, line="58")]
    got = ocr.answers_for(
        page(words, [anchor]), {"1": "Complete each addition."}, boxes=[(0.08, 0.22, 0.28, 0.32)]
    )
    assert (got["1"]["child_answer"], got["1"]["answer_state"]) == ("58", "written")


def test_an_empty_frame_beside_an_answer_on_a_line_is_not_a_blank():
    """The five silent errors the box path introduced, pinned: a decorative rectangle in the
    question's region matched a one-slot count, held nothing, and the answer written on the
    underline beside it was reported as never given."""
    anchor = w("2. What is the value of the digit 5 in 458?", 0.15, 0.19, hand=False, width=0.24)
    frame = (0.60, 0.20, 0.90, 0.28)
    words = [w("50", 0.45, 0.19, line="2. What is the value of the digit 5 in 458? 50")]
    got = ocr.answers_for(
        page(words, [anchor]), {"2": "What is the value of the digit 5 in 458?"}, boxes=[frame]
    )
    assert (got["2"]["child_answer"], got["2"]["answer_state"]) == ("50", "written")


def test_a_frame_around_a_number_line_is_not_a_field():
    """Level B prints a rectangle around each number line. It was counted as a field, the count
    happened to match, and one slot was handed the next box's answer."""
    found = ocr.printed_boxes(_page_with_boxes([(0.10, 0.50, 0.70, 0.56), (0.20, 0.60, 0.28, 0.63)]))
    assert [tuple(round(v, 2) for v in b[:4]) for b in found] == [(0.20, 0.60, 0.28, 0.63)]


def test_ink_in_a_box_with_no_readable_word_is_a_doubt_not_a_blank():
    """A child's faint "2" that Textract returns no word for is still ink."""
    import cv2
    import numpy as np

    img = np.full((1000, 800), 255, np.uint8)
    cv2.rectangle(img, (160, 600), (224, 630), 0, 2)
    cv2.rectangle(img, (400, 600), (464, 630), 0, 2)
    cv2.putText(img, "2", (175, 625), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    boxes = ocr.printed_boxes(cv2.imencode(".jpg", img)[1].tobytes())
    assert len(boxes) == 2
    inked, empty = sorted(boxes, key=lambda b: b[0])
    assert inked[4] > ocr.DEFAULTS["box_ink_blank"] > empty[4]
    # the printed instruction spans the row of boxes, as it does on the page
    anchor = w("Write the missing digits.", 0.10, 0.58, hand=False, width=0.5)
    got = ocr.answers_for(
        page([], [anchor]),
        {"6a": "Write the missing digits.", "6b": "Write the missing digits."},
        boxes=boxes,
    )
    assert (got["6a"]["answer_state"], got["6b"]["answer_state"]) == ("illegible", "blank")


def test_a_question_read_from_its_boxes_still_bounds_the_question_above_it():
    """Cambridge A, question 3: once question 4 was claimed by its printed boxes it dropped out of
    the ordering, question 3's region ran down over question 4's rows, and its Answer-line numbers
    made four candidates for three slots. A claimed question still occupies its rows."""
    q3 = [
        w(q, x, 0.48, hand=False) for q, x in (("165 - 7 =", 0.10), ("243 - 8 =", 0.34), ("352 - 6 =", 0.58))
    ]
    q4 = w("425 - 38 =", 0.10, 0.62, hand=False)
    box4 = (0.08, 0.60, 0.28, 0.70)
    words = [
        w("158", 0.12, 0.55, line="Answer: 158"),
        w("235", 0.36, 0.55, line="Answer: 235"),
        w("346", 0.60, 0.55, line="Answer: 346"),
        w("397", 0.12, 0.69, line="Answer: 397"),
    ]
    slots = {"3a": "165 - 7 =", "3b": "243 - 8 =", "3c": "352 - 6 =", "4a": "425 - 38 ="}
    page_ = page(words, q3 + [q4])
    page_["words"].append(w("425 - 38 =", 0.10, 0.62, hand=False))  # the label, inside its box
    got = ocr.answers_for(page_, slots, boxes=[box4])
    assert got["4a"]["child_answer"] == "397"
    assert [got[k]["child_answer"] for k in ("3a", "3b", "3c")] == ["158", "235", "346"]


def test_working_and_the_answer_in_one_box_read_as_the_answer():
    """Cambridge B, box 1d: the child stacks 55 + 6 in the box and writes 61 on the Answer line.
    Three numbers, one slot — and the box path called that a doubt while the region path had long
    since learned that the last number is the one the child stood behind."""
    anchor = w("55 + 6 =", 0.75, 0.24, hand=False)
    box = (0.73, 0.22, 0.93, 0.33)
    words = [
        w("55 + 6 =", 0.75, 0.24, hand=False),
        w("55", 0.80, 0.27, line="55"),
        w("6", 0.81, 0.29, line="+ 6"),
        w("61", 0.84, 0.32, line="Answer: 61"),
    ]
    got = ocr.answers_for(page(words, [anchor]), {"1d": "55 + 6 ="}, boxes=[box])
    assert (got["1d"]["child_answer"], got["1d"]["answer_state"]) == ("61", "written")


def test_an_expanded_form_written_as_one_token_is_three_answers():
    """Grade 3 baseline, question 3: "200+30+6" comes back from Textract as a single word, and
    three slots against one candidate went to a person on every child. The pieces are the
    answers when — and only when — there are exactly as many as the paper has slots."""
    anchor = w("3. Write 236 in expanded form:", 0.15, 0.22, hand=False, width=0.32)
    words = [w("200+30+6", 0.33, 0.22, line="3. Write 236 in expanded form: 200+30+6")]
    slots = {
        "3a": "Write 236 in expanded form:",
        "3b": "Write 236 in expanded form:",
        "3c": "Write 236 in expanded form:",
    }
    got = ocr.answers_for(page(words, [anchor]), slots)
    assert [got[k]["child_answer"] for k in ("3a", "3b", "3c")] == ["200", "30", "6"]


def test_a_compound_token_in_a_one_slot_region_is_still_working():
    anchor = w("452 - 236 =", 0.10, 0.60, hand=False)
    words = [w("452-236", 0.12, 0.64, line="452-236"), w("216", 0.14, 0.68, line="216")]
    got = ocr.answers_for(page(words, [anchor]), {"9": "452 - 236 ="})
    assert (got["9"]["child_answer"], got["9"]["answer_state"]) == ("216", "written")


def test_an_answer_written_on_the_questions_own_line_is_never_above_the_region():
    """Kabir's 5147 for 8,500 − 3,647, the finding Aseem's report is written around: a large
    handwritten answer on the printed line starts a little above the printed text, its top-left
    corner fell above the region's top, and the answer came back blank."""
    anchor = w("5. 8,500 - 3,647 =", 0.06, 0.490, hand=False, width=0.28, h=0.02)
    answer = w("5147", 0.36, 0.476, h=0.03, line="5. 8,500 - 3,647 =")
    got = ocr.answers_for(page([answer], [anchor]), {"5": "8,500 - 3,647 ="})
    assert (got["5"]["child_answer"], got["5"]["answer_state"]) == ("5147", "written")


def test_a_printed_operand_read_back_as_handwriting_is_never_the_answer():
    """Kabir's quiz: beside his large digits Textract tagged the printed 37,845 as handwriting at
    94%, and "8 x ___ = 72" gave back the printed 72 at 86%. Both were stood behind, both wrong.
    A number the question prints is an echo — working at best — and when nothing else was read,
    the answer goes to a person rather than to the graph."""
    anchor = w("1. 24,568 + 37,845 =", 0.06, 0.19, hand=False, width=0.30)
    # as the photograph came back: the child's copy of the operand on a line of its own, and
    # their answer read as a word — nothing left that is a number, and the child wrote something
    words = [
        # the paper's own 37,845, found a second time and tagged as handwriting, on top of it
        w("37,845", 0.162, 0.205, conf=94, h=0.04, width=0.10, line="37,845", mixed=False),
        w("37,845", 0.160, 0.203, hand=False, h=0.038, width=0.10),
        w("Elhlo", 0.29, 0.186, conf=64, h=0.036, line="Elhlo", mixed=False),
    ]
    got = ocr.answers_for(page(words, [anchor]), {"1": "24,568 + 37,845 ="})
    assert got["1"]["answer_state"] == "illegible"

    # the paper's 72, found a second time and tagged as handwriting, on top of where it is printed
    printed_72 = w("72", 0.36, 0.22, hand=False, width=0.03, h=0.012)
    anchor = w("13. Fill in the blank: 8 x", 0.10, 0.22, hand=False, width=0.30)
    words = [
        w("9", 0.30, 0.22, conf=95, line="13. Fill in the blank: 8 x 9 = 72"),
        w("72", 0.36, 0.22, conf=86, line="13. Fill in the blank: 8 x 9 = 72"),
    ]
    got = ocr.answers_for(page(words + [printed_72], [anchor]), {"13": "Fill in the blank: 8 x ___ = 72"})
    assert (got["13"]["child_answer"], got["13"]["answer_state"]) == ("9", "written")


def test_an_operand_copied_into_the_working_still_leaves_the_answer():
    anchor = w("342 + 579 =", 0.13, 0.38, hand=False)
    words = [
        w("342", 0.14, 0.40, line="342"),
        w("579", 0.14, 0.42, line="579"),
        w("921", 0.14, 0.44, line="921"),
    ]
    got = ocr.answers_for(page(words, [anchor]), {"6": "342 + 579 ="})
    assert (got["6"]["child_answer"], got["6"]["answer_state"]) == ("921", "written")


def test_a_word_on_the_printed_line_belongs_to_it_whatever_textract_grouped():
    """Kabir's 5147 again, the way the photograph actually came back: Textract gave the child's
    digits a line of their own, so a rule that trusted its grouping still reported a blank."""
    anchor = w("5. 8,500 - 3,647 =", 0.06, 0.490, hand=False, width=0.28, h=0.02)
    answer = w("5147", 0.36, 0.476, h=0.03, line="5147", mixed=False)
    got = ocr.answers_for(page([answer], [anchor]), {"5": "8,500 - 3,647 ="})
    assert (got["5"]["child_answer"], got["5"]["answer_state"]) == ("5147", "written")


def test_two_parts_a_tenth_of_a_page_apart_are_two_regions():
    """Week 1, question 13: (a) the largest total and (b) the smallest, each with its own working
    box. One region held both workings — six numbers for two slots — and both went to a person."""
    a13 = w("a What is the largest total Naomi can make?", 0.10, 0.33, hand=False, width=0.5)
    b13 = w("b What is the smallest total she can make?", 0.10, 0.44, hand=False, width=0.5)
    words = [
        w("963", 0.14, 0.36, line="963", mixed=False),
        w("841", 0.14, 0.38, line="841", mixed=False),
        w("1804", 0.14, 0.40, line="1804", mixed=False),
        w("149", 0.14, 0.47, line="149", mixed=False),
        w("368", 0.14, 0.49, line="368", mixed=False),
        w("517", 0.14, 0.51, line="517", mixed=False),
    ]
    slots = {
        "13a": "What is the largest total Naomi can make?",
        "13b": "What is the smallest total she can make?",
    }
    got = ocr.answers_for(page(words, [a13, b13]), slots)
    assert (got["13a"]["child_answer"], got["13b"]["child_answer"]) == ("1804", "517")


def test_three_consecutive_printed_lines_are_still_one_region():
    """Cambridge A, question 5 prints its three parts on three lines a line apart, and its parts
    match each other's lines. Those stay one region, read positionally, as they always were."""
    lines = [
        w("452 - 236. Regroup 452 into 400 +", 0.13, 0.70, hand=False, width=0.30),
        w("452 = 400 + 40 +", 0.13, 0.725, hand=False, width=0.30),
        w("452 - 236 =", 0.13, 0.75, hand=False, width=0.30),
    ]
    words = [w("0", 0.40, 0.70), w("52", 0.40, 0.725), w("72", 0.40, 0.75)]
    slots = {
        "5a": "452 - 236. Regroup 452 into 400 + [ ]",
        "5b": "452 = 400 + 40 + [ ]",
        "5c": "452 - 236 = [ ]",
    }
    got = ocr.answers_for(page(words, lines), slots)
    assert [got[k]["child_answer"] for k in ("5a", "5b", "5c")] == ["0", "52", "72"]


def test_an_answer_that_equals_an_operand_is_kept_wherever_the_child_wrote_it():
    """52 − 26 = 26 on every copy of the word paper, and the child who writes 26 below their
    working has answered it. The question mentioning 26 is no reason to doubt them — only the
    paper having printed 26 *in that spot* would be."""
    anchor = w(
        "2. There were 52 birds sitting on a tree. 26 birds flew away.", 0.10, 0.30, hand=False, width=0.6
    )
    q = {
        "2": "There were 52 birds sitting on a tree. 26 birds flew away. How many birds are left on the tree?"
    }
    for line, mixed in (("ans=26", False), ("26 birds are left on the tree", False), ("26", False)):
        got = ocr.answers_for(page([w("26", 0.30, 0.36, line=line, mixed=mixed)], [anchor]), q)
        assert got["2"]["child_answer"] == "26", line


def test_a_childs_neat_digits_tagged_as_print_still_make_their_brick_a_field():
    """The number wall: twelve bricks, six printed by the paper, six for the child — and one of the
    child's, a neat "19", came back tagged PRINTED. Seven printed-only boxes against the six the
    row lists: the surplus box with the most ink is the child's, and its digits are read as theirs."""
    region = {"top": 0.18, "bottom": 0.32, "left": -0.04, "right": 0.98}
    printed = [
        (0.07, 0.28, 0.16, 0.30, 0.082),
        (0.16, 0.28, 0.25, 0.30, 0.084),
        (0.26, 0.28, 0.35, 0.30, 0.092),
        (0.37, 0.28, 0.46, 0.30, 0.092),
        (0.42, 0.26, 0.50, 0.28, 0.095),
        (0.55, 0.28, 0.64, 0.30, 0.083),
    ]
    childs_tagged_printed = (0.46, 0.28, 0.55, 0.30, 0.117)
    childs = [
        (0.16, 0.23, 0.25, 0.26, 0.096),
        (0.46, 0.23, 0.55, 0.26, 0.139),
        (0.12, 0.26, 0.21, 0.28, 0.108),
        (0.21, 0.26, 0.30, 0.28, 0.106),
        (0.51, 0.26, 0.60, 0.28, 0.110),
    ]
    words = [
        w(str(n), b[0] + 0.02, b[1] + 0.005, hand=False) for n, b in zip((14, 19, 24, 26, 45, 41), printed)
    ]
    words.append(w("19", 0.48, 0.285, hand=False))
    words += [w(str(n), b[0] + 0.02, b[1] + 0.005) for n, b in zip((76, 105, 33, 43, 60), childs)]
    fields = ocr._fields_in(printed + [childs_tagged_printed] + childs, page(words, []), region, printed=6)
    assert len(fields) == 6
    trusted = next(f for f in fields if len(f) > 5)
    assert trusted[:5] == childs_tagged_printed
    assert ocr._read_field(page(words, []), trusted, ocr.DEFAULTS, "none")["child_answer"] == "19"


def test_red_ink_is_painted_out_and_pencil_is_not():
    """A red circle round 5147 read back as 147, at 95%."""
    import cv2
    import numpy as np

    img = np.full((300, 600, 3), 255, np.uint8)
    cv2.putText(img, "5147", (200, 160), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (40, 40, 40), 6)
    cv2.ellipse(img, (290, 140), (150, 70), 0, 0, 360, (30, 30, 220), 6)  # BGR red
    out = cv2.imdecode(
        np.frombuffer(ocr.mask_red_pen(cv2.imencode(".jpg", img)[1].tobytes()), np.uint8), cv2.IMREAD_COLOR
    )
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
    red_left = (
        cv2.inRange(hsv, (0, 80, 60), (12, 255, 255)) | cv2.inRange(hsv, (160, 80, 60), (180, 255, 255))
    ).sum()
    assert red_left == 0
    assert (out[100:170, 205:420].mean(axis=2) < 100).sum() > 2000  # the pencil digits survive
    assert ocr.mask_red_pen(b"", {"red_pen_mask": 0}) == b""


def test_a_truncated_thousands_number_is_not_a_value():
    assert ocr.value_of("24,") is None
    assert ocr.value_of("24,568") == "24568"


def test_an_answer_that_equals_a_printed_number_is_kept_where_the_paper_did_not_print_it():
    """The rule that broke two papers. "Find the missing number: 15 + ___ = 30" — the answer IS 15,
    written in the blank at 97%, and it was deleted because 15 appears in the question. So was the
    26 in "52 birds, 26 flew away". A number is the paper's only where the paper printed it."""
    anchor = w("11. Find the missing number: 15 + ", 0.096, 0.577, hand=False, width=0.30, h=0.012)
    printed = [
        w("15+", 0.324, 0.577, hand=False, width=0.03, h=0.012),
        w("30", 0.435, 0.577, hand=False, width=0.02, h=0.012),
    ]
    childs = w(
        "15", 0.371, 0.578, conf=97, width=0.02, h=0.014, line="11. Find the missing number: 15+ 15 = 30"
    )
    got = ocr.answers_for(
        page([childs] + printed, [anchor]), {"11": "Find the missing number: 15 + ___ = 30"}
    )
    assert (got["11"]["child_answer"], got["11"]["answer_state"]) == ("15", "written")


def test_a_doubtful_answer_is_looked_at_again_larger_and_only_then_stood_behind():
    """A 40x25-pixel answer on a 150-dpi page is at the limit of what the transcriber can resolve,
    and a third of everything that reaches a person sits at 50-69% because of it. The crop is a
    different image, so the floor applies to its confidence unchanged — it is not a second opinion
    on the same pixels, and nothing below the floor is ever stood behind."""
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    ask = []

    def reread(b):
        ask.append(b)
        return page([w("83", 0.5, 0.5, conf=96.0)], [])

    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=58.0, line=q["text"])], [q]),
        {"7": "7. 45 + 38 ="},
        reread=reread,
    )
    assert out["7"] == {
        "child_answer": "83",
        "answer_state": "written",
        "why": "",
        "guess": "",
        "confidence": 96.0,
        "working_shown": "none",
        "box": out["7"]["box"],
        "seen": [{"text": "83", "confidence": 58.0}],  # what the page read, before the second look
    }
    # the crop is the answer's own patch of the page, not the whole region a person is shown
    pad = ocr.DEFAULTS["reread_pad"]
    assert ask == [(0.42 - pad, 0.302 - pad, 0.42 + 0.04 + pad, 0.302 + 0.012 + pad)]


def test_a_second_look_that_is_still_doubtful_changes_nothing():
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=58.0, line=q["text"])], [q]),
        {"7": "7. 45 + 38 ="},
        reread=lambda b: page([w("83", 0.5, 0.5, conf=61.0)], []),
    )
    assert out["7"]["answer_state"] == "illegible"
    assert out["7"]["child_answer"] == ""


def test_a_crop_holding_two_numbers_is_refused_rather_than_chosen_between():
    """The neighbouring answer came with it and there is no telling which is which. The original
    reading was already below the floor, so a person was always going to see this one."""
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=58.0, line=q["text"])], [q]),
        {"7": "7. 45 + 38 ="},
        reread=lambda b: page([w("83", 0.3, 0.5, conf=99.0), w("12", 0.7, 0.5, conf=99.0)], []),
    )
    assert out["7"]["answer_state"] == "illegible"


def test_an_answer_already_over_the_floor_is_never_looked_at_again():
    """One extra call per DOUBTFUL answer is the whole cost case. A page the engine reads cleanly
    must cost nothing more than it did before."""
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    asked = []
    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=96.0, line=q["text"])], [q]),
        {"7": "7. 45 + 38 ="},
        reread=lambda b: asked.append(b),
    )
    assert out["7"]["child_answer"] == "83"
    assert asked == []


def test_the_second_look_is_off_when_its_row_says_zero():
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    asked = []
    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=58.0, line=q["text"])], [q]),
        {"7": "7. 45 + 38 ="},
        cfg={**ocr.DEFAULTS, "reread_dpi": 0},
        reread=lambda b: asked.append(b),
    )
    assert out["7"]["answer_state"] == "illegible"
    assert asked == []


def test_a_crop_that_sees_fewer_digits_than_the_page_is_the_answer_cut_in_half():
    """ "Answer=43" came back from its crop as "4" at 91.7% and would have entered a child's graph
    as 4. More pixels may add a digit the page missed; they cannot take one away."""
    q = w("1. 25 + 18 =", 0.1, 0.30, hand=False, width=0.3)
    out = ocr.answers_for(
        page([q, w("Answer=43", 0.42, 0.302, conf=65.4, line=q["text"])], [q]),
        {"1": "1. 25 + 18 ="},
        reread=lambda b: page([w("4", 0.5, 0.5, conf=91.7)], []),
    )
    assert out["1"]["answer_state"] == "illegible"
    assert out["1"]["child_answer"] == ""


def test_what_a_crop_resolves_a_mark_into_faces_the_echo_test_again():
    """The page read a fragment "3892" of the printed "38,924" beside it, which matched no echo and
    survived. The crop read the mark properly, at 99.3% — and it is the paper's own operand."""
    q = w("3. Achal added 45,678 + 38,924", 0.1, 0.30, hand=False, width=0.5)
    printed = w("38,924", 0.42, 0.302, hand=False, width=0.06, line=q["text"])
    out = ocr.answers_for(
        page([q, printed, w("3892", 0.42, 0.302, conf=51.7, width=0.041, line=q["text"])], [q]),
        {"3": "3. Achal added 45,678 + 38,924"},
        reread=lambda b: page([w("38,924", 0.5, 0.5, conf=99.3)], []),
    )
    assert out["3"]["answer_state"] == "illegible"
    assert out["3"]["child_answer"] == ""


def test_every_answer_that_reaches_a_person_says_why_it_did():
    """ "86 did not add up" was one bucket holding five different failures, and the only way to tell
    them apart was a SQL guess at the shape of the stored reading. The engine knows which branch it
    took, so it says so — and the teacher is told the reason beside the crop, not just that it is
    her problem now."""
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)

    # two numbers where one answer is asked for, in a region with two parts
    q2 = w("8. 12 + 9 =", 0.1, 0.40, hand=False, width=0.3)
    out = ocr.answers_for(
        page(
            [
                q,
                w("83", 0.42, 0.302, line=q["text"]),
                w("44", 0.55, 0.302, line=q["text"]),
                w("31", 0.60, 0.302, line=q["text"]),
                q2,
            ],
            [q, q2],
        ),
        {"7a": "7. 45 + 38 =", "7b": "7. 45 + 38 ="},
    )
    assert out["7a"]["why"] == "1 numbers in the region for 2 answers"

    # a question the page does not carry at all
    assert ocr.answers_for(page([], []), {"9": "9. 100 - 1 ="})["9"]["why"] == (
        "the printed question was not found on the page"
    )

    # an answer the engine stands behind gives no reason, because there is nothing to explain
    out = ocr.answers_for(page([q, w("83", 0.42, 0.302, line=q["text"])], [q]), {"7": "7. 45 + 38 ="})
    assert out["7"] == {**out["7"], "answer_state": "written", "why": ""}

    # a blank is a claim about the child, not a doubt about the reading, so it carries no reason
    blank = ocr.answers_for(page([q], [q]), {"7": "7. 45 + 38 ="})["7"]
    assert (blank["answer_state"], blank["why"]) == ("blank", "")


def test_a_box_claimed_by_its_label_is_never_offered_to_another_question():
    """The Cambridge grid "Complete each addition", row two, as one child's page produced it.

    2a and 2c were claimed by their printed labels; the frames round 2b and 2d did not close, so
    those two went to the region path — which still had 2c's emptied box and a sliver of 2b's own
    answer line on offer as fields. Positions decided: 2d, "29 + 4 =", came back as 64 at 99.8%,
    the child's answer to 58 + 6. She wrote 33, correctly, and was recorded as getting it wrong.
    """
    qs = {
        "2a": ("36 + 7 =", 0.125, 0.325),
        "2b": ("58 + 6 =", 0.330, 0.325),
        "2c": ("47 + 5 =", 0.530, 0.315),
        "2d": ("29 + 4 =", 0.730, 0.320),
    }
    printed = [w(t, x, y, hand=False, width=0.10, h=0.02, line=t, mixed=False) for t, x, y in qs.values()]
    hand = [
        w("42", 0.180, 0.400, width=0.04, h=0.02, line="Answer: 42"),
        w("52", 0.620, 0.315, width=0.035, h=0.02, line="47 + 5 =52"),
        w("64", 0.400, 0.393, width=0.035, h=0.016, line="Answer: 64"),
        w("33", 0.790, 0.390, width=0.04, h=0.02, line="Answer: 33"),
    ]
    boxes = [
        (0.1129, 0.3157, 0.3024, 0.4199, 0.1),  # 2a, closed, its label inside
        (0.5202, 0.3031, 0.7145, 0.4097, 0.1),  # 2c, closed, its label inside
        (0.3911, 0.3915, 0.4395, 0.4097, 0.3),  # a sliver of 2b's answer line
    ]
    out = ocr.answers_for(page(printed + hand, printed), {k: v[0] for k, v in qs.items()}, boxes=boxes)
    assert out["2a"]["child_answer"] == "42"
    assert out["2c"]["child_answer"] == "52"
    # the property that protects the child: 2d is never handed 2b's answer
    assert out["2d"]["child_answer"] != "64"
    assert (out["2b"]["child_answer"], out["2d"]["child_answer"]) in {("64", "33"), ("", "")}


def test_an_unsure_reading_keeps_its_guess_for_a_person_and_is_never_marked_from_it():
    """ "A 51" came back at 29%. The engine threw the 51 away and the teacher had to type it. Kept
    as a guess she confirms with one click — but a guess is never the child's answer: the reading
    still stands at "illegible", and marking sees nothing."""
    from engine import legacy

    q = w("4. 45 + 18 - 12 =", 0.1, 0.30, hand=False, width=0.3)
    out = ocr.answers_for(page([q, w("A51", 0.42, 0.302, conf=29.0, line=q["text"])], [q]), {"4": q["text"]})
    assert (out["4"]["answer_state"], out["4"]["child_answer"], out["4"]["guess"]) == ("illegible", "", "51")
    assert legacy.mark({"kind": "bare", "answer": 51}, {"answer": "51", "misconceptions": {}}, out["4"])[
        0
    ] == ("unreadable")
    # a reading the engine stands behind carries no guess: there is nothing to confirm
    sure = ocr.answers_for(page([q, w("51", 0.42, 0.302, conf=97.0, line=q["text"])], [q]), {"4": q["text"]})
    assert sure["4"]["guess"] == ""


def test_the_reader_records_what_it_saw_even_when_it_gives_up():
    """ADR 0032: a check on an answer the reader gave up on teaches nothing unless the reader wrote
    down what it saw. Every reading carries `seen` — each number in the region with its confidence —
    including the ones that go to a person."""
    q = w("7. 45 + 38 =", 0.1, 0.30, hand=False, width=0.3)
    # two numbers on two rows under the question, for three answers
    out = ocr.answers_for(
        page([q, w("83", 0.42, 0.33, conf=91.0), w("44", 0.42, 0.36, conf=62.5)], [q]),
        {"7a": "7. 45 + 38 =", "7b": "7. 45 + 38 =", "7c": "7. 45 + 38 ="},
    )
    assert out["7a"]["why"] == "2 numbers in the region for 3 answers"
    assert out["7a"]["seen"] == [{"text": "83", "confidence": 91.0}, {"text": "44", "confidence": 62.5}]
    clean = ocr.answers_for(
        page([q, w("83", 0.42, 0.302, conf=91.0, line=q["text"])], [q]), {"7": "7. 45 + 38 ="}
    )
    assert clean["7"]["child_answer"] == "83" and clean["7"]["seen"] == [{"text": "83", "confidence": 91.0}]
