"""The parent report (goals/w4c-parent-report.yaml, `w4_close/parent_report.py`). One Grade 2 child, Ria, whose
answers give each part something true to say: 2-digit − 2-digit on a paper, the smaller digit taken from the larger
four times (once with working); 2-digit + 1-digit nine of nine; 2-digit + 2-digit three wrong one day, all right the
next. The model is stood in for; the database is the local copy, rolled back."""

import copy
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from engine.core import db
from engine.w4_close import parent_report as P

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
NAME = "Riaparentreport"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    t = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    kid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'PR-TEST', 'G2') returning id",
        (t,),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s, %s, %s)", (t, kid, NAME)
    )
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, child_id, week) values (%s, 'G2', %s, 'PR-TEST') returning id",
        (t, kid),
    ).fetchone()["id"]
    inst = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s, %s, %s, %s, 'returned') returning id",
        (t, f"PR-{str(kid)[:8]}", tpl, kid),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s, 'pr', 1, %s, 'processed')"
        " returning id",
        (t, inst),
    ).fetchone()["id"]
    day1 = datetime.now(timezone.utc) - timedelta(days=3)
    day2 = datetime.now(timezone.utc)
    paper = [(False, "45", ["M_SMALL_FROM_LARGE"], "none")] * 3 + [
        (False, "45", ["M_SMALL_FROM_LARGE"], "partial")
    ]
    for n, (right, wrote, codes, working) in enumerate(paper + [(True, "35", [], "none")] * 2):
        item = conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses)"
            " values (%s, %s, 'pr', 'R24', '{NUM.OPS.02}', 'Procedural', 'column', %s, %s) returning id",
            (
                t,
                f"pr/{kid}/{n}",
                json.dumps({"op": "-", "a": 62, "b": 27}),
                json.dumps([{"rid": "a", "answer": 35}]),
            ),
        ).fetchone()["id"]
        res = conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, misconception_codes,"
            " working_shown, state) values (%s, %s, %s, 'a', %s, %s, %s, %s, 'confirmed') returning id",
            (
                t,
                cap,
                item,
                json.dumps({"child_answer": wrote}),
                "correct" if right else "wrong",
                codes,
                working,
            ),
        ).fetchone()["id"]
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, item_result_id, observed_at, confirmed_by) values (%s,%s,'NUM.OPS.02','R24',%s,%s,'item',%s,%s,'t')",
            (t, kid, right, codes, res, day2),
        )
    direct = (
        [("R21", True, day1)] * 9
        + [("R22", False, day1)] * 3
        + [("R22", True, day1)]
        + [("R22", True, day2)] * 4
    )
    for rung, right, when in direct:
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,'NUM.OPS.01',%s,%s,'{}','item',%s,'t')",
            (t, kid, rung, right, when),
        )
    conn.execute("select rebuild_child_skill_state(%s::uuid)", (kid,))
    return kid


def _good(f):
    """A draft that says only what the facts say, as the model is asked to."""
    return {
        "summary": "[child] is building steady habits in maths, and the educator sees careful work on the page.",
        "can_do": [
            {"id": x["id"], "sentence": f"[child] got {x.get('right', x.get('recent'))} right."}
            for k in ("can_do", "nearly", "improving")
            for x in f[k]
        ],  # fmt: skip
        "working_on": [
            {
                "id": w["id"],
                "explanation": f"In {w['example']['question']} [child] wrote {w['example']['wrote']}; the answer is {w['example']['right']}."
                if w["example"]
                else "[child] sometimes takes the smaller digit from the larger, and the educator shows the exchange.",
            }
            for w in f["working_on"]
        ],
        "at_home": ["Take two handfuls of spoons and find how many more are in one than the other."],
        "next_at_school": "The educator works on exchanging a ten when the top digit is smaller.",
    }


