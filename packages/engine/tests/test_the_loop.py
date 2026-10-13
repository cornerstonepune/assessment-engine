"""M5a: every new skill through the whole loop (goals/md5a-the-loop.yaml).

For each multiplication and division skill set at each level: its topic switched on, as an educator does on the site; a
library worksheet of it printed for a child; its boxes filled with known answers, one named mistake planted wherever its
questions can show it and the key everywhere else; the copy read and marked; what the reader held, confirmed by a person
as the child wrote it; the paper signed off. Then, stage by stage, the planted mistake must come back: named on every
answer it was planted on, counted as evidence on the skill set's rung, repeating in the child's graph, the subject of the
child's next paper, and said by its own name on the class card and in the parent report's facts. Then round again
(M5b): that next paper printed for the child, the mistake made on it again, read back by its code, named and counted.

The handwriting reader is stood in (as `test_every_answer.py` does): what it reads is the answer written. Reading
handwriting is scored on its own (`engine eval`); this is about everything after it. The planted answers are each
question's own stored wrong answer for the mistake (`responses[].misconceptions`), so a stage that loses or renames the
mistake fails here, whatever made it.
"""

import json
import uuid
from collections import Counter

import pytest

from engine.adapters import ocr
from engine.assess import graph
from engine.core import db, mistake_names
from engine.w2_print import focus_paper, handout
from engine.w3_read import boxes, copies, marking, second_reader
from engine.w4_close import card, parent_facts
from tests.test_each_answer import _wrote
from tests.test_sorting import _scanned as _scanned_file

SEED = db.REPO_ROOT / "supabase" / "seed"
LEVELS = ("Easy", "Medium", "Hard", "Advance")
NEW = sorted(
    s["code"]
    for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
    if s["code"].split(".")[0] in ("MUL", "DIV", "MD")
)
PERSON = "End-to-end loop"
WEEK = "2026-W42"


@pytest.fixture
def conn():
    import os

    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def _sheet(conn, code, level):
    return conn.execute(
        "select t.code, t.band, t.item_ids, s.rung_code, s.topic_code, s.level_band ->> t.difficulty as grade"
        " from sheet_template t join skill_set s"
        " on s.code = t.skill_set_code where t.source = 'library' and t.retired_at is null"
        " and t.skill_set_code = %s and t.difficulty = %s"
        " order by t.code limit 1",
        (code, level),
    ).fetchone()


def _slots(conn, ids):
    """[(item_id, rid, key, {mistake: its wrong answer})] of every answer box on the sheet, in the order printed."""
    rows = {r["id"]: r for r in conn.execute("select id, responses from item where id = any(%s)", (ids,))}
    return [
        (i, x["rid"], str(x["answer"]), {m: str(v) for m, v in (x.get("misconceptions") or {}).items()})
        for i in ids
        for x in rows[i]["responses"]
    ]


def _planted(slots):
    """The mistake the sheet can show on the most answers — a number, or a tick, the key is not — and the slots it
    goes on. Every mistake that ties for most is a fair choice; the first by name is taken, so a run is repeatable."""
    can = Counter(m for _, _, key, wrong in slots for m, v in wrong.items() if v and v != key)
    if not can:
        return None, []
    most = max(can.values())
    m = min(c for c, n in can.items() if n == most)
    return m, [(i, rid) for i, rid, key, wrong in slots if wrong.get(m, key) != key]


