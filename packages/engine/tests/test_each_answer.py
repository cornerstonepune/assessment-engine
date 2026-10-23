"""Each answer of a question with several answers, on its own (goals/md0a-every-answer-counts.yaml): marked against its
own key, read in its own boxes, and — a tick or a sentence — left to a person. Nothing here needs a database: the box
test prints a real paper and stands a shape-matcher in for the reader (`test_boxes`). The worksheet read end to end,
marked, signed off and counted is `test_every_answer.py`.
"""

import random
import uuid

import pytest

from engine.adapters import ocr
from engine.assess import diagnosis, equality, estimate, geometry
from engine.assess import learned_rules as L
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.w3_read import boxes, legacy, marking, profiles, reading, render_pdf, second_reader
from tests.test_boxes import StandIn, _scanned, _write


def _wrote(text):
    return {"child_answer": text, "answer_state": "written" if text else "blank", "working_shown": "none"}


# ---------------------------------------------------------------------------------------------- marking, one answer


def test_an_estimate_within_its_own_tolerance_is_right_and_one_outside_it_is_wrong():
    """An estimate's key carries how far a fair estimate may land from it (`Response.tolerance`). Nothing that marked a
    child's paper read it: 80 for an estimate keyed 70 within ten was marked wrong."""
    est = {"rid": "est", "kind": "digits", "answer": "70", "tolerance": 10, "misconceptions": {}}
    assert marking.mark({}, est, _wrote("70"))[0] == "correct"
    assert marking.mark({}, est, _wrote("80"))[0] == "correct"
    assert marking.mark({}, est, _wrote("85"))[0] == "wrong"
    exact = {"rid": "ans", "kind": "digits", "answer": "75", "misconceptions": {}}
    assert marking.mark({}, exact, _wrote("76"))[0] == "wrong", "an answer with no tolerance is exact"


def test_a_written_reason_is_judged_by_a_person_never_marked_unreadable():
    """A reason the child writes ("why") is a sentence. Its own kind says so; it was marked unreadable because only the
    question's kind was asked."""
    why = {"rid": "why", "kind": "text", "answer": None}
    assert marking.mark({}, why, _wrote("she forgot to carry the one"))[0] == "needs_teacher"
    assert marking.mark({}, why, _wrote(""))[0] == "blank"


def test_each_answer_is_marked_against_its_own_key():
    """A slot carries the answer it is for; the first answer of its question never stands in for it."""
    est = {"rid": "est", "kind": "digits", "answer": "70", "tolerance": 10, "misconceptions": {}}
    ans = {"rid": "ans", "kind": "digits", "answer": "68", "misconceptions": {"M_NOCARRY": "58"}}
    slot = {"spec": {}, "responses": [est, ans], "response": ans}
    assert marking.response_of(slot) is ans
    assert marking.response_of({"spec": {}, "responses": [est, ans]}) is est, (
        "a paper's own slot: its one answer"
    )
    assert marking.mark_read({}, marking.response_of(slot), _wrote("68"))[0] == "correct"
    assert marking.mark_read({}, marking.response_of(slot), _wrote("69"))[0] != "correct", (
        "69 is a fair estimate (70 within ten) and a wrong exact answer: marked against the estimate it would pass"
    )


def test_a_rule_about_working_a_sum_explains_only_the_sum_worked_exactly(monkeypatch):
    """A learned mistake, Jev's shortlist and rule discovery read how a child works `a op b` (`learned_rules`). Its
    estimate, a check of it, or a reason is not that sum: a wrong estimate named as a column mistake is a wrong name."""
    spec = {"a": 47, "b": 28, "op": "+"}
    assert L.works_the_sum(spec, {"rid": "ans", "answer": "75"})
    assert L.works_the_sum({"a": "62", "b": "18", "op": "-"}, {"rid": "a", "answer": 44}), (
        "an old paper's sum"
    )
    assert not L.works_the_sum(spec, {"rid": "est", "answer": "80", "tolerance": 10}), "an estimate"
    assert not L.works_the_sum(spec, {"rid": "est", "answer": "75", "tolerance": 10}), (
        "an estimate, even when exact"
    )
    assert not L.works_the_sum(spec, {"rid": "check", "answer": "47"}), "a check: the answer take away 28"
    assert not L.works_the_sum(spec, {"rid": "why", "answer": None}), "a reason"
    assert not L.works_the_sum({"a": 6, "b": 7, "op": "×"}, {"rid": "a", "answer": "42"}), (
        "no rule here for ×"
    )
    called = []
    monkeypatch.setattr(marking.learned_mistakes, "recognise", lambda *a: called.append(a) or ["M_LEARNED_X"])
    learned = [("M_LEARNED_X", {"op": "+"})]
    est = {"rid": "est", "kind": "digits", "answer": "80", "tolerance": 10, "misconceptions": {}}
    assert marking.mark(spec, est, _wrote("60"), learned=learned)[:2] == ("wrong", [])
    assert called == [], "a wrong estimate is never matched against rules for working the sum"
    ans = {"rid": "ans", "kind": "digits", "answer": "75", "misconceptions": {}}
    assert marking.mark(spec, ans, _wrote("65"), learned=learned)[1] == ["M_LEARNED_X"]