def test_the_facts_are_the_childs_signed_off_answers_and_never_their_name(conn, child):
    f = P.facts(conn, child)
    assert NAME not in json.dumps(f), "rule 6: nothing a model is given names the child"
    assert f["grade"] == "Grade 2" and f["answers"] == 23
    add = next(x for x in f["can_do"] if x["id"] == "ADD.2D1D")
    assert (add["right"], add["answered"]) == (9, 9) and add["can"]
    better = next(x for x in f["improving"] if x["id"] == "ADD.2D2D")
    assert (better["earlier"], better["recent"]) == ("1 of 4 right", "4 of 4 right"), (
        "the earlier half, then the recent"
    )
    slip = f["working_on"][0]
    assert slip["id"] == "M_SMALL_FROM_LARGE" and slip["times"] == 4
    assert slip["example"] == {"question": "62 − 27 = ?", "wrote": "45", "right": 35}
    hint = conn.execute(
        "select repair_hint from misconception where code = 'M_SMALL_FROM_LARGE' and op = '-'"
    ).fetchone()["repair_hint"]
    assert slip["what_we_do"] == hint and slip["what_happens"] and "written as" not in slip["what_happens"]
    assert f["on_the_papers"] == {
        "wrong_answers": 7,
        "wrong_answers_with_working_shown": 1,
        "questions_the_child_left_blank": 0,
    }
    assert f["days"] == 4, "the answers span four days, and the facts say so"


def test_words_that_say_what_the_facts_do_not_are_caught(conn, child):
    """Nimish, 2026-09-28: "a proper understanding and explanation of where the child is" — written by a model, but
    never a number, a name or a word the facts and the school do not hold."""
    f = P.facts(conn, child)
    assert P.check(f, _good(f)) == []
    for spoil, expect in [
        (lambda d: d.update(summary=d["summary"] + " [child] got 97 of them."), "the number 97"),
        (lambda d: d.update(summary=d["summary"] + " The teacher is pleased."), "'teacher'"),
        (lambda d: d.update(summary=d["summary"] + " We think Aarav is ready."), "'Aarav'"),
        (lambda d: d.update(summary=d["summary"].replace("[child]", "Your child")), "never says [child]"),
        (lambda d: d["can_do"].pop(), "can_do must have exactly one entry"),
        (lambda d: d.update(at_home=["Practise 2-digit sums: aim for full marks!"]), "exclamation"),
        (lambda d: d.update(next_at_school="We work on M_SMALL_FROM_LARGE next week."), "a code"),
        (
            lambda d: d.update(next_at_school="[child] is right half the time, about 50 percent."),
            "percentage",
        ),
    ]:
        d = copy.deepcopy(_good(f))
        spoil(d)
        assert any(expect in p for p in P.check(f, d)), expect


def test_a_draft_that_breaks_its_facts_is_sent_back_once_and_never_kept_if_it_breaks_them_again(conn, child):
    asked = []

    def ask(conn, purpose, variables, meta=None, version=None):
        asked.append(variables)
        d = _good(variables["facts"])
        if len(asked) == 1:
            d["summary"] += " The teacher says so."
        return d

    got = P.draft(conn, child, ask=ask)
    assert got["attempts"] == 2 and got["problems"] == []
    assert "'teacher'" in asked[1]["fix"], "the second ask names what the first broke"
    assert NAME not in json.dumps(asked, default=str)

    def stubborn(conn, purpose, variables, meta=None, version=None):
        return {**_good(variables["facts"]), "next_at_school": "The teacher decides."}

    bad = P.draft(conn, child, ask=stubborn)
    assert bad["problems"]
    with pytest.raises(ValueError, match="never kept"):
        P.keep(conn, child, bad)


def test_a_kept_report_waits_for_an_educator_says_when_it_is_out_of_date_and_is_approved_once(conn, child):
    ask = lambda conn, purpose, variables, meta=None, version=None: _good(variables["facts"])  # noqa: E731
    P.keep(conn, child, P.draft(conn, child, ask=ask))
    note = P.latest(conn, child)
    assert (
        note["approved_by"] is None
        and note["stale"] is False
        and note["draft"]["summary"].startswith("[child]")
    )
    with pytest.raises(ValueError, match="names the educator"):
        P.approve(conn, child, note["id"], "")
    P.approve(conn, child, note["id"], "neha")
    assert P.latest(conn, child)["approved_by"] == "neha"
    with pytest.raises(LookupError):
        P.approve(conn, child, note["id"], "someone else")
    t = conn.execute("select tenant_id from child where id = %s", (child,)).fetchone()["tenant_id"]
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,"
        " observed_at, confirmed_by) values (%s,%s,'NUM.OPS.01','R21',true,'{}','item',now(),'t')",
        (t, child),
    )
    assert P.latest(conn, child)["stale"] is True, (
        "an answer signed off since: the report says it is out of date"
    )


