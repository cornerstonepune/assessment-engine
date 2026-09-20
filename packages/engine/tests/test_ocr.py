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
    # And even without being told, a mark the child made ON the printed line is not nothing.
    assert ocr.answers_for(p, q)["13"]["answer_state"] == "illegible"


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