def test_a_tick_or_a_sentence_is_never_the_childs_handwriting_in_the_notebook():
    """The notebook shows the second reader a child's own handwriting and measures how often the reader gave up. A
    tick or a sentence was never handed to the reader: it is neither a sample of digits nor the reader giving up."""
    tick = {"fmt": "inverse_check", "capture_id": uuid.uuid4(), "page": 1, "box": [0.1, 0.1, 0.2, 0.2],
            "human_read": "right", "model_read": "", "why": boxes.FOR_A_PERSON, "guess": "", "answer_state": "for_a_person",
            "confidence": 0.0}  # fmt: skip
    digit = {
        **tick,
        "human_read": "47",
        "model_read": "47",
        "why": "",
        "answer_state": "written",
        "confidence": 99.0,
    }
    notes = profiles.build([tick, digit])
    assert [x["text"] for x in notes["samples"]] == ["47"], (
        "only what the child wrote as a number is a sample"
    )
    assert notes["gave_up"]["n"] == 0 and notes["checked"] == 1
    assert second_reader._groups({"1.right": tick}) == {}, "nothing the second reader is asked about"


def _page_of(monkeypatch, region):
    """`reading.read_pages` on one page, every outside service stood in: the boxes never line up, and `region` stands
    in for the reader by words."""
    monkeypatch.setattr(reading.ocr, "settings", lambda conn: {})
    monkeypatch.setattr(reading.ocr, "mask_red_pen", lambda jpeg, cfg: jpeg)
    monkeypatch.setattr(reading.digits, "settings", lambda conn: {"min_confidence": 90})
    monkeypatch.setattr(reading.render_pdf, "photo", lambda path, page: (None, None))
    monkeypatch.setattr(reading.crops, "keeper", lambda path, page: None)
    monkeypatch.setattr(reading.boxes, "read_page", lambda *a, **k: None)
    monkeypatch.setattr(reading.stencil, "read_page", region)
    monkeypatch.setattr(legacy, "second_look", lambda *a, **k: None)
    one = {
        "spec": {"page": 1, "question": "q"},
        "responses": [{"rid": "ans", "kind": "digits", "answer": "12"}],
    }
    est, ans = (
        {"rid": "est", "kind": "digits", "answer": "10"},
        {"rid": "ans", "kind": "digits", "answer": "12"},
    )
    two = {"spec": {"page": 1, "question": "q"}, "responses": [est, ans]}
    tick = {
        "spec": {"page": 1, "question": "q"},
        "responses": [{"rid": "right", "kind": "tick", "answer": "right"}],
    }
    by_key = {"1": one, "2": {**two, "response": est}, "2.ans": {**two, "response": ans}, "3": tick}
    by_key = {k: {**it, "item_key": k.split(".")[0]} for k, it in by_key.items()}

    def read(paper):
        scan = {"path": "x.pdf", "paper": paper, "paper_code": "P", "by_key": by_key, "page_numbers": [1],
                "images": [b""]}  # fmt: skip
        return reading.read_pages(None, scan, None, None, notes={}, second=False)[0]

    return read


def test_a_printed_page_that_did_not_line_up_goes_whole_to_a_person(monkeypatch):
    """R2 (Nimish, 2026-10-22): a page of the school's own paper whose boxes cannot be found goes whole to a person. It
    was read by the words printed above each answer instead, and on a page of pictures, where several questions' words
    are not found, one field went to all of them: on 22 Oct, one box to Q1, Q7 and Q8 of a Grade 1 copy."""
    asked = []
    read = _page_of(
        monkeypatch,
        lambda jpeg, questions, *a, **k: asked.append(questions) or {q: _wrote("12") for q in questions},
    )
    page = read({"fields": "cells", "geometry": [1], "printed": "x.pdf"})
    assert asked == [], "a printed page is never read by its words"
    got = page["readings"]
    assert set(got) == {"1", "2", "2.ans", "3"}, "every answer on the page is there, for a person"
    assert all(r["child_answer"] == "" and r["guess"] == "" for r in got.values()), (
        "nothing read, nothing guessed"
    )
    assert {k for k, r in got.items() if r["answer_state"] == "not_found"} == {"1", "2", "2.ans"}
    assert all(got[k]["why"] == boxes.UNALIGNED for k in ("1", "2", "2.ans")), "the reader's failure, said so"
    assert got["3"]["answer_state"] == "for_a_person" and profiles.never_read(got["3"]["why"]), (
        "a tick is a person's to read, lined up or not"
    )
    assert "did not line up" in page["note"] and "4 for a person" in page["note"]