def test_the_eval_counts_every_child_and_the_bar_is_all_of_them(conn, child):
    ask = lambda conn, purpose, variables, meta=None, version=None: _good(variables["facts"])  # noqa: E731
    got = P.evaluate(conn, None, ask=ask)
    assert got["n"] >= 1 and got["passed"] + len(got["failures"]) == got["n"] and got["sample"]
    assert all(set(f) == {"child", "problems"} and len(f["child"]) == 8 for f in got["failures"]), (
        "no name, ever"
    )


def test_the_report_over_http_is_written_kept_and_approved(conn, child, monkeypatch):
    from fastapi.testclient import TestClient

    from engine.api import deps
    from engine.api.app import app

    monkeypatch.setattr(
        P.llm, "generate", lambda conn, purpose, variables, meta=None, version=None: _good(variables["facts"])
    )
    monkeypatch.setenv("ENGINE_KEY", "k")
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    try:
        with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
            assert client.get(f"/child/{child}/parent-report").json()["note"] is None
            r = client.post(f"/child/{child}/parent-report", json={"by": "neha"})
            assert r.status_code == 201, r.text
            note = r.json()["note"]
            assert note["approved_by"] is None
            r = client.post(f"/child/{child}/parent-report/{note['id']}/approve", json={"by": "neha"})
            assert r.status_code == 200 and r.json()["note"]["approved_by"] == "neha"
            assert (
                client.post(
                    f"/child/{child}/parent-report/{note['id']}/approve", json={"by": "x"}
                ).status_code
                == 409
            )
            assert client.get("/child/00000000-0000-0000-0000-000000000000/parent-report").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_a_draft_over_its_schema_is_sent_back_and_one_childs_failure_never_ends_the_eval(conn, child):
    """2026-09-28, the first eval on live: one draft longer than its schema allows raised, and the eval of every other
    child ended with it."""
    asked = []

    def long_once(conn, purpose, variables, meta=None, version=None):
        asked.append(1)
        if len(asked) == 1:
            raise P.llm.LLMError("parent_report output failed its schema: '...' is too long")
        return _good(variables["facts"])

    got = P.draft(conn, child, ask=long_once)
    assert got["attempts"] == 2 and got["problems"] == []
    assert "failed its schema" in P.draft(conn, child, ask=lambda *a, **k: (_ for _ in ()).throw(
        P.llm.LLMError("parent_report output failed its schema: too long")))["problems"][0]  # fmt: skip

    def down(conn, purpose, variables, meta=None, version=None):
        raise P.llm.LLMError("all models unavailable")

    with pytest.raises(P.llm.LLMError):
        P.draft(
            conn, child, ask=down
        )  # not a draft's fault: said, not counted as a draft that broke its facts
    ev = P.evaluate(conn, None, ask=down)
    assert ev["n"] >= 1 and ev["passed"] == 0 and len(ev["failures"]) == ev["n"]


def test_what_the_first_eval_on_live_found_is_caught_or_let_through_as_it_should_be(conn, child):
    """2026-09-28, `parent_report` v2 on live, 3 of 9: each cause pinned here."""
    f = P.facts(conn, child)
    ids = [x["id"] for k in ("can_do", "nearly", "improving") for x in f[k]]
    assert len(ids) == len(set(ids)), "a skill set is said once, however many of its rung's skills are strong"

    def said(**parts):
        return P.check(f, {**_good(f), **parts})

    # a sentence's first word after a closing quote is not a name
    assert said(at_home=["Tell the story: 'Some birds flew away.' Use buttons to act it out."]) == []
    assert any("'Aarav'" in p for p in said(at_home=["Tell the story to Aarav and act it out."]))
    # the school's own skill name is not the banned word; every other form of it is
    assert said(next_at_school="The educator works on word problems with [child].") == []
    assert any(
        "'problems'" in p for p in said(next_at_school="The educator sees problems in [child]'s work.")
    )
    assert any("'struggles'" in p for p in said(next_at_school="[child] struggles with the exchange."))
    # a practice sum the model made up is a number the facts do not hold
    assert any(
        "the number 25" in p for p in said(at_home=["Start with 25 take away 3, which needs no exchange."])
    )


