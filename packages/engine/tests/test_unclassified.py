"""The unclassified-answers report (ADR 0012).

A wrong answer no named mistake explains is already tagged `unclassified` at marking. This is
the report that gathers them so a person can see a pattern and name it — for any subject beyond
arithmetic it is the only way the mistake vocabulary grows.
"""

import os

import pytest

from engine.core import db
from engine.w1_bank import inventory

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def wrong_answers(conn):
    """Two children writing the same unexplained answer, one writing an explained one."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    item = conn.execute(
        "select id, responses from item where status='active' and skill_set_code='SUB.2D.EXCH'"
        " and difficulty='Hard' and fmt='column_grid' limit 1"
    ).fetchone()
    known = next(iter(next(r for r in item["responses"] if r["rid"] == "ans")["misconceptions"].items()))
    cap = conn.execute(
        "insert into capture (tenant_id, path, pages, status) values (%s,'test.pdf',1,'processed')"
        " returning id",
        (tenant,),
    ).fetchone()["id"]
    rows = [("8113", []), ("8113", []), (str(known[1]), [known[0]])]
    for i, (raw, codes) in enumerate(rows):
        c2 = conn.execute(
            "insert into capture (tenant_id, path, pages, status) values (%s,%s,1,'processed') returning id",
            (tenant, f"test-{i}.pdf"),
        ).fetchone()["id"]
        conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status,"
            " misconception_codes) values (%s,%s,%s,'ans',%s,'wrong',%s)",
            (tenant, c2, item["id"], raw, codes),
        )
    return cap


def test_an_unexplained_wrong_answer_is_surfaced_with_how_many_children_wrote_it(conn, wrong_answers):
    rows = inventory.unclassified(conn)
    mine = [r for r in rows if r["wrote"] == "8113"]
    assert mine and mine[0]["children"] == 2, "two children wrote it; that is the pattern to name"


def test_a_wrong_answer_a_named_mistake_already_explains_is_not_in_the_report(conn, wrong_answers):
    raws = {r["wrote"] for r in inventory.unclassified(conn)}
    explained = conn.execute(
        "select raw_read from item_result where cardinality(misconception_codes) > 0"
        " order by created_at desc limit 1"
    ).fetchone()
    assert explained["raw_read"] not in raws, "already diagnosed — not a candidate for a new name"


def test_the_report_is_ordered_by_how_many_children_made_the_mistake(conn, wrong_answers):
    counts = [r["children"] for r in inventory.unclassified(conn)]
    assert counts == sorted(counts, reverse=True), "the commonest unexplained answer comes first"