def test_a_paper_entered_by_hand_is_still_read_by_its_words(monkeypatch):
    """A paper entered by hand records no boxes: its every question is read by the words above it, as before R2."""
    asked = {}

    def region(jpeg, questions, *a, **k):
        asked.update(questions)
        return {q: _wrote("12") for q in questions}

    read = _page_of(monkeypatch, region)
    got = read({"fields": "boxes"})["readings"]
    assert set(asked) == {"1", "2", "2.ans", "3"}, (
        "every question is given, so each one's region ends at the next"
    )
    assert all(r["child_answer"] == "12" for r in got.values())


# ---------------------------------------------------------------------------------------------- reading, every box


@pytest.fixture(scope="module")
def two_answer_paper(tmp_path_factory):
    """Two estimate-then-work-it-out questions, a check with a tick and a corrected answer with a reason, printed."""
    rng = random.Random(11)

    def drawn(
        make,
    ):  # a generator refuses numbers that do not make its question: draw again, as the bank does
        for _ in range(50):
            try:
                return make()
            except RuntimeError:
                continue
        raise RuntimeError("no numbers in fifty draws")

    qs = [
        drawn(lambda: estimate.estimate_then_calc(rng, "R5", "Procedural", "+", 2, 2, [0, 1]))
        for _ in range(2)
    ]
    qs.append(drawn(lambda: equality.inverse_check(rng, "R16", "Conceptual", "+", digits=2)))
    qs.append(drawn(lambda: diagnosis.find_mistake(rng, "X2", "Stretch", "+", digits=2)))
    out = tmp_path_factory.mktemp("two")
    key = render_sheet(
        Sheet("CS00C0D2", "G2", "Focus", 1, "W1", qs, title="Practice"), out, week_label="Practice"
    )
    return out / "CS00C0D2.pdf", key, qs


def test_every_answer_of_a_question_is_read_in_its_own_boxes(two_answer_paper, tmp_path, monkeypatch):
    """Each number a question asks for is read where it was written; a tick or a sentence is not a number, so the
    digit reader is never handed it — a person reads it, shown the place it was written."""
    reader = StandIn()
    monkeypatch.setattr(boxes.digits, "read", reader.read)
    pdf, key, qs = two_answer_paper
    runs, _ = geometry.cells_of(key["geometry"], 1)
    by_id = {it["item_id"]: q for it, q in zip(key["items"], qs, strict=True)}
    written = {}
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    for (item, rid), run in runs.items():
        response = next(r for r in by_id[item].responses if r.rid == rid)
        if response.kind != "digits":
            continue
        text = str(int(response.answer) + (1 if rid == "ans" else 0))[-len(run) :]  # the exact answer one out
        written[(item, rid)] = text
        for cell, ch in zip(run, text.rjust(len(run)), strict=True):
            if ch.strip():
                _write(img, cell, ch, boxes.PPM)
    scan = _scanned(img, tmp_path / "scan.pdf")
    answers = {(g["item"], g["resp"]) for g in key["geometry"] if g["page"] == 1 and g.get("kind") != "work"}
    wanted = {f"{n}.{rid}": (item, rid) for n, (item, rid) in enumerate(sorted(answers))}
    people = {
        s for s, (item, rid) in wanted.items()
        if next(r for r in by_id[item].responses if r.rid == rid).kind != "digits"
    }  # fmt: skip
    assert people, "the paper prints a tick and a sentence"
    photo, frame = render_pdf.photo(scan, 1)
    got = boxes.read_page(
        photo, 1, pdf, key["geometry"], wanted, ocr.settings(), frame=frame, for_a_person=people
    )
    assert set(got) == set(wanted), "every answer the paper asks for comes back"
    for slot, (item, rid) in wanted.items():
        if slot in people:
            assert got[slot]["answer_state"] == "for_a_person" and "a person" in got[slot]["why"]
            assert got[slot]["child_answer"] == "" and len(got[slot]["box"]) == 4
        else:
            assert got[slot]["child_answer"] == written[(item, rid)], slot