def _a_child(conn, section, band):
    """A child of the grade the level is for: a child's next paper is drawn from the levels of their own grade."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '7', %s, %s) returning id",
        (tenant, band, section),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Mira')", (tenant, child)
    )
    return child


def _read(conn, pdf, ids, wrote, scan_at, monkeypatch):
    """A copy printed for its child (`pdf`, the child's own code on it), scanned and read by that code; the reader
    stood in to read what `wrote` says each box holds. A tick or a reason comes back for a person, as the box reader
    returns them. → what the reading says of the copy."""
    monkeypatch.setattr(copies, "CUT", scan_at.parent / "scans")
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(second_reader, "propose", lambda conn, r, *a, **k: (r, ""))
    by_key = {
        r["item_key"]: r["id"]
        for r in conn.execute("select id, item_key from item where id = any(%s)", (ids,))
    }

    def read_page(img, page_no, pdf, geometry, wanted, cfg, frame=None, keep=None, for_a_person=()):
        out = {}
        for slot, (item_key, rid) in wanted.items():
            if slot in for_a_person:
                out[slot] = {"child_answer": "", "answer_state": "for_a_person", "why": boxes.FOR_A_PERSON,
                             "box": [0.1, 0.1, 0.2, 0.1], "confidence": 0.0, "working_shown": "none"}  # fmt: skip
            else:
                out[slot] = {**_wrote(wrote[(by_key[item_key], rid)]), "confidence": 99.0}
        return out

    monkeypatch.setattr(boxes, "read_page", read_page)
    (got,) = copies.read(conn, _scanned_file([pdf], scan_at), "", [], PERSON)
    return got


def _results(conn, child, qr):
    return conn.execute(
        "select r.id, r.item_id, r.rid, r.status, r.misconception_codes from item_result r"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.qr_code = %s and si.child_id = %s and c.superseded_by is null",
        (qr, child),
    ).fetchall()


def _round(conn, child, qr, pdf, ids, mistake, scan_at, monkeypatch, what):
    """One turn of the loop on one printed copy: `mistake` planted wherever its questions can show it, the key
    everywhere else; read by its code onto that copy; each held answer confirmed by a person as the child wrote it;
    each planted answer named, and the key marked right; then signed off. → how many answers were planted."""
    slots = _slots(conn, ids)
    on = [(i, rid) for i, rid, key, wrong in slots if wrong.get(mistake, key) != key]
    wrote = {(i, rid): (wrong[mistake] if (i, rid) in on else key) for i, rid, key, wrong in slots}
    got = _read(conn, pdf, ids, wrote, scan_at, monkeypatch)
    assert got["child_id"] == child and got["by_code"] and not got.get("skipped"), f"{what}: read as {got}"
    for r in _results(conn, child, qr):  # a person confirms each held answer as the child wrote it
        if r["status"] != "needs_teacher":
            continue
        if (
            wrote[(r["item_id"], r["rid"])] == "None"
        ):  # a reason, which only a person marks: Right, on the site
            conn.execute("select resolve_result(%s, 'correct', '{}'::text[], %s)", (r["id"], PERSON))
        else:
            marking.correct(conn, r["id"], wrote[(r["item_id"], r["rid"])], PERSON)
    marked = {(r["item_id"], r["rid"]): r for r in _results(conn, child, qr)}
    assert set(marked) == set(wrote), f"{what}: every answer box is read once"
    missed = [k for k in on if mistake not in (marked[k]["misconception_codes"] or [])]
    assert not missed, f"{what}: {len(missed)} of {len(on)} planted answers not named {mistake}"
    wrong_key = [
        (k, wrote[k], marked[k]["status"]) for k in set(wrote) - set(on) if marked[k]["status"] != "correct"
    ]
    assert not wrong_key, f"{what}: the key marked wrong {wrong_key}"
    marking.confirm(conn, child, PERSON)
    return len(on)


def _counted(conn, child, mistake, rung=None):
    return conn.execute(
        "select count(*) as n from evidence_event where child_id = %s and %s = any(misconception_codes)"
        " and (%s::text is null or rung_code = %s)",
        (child, mistake, rung, rung),
    ).fetchone()["n"]


@pytest.mark.parametrize("code,level", [(c, lv) for c in NEW for lv in LEVELS])
def test_a_mistake_planted_on_a_new_skills_paper_comes_back_through_every_stage(
    conn, tmp_path, monkeypatch, every_kind_trusted, code, level
):
    sheet = _sheet(conn, code, level)
    if sheet is None and level not in [
        lv
        for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
        if s["code"] == code
        for lv in s["difficulty"]
    ]:
        pytest.skip(f"{code} has no {level} level")
    assert sheet, f"{code} {level}: no library worksheet to print"
    conn.execute(
        "update topic set taught = true, taught_by = %s, taught_at = now() where code = %s",
        (PERSON, sheet["topic_code"]),
    )
    mistake, on = _planted(_slots(conn, sheet["item_ids"]))
    assert mistake and len(on) >= 2, (
        f"{code} {level}: no mistake its questions can show twice — {len(on)} places"
    )

    # the first turn: the worksheet, printed for the child as an educator does on the site (Make papers, `handout`)
    section = f"L{uuid.uuid4().hex[:5]}"
    child = _a_child(conn, section, sheet["grade"] or sheet["band"])
    pdf = handout.for_children(conn, sheet["code"], [child], WEEK, PERSON, tmp_path / "print")
    qr = conn.execute("select qr_code from sheet_instance where child_id = %s", (child,)).fetchone()[
        "qr_code"
    ]
    planted = _round(
        conn,
        child,
        qr,
        pdf,
        sheet["item_ids"],
        mistake,
        tmp_path / "first.pdf",
        monkeypatch,
        f"{code} {level}",
    )
    seen = _counted(conn, child, mistake, sheet["rung_code"])
    assert seen == planted, (
        f"{code} {level}: {seen} of {planted} planted answers counted on {sheet['rung_code']}"
    )

    graph.rebuild(conn, child)
    state = conn.execute(
        "select state, repeating_misconception from child_skill_state where child_id = %s and rung_code = %s"
        " and repeating_misconception is not null",
        (child, sheet["rung_code"]),
    ).fetchall()
    assert any(s["repeating_misconception"] == mistake for s in state), f"{code} {level}: graph {state}"

    nxt = focus_paper.plan(conn, child, WEEK)["areas"]
    assert nxt and nxt[0]["skill_set"] == code and nxt[0]["mistake"] == mistake, (
        f"{code} {level}: next {nxt[:1]}"
    )
    assert any(q["shows_mistake"] for q in nxt[0]["questions"]), (
        f"{code} {level}: no next question can show {mistake} — {nxt[0]['level']}, skill {nxt[0]['skill']},"
        f" {[(q['fmt'], q['text'][:40]) for q in nxt[0]['questions']]}"
    )

    name = mistake_names.names(conn)(mistake)
    line = next(k for k in card.build(conn, section)["children"] if k["child_id"] == str(child))
    assert line["home"] and line["home"]["mistake"] == mistake and line["home"]["mistake_name"], line
    facts = parent_facts.facts(conn, child)
    said = [w for w in facts["working_on"] if w["id"] == mistake]
    assert said and said[0]["mistake"] and said[0]["what_we_do"], (
        f"{code} {level}: parent facts {facts['working_on']}"
    )
    assert "borrow" not in (name + line["home"]["mistake_name"] + said[0]["mistake"]).lower(), (
        "the school's words"
    )

    # the second turn (M5b): that next paper, approved and printed for the child, comes back from its scan by its code,
    # the mistake made again named on it, and counted once signed off
    made = focus_paper.make(conn, child, WEEK, PERSON)
    ids = conn.execute(
        "select t.item_ids from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
        " where si.qr_code = %s",
        (made["qr"],),
    ).fetchone()["item_ids"]
    again = _round(
        conn,
        child,
        made["qr"],
        made["pdf_path"],
        ids,
        mistake,
        tmp_path / "next.pdf",
        monkeypatch,
        f"{code} {level}, its next paper",
    )
    assert again >= 1, f"{code} {level}: the next paper's questions could not show {mistake}"
    assert _counted(conn, child, mistake) == planted + again, (
        f"{code} {level}: the next paper's mistakes counted"
    )
