"""The geometry that turns OCR words into a child's answers. No network: the cases here are the
ones a real page produced, written down as boxes.

Measured on that page after these rules: 14 of 14 ordinary answer boxes read exactly right, against
9 of 14 for the vision model it replaced.
"""

from engine.adapters import ocr


def w(text, x, y, hand=True, conf=99.0, h=0.012, width=0.04):
    return {"text": text, "x": x, "y": y, "w": width, "h": h, "hand": hand, "confidence": conf}


def page(words, lines):
    return {"words": words, "lines": lines}


def test_a_printed_number_is_never_the_childs_answer():
    """Q5 prints "452 = 400 + [ ] + 12". The 452 and the 12 are the paper's; only the 0 is the
    child's. Before Textract's handwriting flag was used, the printed 452 was returned as the
    answer."""
    anchor = w("452 = 400 +", 0.13, 0.72, hand=False, width=0.30)  # an inline line is wide
    p = page([w("452", 0.14, 0.75, hand=False), w("0", 0.26, 0.75)], [anchor])
    assert [c["text"] for c in ocr._handwriting_near(p, anchor)] == ["0"]


def test_the_neighbouring_boxs_answer_is_not_a_candidate():
    """Four boxes across a page sit about 0.19 apart. At a 0.13 column tolerance question 1a's
    answer was a candidate for 1b and won on a rounding tie, which is how 245 became 155."""
    anchor = w("236 + 9 =", 0.313, 0.239, hand=False)
    p = page([w("155", 0.186, 0.313), w("245", 0.378, 0.310)], [anchor])
    assert [c["text"] for c in ocr._handwriting_near(p, anchor)] == ["245"]


def test_the_labelled_answer_box_beats_a_number_left_in_the_working():
    """On 4c the working shows 284 and the answer line 384. The paper's own "Answer:" label says
    which one the child is standing behind."""
    anchor = w("342 - 58 =", 0.51, 0.62, hand=False)
    label = w("Answer: 384", 0.51, 0.70, hand=False)
    p = page([w("284", 0.52, 0.66), w("384", 0.56, 0.70)], [anchor, label])
    assert [c["text"] for c in ocr._handwriting_near(p, anchor)] == ["384"]


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