def test_what_the_v3_eval_on_live_found_the_facts_now_say_and_the_check_catches(conn, child, monkeypatch):
    """2026-09-28, v3 on live, 10 of 10 held to their facts, and a person reading them found: "can do X" and "will
    practise X next" to the same parent; "over this week" for answers over more days; "leave four questions blank"."""
    real = P.report.build

    def secure_next(conn, child_id, since=None):
        rep = real(conn, child_id, since)
        return {
            **rep,
            "next": {"skill_set": "ADD.2D1D", "level": "Hard", "mistake": None, "state": "stretch_ready"},
        }

    monkeypatch.setattr(P.report, "build", secure_next)
    f = P.facts(conn, child)
    assert f["next"]["why"].startswith("secure already") and f["next"]["level"] == "Hard"
    assert "questions_the_child_left_blank" in f["on_the_papers"]
    for said in ("Over this week, [child] answered them.", "[child] did well today.", "Practise it weekly."):
        assert any("a time the facts do not give" in p for p in P.check(f, {**_good(f), "summary": said}))


def test_numbers_are_read_however_they_are_written():
    assert P.numbers_in("9,000 take away 3,456") == ({9000, 3456}, set())
    assert P.numbers_in("leaving sixty-one, then forty three got on") == (set(), {61, 43})
    assert P.numbers_in("nine thousand four hundred and fifty-six seats")[1] == {9456}
    assert P.numbers_in("count in tens on a hundred-square, in hundreds") == (set(), set()), (
        "a place value's name"
    )


def test_what_the_v4_eval_on_live_found_is_caught(conn, child):
    """2026-09-28, v4 on live, 9 of 10, and reading all nine: a child's steps retold in number words, a sum in
    grouped digits, and a quoted sentence's first word taken for a name."""
    f = P.facts(conn, child)

    def said(**parts):
        return P.check(f, {**_good(f), **parts})

    assert any("the number 61" in p for p in said(next_at_school="[child] wrote sixty-one and stopped."))
    assert any("the number 9000" in p for p in said(at_home=["Try 9,000 take away 3,456 together."]))
    assert (
        said(
            at_home=["Tell a story like 'First you had some apples. Then you picked more.' Ask what happens."]
        )
        == []
    )
    assert said(at_home=["Count in tens up to a hundred together, with spoons."]) == []


def test_what_the_v5_eval_on_live_found_is_read_right_and_next_is_never_the_models(conn, child):
    """2026-09-28, v5 on live, 8 of 10: "ten, twenty, thirty" read as 60 and "one ten, two tens" as 13 (the check was
    wrong, not the words); "[child become" let through; and "secure already" written up as "still practising"."""
    assert P.numbers_in("count to ten, twenty, thirty and beyond")[1] == {10, 20, 30}
    assert P.numbers_in("'one ten, two tens, three tens'")[1] == {1, 10, 2, 3}
    assert P.numbers_in("twenty-three, then four hundred and fifty-six")[1] == {23, 456}
    f = P.facts(conn, child)
    assert any(
        "a bracket" in p for p in P.check(f, {**_good(f), "summary": "[child become sure of it, [child]."})
    )

    seen = []

    def ask(conn, purpose, variables, meta=None, version=None):
        seen.append(variables["facts"])
        return _good(variables["facts"])

    P.draft(conn, child, ask=ask)
    assert "next" not in seen[0], "what comes next is said by code on the page, never by the model"


def test_what_the_v6_eval_on_live_refused_that_it_should_not_have(conn, child):
    """2026-09-28, v6 on live, 8 of 10 — both refusals the check's: a "story problem" is a kind of question, not the
    child's; "ten, twenty, thirty" is counting aloud, not a count. What the rules are for still holds."""
    f = P.facts(conn, child)

    def said(**parts):
        return P.check(f, {**_good(f), **parts})

    assert said(at_home=["Make up a short story problem together about pocket money."]) == []
    assert said(at_home=["Count in tens aloud together — ten, twenty, thirty — with spoons."]) == []
    assert any("'problem'" in p for p in said(next_at_school="[child] has a problem with exchanging."))
    assert any("the number 61" in p for p in said(next_at_school="[child] wrote sixty-one."))
