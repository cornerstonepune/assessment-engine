"""W2's HTTP surface: the three calls F2 makes, against the real schema in a rolled-back
transaction. What is checked here is the wiring — that a route forwards to the function the CLI
uses and shapes what n8n needs — not the week logic, which `test_week.py` and the W2 scenarios own.
"""

import os

import pytest
from fastapi.testclient import TestClient

from engine import db
from engine.api import deps
from engine.api.app import app

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SECTION, WEEK, SET = "APISEC", "api-week", "SUB.2D.EXCH"
KEY = "test-engine-key"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    app.dependency_overrides[deps.get_tenant_id] = lambda: conn.execute(
        "select id from tenant where slug = %s", (db.tenant_slug(),)
    ).fetchone()["id"]
    with TestClient(app, headers={"X-Engine-Key": KEY}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def children(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute("delete from child where section = %s", (SECTION,))
    for i in (1, 2):
        row = conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2') returning id",
            (tenant, str(i), SECTION),
        ).fetchone()
        conn.execute(
            "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)",
            (tenant, row["id"], f"Api {i}"),
        )
    return None  # no commit: the route shares this connection and the fixture rolls it back


def test_prescribe_then_assemble_over_http(client, children):
    r = client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prescribed"] == 2 and sum(body["by_rule"].values()) == 2

    r = client.post("/week/assemble", json={"section": SECTION, "week": WEEK})
    assert r.status_code == 200, r.text
    built = r.json()
    assert built["sheets"] == 2 and built["spares"] >= 1
    assert len(built["qr_codes"]) == built["sheets"] + built["spares"]
    assert len(set(built["qr_codes"])) == len(built["qr_codes"])
    assert built["short"] == []


def test_assembling_the_same_week_twice_is_one_week(client, children):
    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    first = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()
    again = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()
    assert again["already"] is True, "the same week assembled twice must not print a second set"
    assert again["qr_codes"] == first["qr_codes"]


def test_a_sheet_cannot_be_printed_without_someone_approving_it(client, children, conn):
    """The gate is the database's, not the application's: mark a sheet printed with no approver and
    the constraint refuses it. Before this, `print_status` was a label any code could set."""
    import psycopg
    import pytest as _pytest

    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    built = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()
    qr = built["qr_codes"][0]
    with _pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "update sheet_instance set print_status = 'printed', printed_at = now() where qr_code = %s",
            (qr,),
        )
    conn.rollback()


def test_approving_the_week_names_the_person_on_every_sheet(client, children, conn):
    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    built = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()
    r = client.post("/week/approve", json={"section": SECTION, "week": WEEK, "by": "neha@example.org"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sheets"] == built["sheets"] + built["spares"]
    assert body["named"] == built["sheets"] and body["spares"] == built["spares"]
    rows = conn.execute(
        "select print_status, approved_by from sheet_instance where qr_code = any(%s)",
        (built["qr_codes"],),
    ).fetchall()
    assert {(x["print_status"], x["approved_by"]) for x in rows} == {("printed", "neha@example.org")}

    again = client.post(
        "/week/approve", json={"section": SECTION, "week": WEEK, "by": "someone@else.org"}
    ).json()
    assert again["already"] is True or again["sheets"] == 0, "a second approval approves nothing further"


def test_a_papers_page_is_served_as_printed(client, children, conn, tmp_path):
    """The paper view shows the page itself — QR and all — from the PDF the render wrote, never a
    second drawing of it."""
    import pymupdf

    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    qr = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()["qr_codes"][0]
    pdf = tmp_path / f"{qr}.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), qr)
        doc.save(pdf)
    conn.execute("update sheet_instance set pdf_path = %s where qr_code = %s", (str(pdf), qr))

    r = client.get(f"/sheet/{qr}/page/1.jpg")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"


def test_a_paper_never_rendered_or_unknown_is_not_found(client, children):
    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    qr = client.post("/week/assemble", json={"section": SECTION, "week": WEEK}).json()["qr_codes"][0]
    assert client.get(f"/sheet/{qr}/page/1.jpg").status_code == 404
    assert client.get("/sheet/CS000000/page/1.jpg").status_code == 404


def test_a_child_who_cannot_be_given_a_worksheet_is_named_in_the_answer(client, children, conn):
    """A short child's row carries the child's id, and the result is stored for replay as JSON: the
    id has to arrive as text, or the whole assembly fails and nobody is told why (step 7)."""
    client.post("/week/prescribe", json={"section": SECTION, "week": WEEK, "skill_set": SET})
    conn.execute(
        "update sheet_template set retired_at = now() where source = 'library' and skill_set_code = %s",
        (SET,),
    )
    r = client.post("/week/assemble", json={"section": SECTION, "week": WEEK})
    assert r.status_code == 200, r.text
    short = r.json()["short"]
    assert short and all(s["why"] and isinstance(s["child_id"], str) for s in short)
