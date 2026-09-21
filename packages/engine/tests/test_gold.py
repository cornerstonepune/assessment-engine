"""W3's gold end to end (ADR 0028): a child's 8500 − 3647 = 5147 goes from the page to the named
mistake in the child's graph, and `engine gold check` says so — and names what stands in the way
when it does not, the first thing first. On the copy, inside one rolled-back transaction."""

import json
import os

import pytest

from engine import db, gold, legacy
from engine.adapters import llm, ocr
from engine.assess import graph

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

PAPER = {
    "code": "GOLD-TEST",
    "title": "gold test",
    "band": "G3",
    "week": "test",
    "date": "2026-09-11",
    "pages": [{"n": 1, "mask": 0}],
    "items": [{"n": 1, "page": 1, "expr": "8500 - 3647", "question": "8,500 - 3,647 ="}],
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','TESTSEC','G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Goldtest')", (tenant, cid)
    )
    return cid


def _read(conn, child, tmp_path, monkeypatch, wrote):
    """Enter the paper and read one scan of it, the reader standing in to say the child wrote `wrote`."""
    paper = tmp_path / "paper.json"
    paper.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, paper)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, *a, **k: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(
        ocr,
        "answers_for",
        lambda page, slots, *a, **k: {
            "1": {
                "child_answer": wrote,
                "answer_state": "written",
                "confidence": 99.0,
                "working_shown": "none",
            }
        },
    )
    monkeypatch.setattr(llm, "generate", lambda *a, **k: pytest.fail("a sure reading needs no model"))
    legacy.import_scan(conn, scan, "GOLD-TEST", child, "test")
    item = conn.execute("select skill_codes from item where item_key = 'legacy/GOLD-TEST/1'").fetchone()
    return item["skill_codes"][0]


def _transcribe(tmp_path, skill):
    path = tmp_path / "gold.json"
    path.write_text(
        json.dumps(
            {
                "source": "a test report",
                "findings": [
                    {
                        "child": "Goldtest",
                        "verdict": "faulty",
                        "skill": skill,
                        "item": "legacy/GOLD-TEST/1",
                        "mark": "wrong",
                        "answer": "5147",
                        "mistake": "M_SMALL_FROM_LARGE",
                        "words": "subtracts the smaller digit from the larger in each column (8500-3647=5147)",
                    }
                ],
            }
        )
    )
    return path


def _outcome(conn, child):
    return next(r["outcome"] for r in gold.check(conn) if r["child_id"] == child)


def test_the_mistake_a_teacher_named_comes_back_out_of_the_graph(conn, child, tmp_path, monkeypatch):
    skill = _read(conn, child, tmp_path, monkeypatch, "5147")
    path = _transcribe(tmp_path, skill)
    assert gold.load(conn, path) == 1
    assert _outcome(conn, child) == "transcription not yet confirmed"

    gold.confirm(conn, "a person")
    assert _outcome(conn, child) == "not yet signed off"

    legacy.confirm(conn, child, "a person")
    graph.rebuild(conn, child)
    assert _outcome(conn, child) == "in the graph"

    # loading the same file again changes nothing, and keeps the confirmation
    gold.load(conn, path)
    assert _outcome(conn, child) == "in the graph"


def test_a_misread_is_named_as_a_misread_not_as_a_wrong_diagnosis(conn, child, tmp_path, monkeypatch):
    skill = _read(conn, child, tmp_path, monkeypatch, "4853")  # the reader saw the right answer
    gold.load(conn, _transcribe(tmp_path, skill))
    gold.confirm(conn, "a person")
    assert _outcome(conn, child) == "read differently"


def test_changing_a_finding_withdraws_its_confirmation(conn, child, tmp_path, monkeypatch):
    skill = _read(conn, child, tmp_path, monkeypatch, "5147")
    path = _transcribe(tmp_path, skill)
    gold.load(conn, path)
    gold.confirm(conn, "a person")
    spec = json.loads(path.read_text())
    spec["findings"][0]["answer"] = "5174"
    path.write_text(json.dumps(spec))
    gold.load(conn, path)
    assert _outcome(conn, child) == "transcription not yet confirmed"
