"""Where each answer stands (goal u3-marking): waiting for a person, settled by the engine, or checked by a person.

One definition, in the database (`answer_standing`), read by `engine read waiting` and the Marking screen alike, so
the two can never count differently. Against the real schema, rolled back.
"""

import os

import pytest

from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def paper(conn):
    """One child's read paper holding one answer of each kind; returns its sheet and the answers by name."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','STANDINGTEST','G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    items = [
        r["id"] for r in conn.execute("select id from item where status = 'active' order by item_key limit 5")
    ]
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, week, item_ids, source, key) values (%s,'G2','STANDING-TEST',%s,'legacy',"
        ' \'{"title": "Standing test"}\') returning id',
        (tenant, items),
    ).fetchone()["id"]
    sheet = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s,'STANDING-TEST',%s,%s,'returned') returning id",
        (tenant, template, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, pages, status, sheet_instance_id)"
        " values (%s,'standing.pdf',1,'processed',%s) returning id",
        (tenant, sheet),
    ).fetchone()["id"]
    kinds = {
        "engine_right": ("correct", '{"child_answer": "7", "answer_state": "written"}'),
        "engine_wrong": ("wrong", '{"child_answer": "9", "answer_state": "written"}'),
        "unreadable": ("unreadable", '{"child_answer": "", "why": "no number"}'),
        "to_judge": ("needs_teacher", '{"child_answer": "<", "answer_state": "written"}'),
        "typed": ("unreadable", '{"child_answer": "", "why": "no number"}'),
    }
    ids = {}
    for (name, (status, raw)), item in zip(kinds.items(), items):
        ids[name] = conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status)"
            " values (%s,%s,%s,'ans',%s,%s) returning id",
            (tenant, cap, item, raw, status),
        ).fetchone()["id"]
    # a person typed what the child wrote, and the engine marked it
    conn.execute(
        "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)"
        " values (%s,%s,%s,%s,'','12','teacher@school.test')",
        (tenant, child, cap, ids["typed"]),
    )
    conn.execute("update item_result set status = 'correct' where id = %s", (ids["typed"],))
    return {"sheet": sheet, "capture": cap, "child": child, "tenant": tenant, **ids}


def standing(conn, sheet):
    rows = conn.execute(
        "select item_result_id, standing, signed_off from answer_standing where sheet_instance_id = %s",
        (sheet,),
    ).fetchall()
    return {r["item_result_id"]: (r["standing"], r["signed_off"]) for r in rows}


def test_each_answer_is_waiting_settled_by_the_engine_or_checked_by_a_person(conn, paper):
    s = standing(conn, paper["sheet"])
    assert s[paper["engine_right"]] == ("engine", False)
    assert s[paper["engine_wrong"]] == ("engine", False)
    assert s[paper["unreadable"]] == ("waiting", False)
    assert s[paper["to_judge"]] == ("waiting", False)
    assert s[paper["typed"]] == ("person", False)
    assert len(s) == 5


def test_a_judgement_made_on_a_paper_is_recorded_as_a_persons_check(conn, paper):
    """resolve_result (a paper's or a child's Right / Wrong / Blank) now leaves the same record as the queue does."""
    conn.execute("select resolve_result(%s, 'wrong', '{}', 'teacher@school.test')", (paper["to_judge"],))
    said = conn.execute(
        "select judged, by, human_read from read_correction where item_result_id = %s", (paper["to_judge"],)
    ).fetchone()
    assert said == {"judged": "wrong", "by": "teacher@school.test", "human_read": "<"}
    s = standing(conn, paper["sheet"])
    assert s[paper["to_judge"]] == ("person", True)
    # signing off is the person standing behind the whole paper; who settled each mark is unchanged
    assert s[paper["engine_right"]] == ("engine", True)


def test_a_superseded_read_is_not_counted(conn, paper):
    newer = conn.execute(
        "insert into capture (tenant_id, path, pages, status, sheet_instance_id)"
        " values (%s,'standing-2.pdf',1,'processed',%s) returning id",
        (paper["tenant"], paper["sheet"]),
    ).fetchone()["id"]
    conn.execute("update capture set superseded_by = %s where id = %s", (newer, paper["capture"]))
    assert standing(conn, paper["sheet"]) == {}
