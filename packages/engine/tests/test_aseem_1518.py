"""M5c: Aseem's 56 × 3 = 1518 (goals/md5c-aseem-1518.yaml).

Question 18 of G3-QUIZ20 — the paper as the school printed it, entered from `supabase/seed/papers` — read as the child
wrote it, marked, confirmed, signed off, and into the graph. The handwriting reader is stood in, as in
`test_legacy.py`: the scan is not in the repository (rule 6), and reading handwriting is scored on its own.
"""

import pytest

from engine.adapters import ocr
from engine.assess import graph
from engine.core import db
from engine.w2_print import focus_paper
from engine.w3_read import legacy, marking

PAPER = db.REPO_ROOT / "supabase" / "seed" / "papers" / "G3-QUIZ20.json"
PERSON = "Aseem's paper"
WEEK = "2026-W42-1518"


@pytest.fixture
def conn():
    import os

    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def _child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '18', 'QUIZ20', 'G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Kabir')", (tenant, cid)
    )
    return cid


def _read(conn, child, scan, wrote, monkeypatch):
    """The paper's scan read for `child`, the reader stood in: `wrote` is what each question's box holds; every other
    box is blank. A wrong answer the engine read waits for a person, who confirms it as written."""
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg", b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(
        ocr,
        "answers_for",
        lambda page, slots, cfg=None, symbolic=(), boxes=(), reread=None: {
            s: {"child_answer": wrote.get(s, ""), "answer_state": "written" if s in wrote else "blank",
                "confidence": 99.0, "working_shown": "none"}
            for s in slots
        },
    )  # fmt: skip
    scan.write_bytes(scan.name.encode())  # a file of its own: the same file is read once
    s = legacy.import_scan(conn, scan, "G3-QUIZ20", child, PERSON)
    for r in conn.execute(
        "select id, item_id from item_result where capture_id = %s and status = 'needs_teacher'",
        (s["capture_id"],),
    ).fetchall():
        key = conn.execute("select item_key from item where id = %s", (r["item_id"],)).fetchone()["item_key"]
        n = key.rsplit("/", 1)[1]
        if n in wrote:
            marking.correct(conn, r["id"], wrote[n], PERSON)
    marking.confirm(conn, child, PERSON)
    return s


def test_56_times_3_written_1518_on_aseems_paper_is_named_counted_and_aimed_at(
    conn, tmp_path, monkeypatch, every_kind_trusted
):
    legacy.load_paper(conn, PAPER)
    _, items = legacy.paper_rows(conn, "G3-QUIZ20")
    q18 = items["18"]
    assert q18["spec"]["answer"] == 168, "56 × 3 is 168"
    assert q18["responses"][0]["misconceptions"].get("M_MUL_CONCAT") == 1518, (
        "1518 is each product side by side"
    )
    rung = conn.execute("select rung_code from item where id = %s", (q18["id"],)).fetchone()["rung_code"]
    assert rung == conn.execute("select rung_code from skill where code = 'MUL.2D1D'").fetchone()["rung_code"]

    child = _child(conn)
    _read(conn, child, tmp_path / "quiz20-kabir.pdf", {"18": "1518"}, monkeypatch)
    r = conn.execute(
        "select status, misconception_codes from item_result where item_id = %s", (q18["id"],)
    ).fetchone()
    assert r["status"] == "wrong" and r["misconception_codes"] == ["M_MUL_CONCAT"], dict(r)
    ev = conn.execute(
        "select skill_code, rung_code, correct, misconception_codes from evidence_event where child_id = %s"
        " and 'M_MUL_CONCAT' = any(misconception_codes)",
        (child,),
    ).fetchall()
    assert [(e["skill_code"], e["rung_code"], e["correct"]) for e in ev] == [("NUM.OPS.03", rung, False)], ev

    graph.rebuild(conn, child)
    once = conn.execute(
        "select state, n_events, n_correct, repeating_misconception from child_skill_state"
        " where child_id = %s and rung_code = %s",
        (child, rung),
    ).fetchone()
    assert once and once["n_events"] == 1 and once["n_correct"] == 0, once
    assert once["repeating_misconception"] is None, "made once, it is not yet the child's pattern"

    # made again on the next two quizzes: named as repeating from the second, and the child's pattern on MUL.2D1D once
    # the graph has as many of their answers there as the school's row asks before it says anything (`state.min_events`)
    least = conn.execute("select value from threshold where key = 'state.min_events'").fetchone()["value"]
    for n in range(2, int(least) + 1):
        _read(conn, child, tmp_path / f"quiz20-kabir-{n}.pdf", {"18": "1518"}, monkeypatch)
        graph.rebuild(conn, child)
        now = conn.execute(
            "select state, repeating_misconception from child_skill_state where child_id = %s and rung_code = %s",
            (child, rung),
        ).fetchone()
        assert now["repeating_misconception"] == "M_MUL_CONCAT", (n, now)
    assert now["state"] == "patterned_error", now
    conn.execute(
        "update skill set taught = true, taught_by = %s, taught_at = now() where code = 'MUL.2D1D'",
        (PERSON,),
    )
    nxt = focus_paper.plan(conn, child, WEEK)["areas"]
    assert nxt and nxt[0]["skill_set"] == "MUL.2D1D" and nxt[0]["mistake"] == "M_MUL_CONCAT", nxt[:1]
    assert any(q["shows_mistake"] for q in nxt[0]["questions"]), nxt[0]
