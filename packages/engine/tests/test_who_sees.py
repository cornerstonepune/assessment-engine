"""Who sees a child's answers and papers (goals/own_who_sees_answers.yaml).

Nimish, 27 Oct 2026: "their assessments, answers to be checked etc. should be restricted to their grade ... Achal should
only see the papers he has uploaded." The rule is one database function, `staff_sees` (migration 20261220090000), that the
website asks of everything it shows; these hold the rule itself, the staff ids it is asked with, and the uploader every
new upload records.
"""

import json
import os
import uuid
from pathlib import Path

import pytest

from engine.core import db
from engine.w3_read import inbox
from tests.rows import a_read_paper, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

ME = str(uuid.uuid4())
SOMEONE = str(uuid.uuid4())


@pytest.mark.parametrize(
    ("role", "classes", "subjects", "section", "subject", "uploaded_by", "sees"),
    [
        ("coordinator", [], [], "2A", "MATH", None, True),  # a coordinator sees everything
        ("coordinator", [], [], None, None, None, True),  # ... every class, even one it was not asked about
        ("educator", ["2A"], [], "2A", "MATH", None, True),  # a class on their entry
        ("educator", ["2A"], [], "2B", "MATH", None, False),  # another class
        ("educator", ["2A"], [], "2B", "MATH", ME, True),  # another class, but they put it in
        ("educator", ["2A"], [], "2B", "MATH", SOMEONE, False),  # another class, put in by someone else
        ("educator", ["2A"], ["MATH"], "2A", "ENG", None, False),  # their class, a subject not theirs
        ("educator", ["2A"], ["MATH"], "2A", "MATH", None, True),
        ("educator", ["2A"], ["MATH"], "2A", None, None, True),  # a thing with no subject: the class decides
        (
            "educator",
            ["2A"],
            ["MATH"],
            "2B",
            "ENG",
            ME,
            True,
        ),  # what they put in is theirs, whatever its subject
        ("educator", [], [], "2A", "MATH", None, False),  # linked to no class: only what they put in
        ("educator", [], [], None, None, None, False),  # ... and so not every class
        ("educator", [], [], None, None, ME, True),  # a scan not yet sorted onto a paper, theirs
    ],
)
def test_the_one_rule(role, classes, subjects, section, subject, uploaded_by, sees):
    with db.connect() as conn:
        got = conn.execute(
            "select staff_sees(%s, %s::text[], %s::text[], %s::uuid, %s, %s, %s::uuid) as s",
            (role, classes, subjects, ME, section, subject, uploaded_by),
        ).fetchone()["s"]
    assert got is sees


@pytest.fixture
def person():
    """A member of staff of the test's own, taken off the list again after."""
    email = f"who-sees-{uuid.uuid4().hex[:6]}@cornerstone.test"
    with db.connect() as conn:
        conn.execute(
            "update config set value = value || %s::jsonb where key = 'app.staff'",
            (json.dumps([{"email": email, "name": "Who Sees", "role": "educator", "classes": []}]),),
        )
        conn.commit()
    yield email
    with db.connect() as conn:
        conn.execute(
            "update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s"
            " where s ->> 'email' <> %s) where key = 'app.staff'",
            (email,),
        )
        conn.commit()


def test_every_member_of_staff_has_an_id_that_a_rewrite_of_the_list_keeps(person):
    with db.connect() as conn:
        first = conn.execute("select staff_id(%s) as id", (person.upper(),)).fetchone()["id"]
        assert first is not None
        # the website writes the whole list back when a class is changed: the id stays
        conn.execute(
            "update config set value = (select jsonb_agg(case when s ->> 'email' = %s"
            ' then s || \'{"classes": ["2A"]}\'::jsonb else s end) from jsonb_array_elements(value) s)'
            " where key = 'app.staff'",
            (person,),
        )
        assert conn.execute("select staff_id(%s) as id", (person,)).fetchone()["id"] == first
        assert conn.execute("select staff_id('nobody@cornerstone.test') as id").fetchone()["id"] is None


def test_a_paper_is_seen_by_its_class_and_by_whoever_put_it_in():
    with db.connect() as conn:
        paper = a_read_paper(conn, [{"status": "correct", "read": "35"}])
        section = conn.execute("select section from child where id = %s", (paper["child"],)).fetchone()[
            "section"
        ]
        sheet = conn.execute(
            "select sheet_instance_id as id from capture where id = %s", (paper["capture"],)
        ).fetchone()["id"]

        def sees(classes, staff=ME):
            return conn.execute(
                "select staff_sees_sheet('educator', %s::text[], '{}', %s::uuid, %s) as s,"
                " staff_sees_capture('educator', %s::text[], '{}', %s::uuid, %s) as c",
                (classes, staff, sheet, classes, staff, paper["capture"]),
            ).fetchone()

        assert sees([section]) == {"s": True, "c": True}
        assert sees(["SOME-OTHER-CLASS"]) == {"s": False, "c": False}
        conn.execute("update capture set uploaded_by = %s where id = %s", (ME, paper["capture"]))
        assert sees(["SOME-OTHER-CLASS"]) == {"s": True, "c": True}
        assert sees(["SOME-OTHER-CLASS"], SOMEONE) == {"s": False, "c": False}
        conn.rollback()


def test_an_upload_records_who_put_it_in_and_a_reading_again_keeps_it(person, monkeypatch, tmp_path):
    t = None
    with db.connect() as conn:
        t = str(tenant(conn))
        paper = a_read_paper(conn, [{"status": "correct", "read": "35"}])
        conn.commit()
    name = f"who-sees-{uuid.uuid4().hex[:6]}.pdf"
    path = tmp_path / name
    path.write_bytes(b"%PDF-")
    runs = []
    try:
        run = inbox.start(t, path, person, pages=1)
        runs.append(run)
        # the reading itself is the reader's; here it read the one copy above
        monkeypatch.setattr(inbox.copies, "read", lambda *a, **k: [{"capture_id": paper["capture"]}])
        inbox.read(run, Path(path), person)
        again = inbox.start(t, path, "someone-else@cornerstone.test", pages=1, of_run=run)
        runs.append(again)
        strange = inbox.start(t, tmp_path / f"x-{name}", "nobody@cornerstone.test", pages=1)
        runs.append(strange)
        with db.connect() as conn:
            me = conn.execute("select staff_id(%s) as id", (person,)).fetchone()["id"]
            by = {
                r["id"]: r["uploaded_by"]
                for r in conn.execute(
                    "select id::text, uploaded_by from flow_run where id = any(%s::uuid[])", (runs,)
                ).fetchall()
            }
            assert by == {run: me, again: me, strange: None}  # never a guess
            cap = conn.execute(
                "select uploaded_by from capture where id = %s", (paper["capture"],)
            ).fetchone()
            assert cap["uploaded_by"] == me
    finally:
        with db.connect() as conn:
            conn.execute("delete from flow_run where id = any(%s::uuid[])", (runs,))
            conn.commit()
