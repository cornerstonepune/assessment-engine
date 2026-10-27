"""One scan file is read by one reading at a time (goals/dbt_one_read_per_file.yaml).

Nimish, 2026-10-26: one 23-page file, "Read again" pressed several times; every reading but the first stopped with
"QueryCanceled: canceling statement due to statement timeout CONTEXT: while inserting index tuple … in relation
"sheet_instance"". That context is Postgres waiting on another transaction's uncommitted row with the same unique key:
a reading holds every copy's `sheet_instance` row in one transaction until the whole file is read, minutes, and a
second reading of the same file waits on the first copy's row until the statement timeout. "Read again" was refused only
on the run pressed, never on the file, so a press on an earlier row of the same file started a second reading."""

import os
import threading
import uuid

import pymupdf
import pytest

from engine.core import db
from engine.w3_read import inbox

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def scan(tmp_path, monkeypatch):
    """A file in an inbox of the test's own, under a name no other run has; its runs deleted afterwards."""
    monkeypatch.setattr(inbox, "INBOX", tmp_path)
    path = tmp_path / f"dbt-{uuid.uuid4().hex[:8]}.pdf"
    doc = pymupdf.open()
    doc.new_page()
    path.write_bytes(doc.tobytes())
    with db.connect() as c:
        tenant = str(db.one(c, "select id from tenant limit 1")["id"])
    yield path, tenant
    with db.connect() as c:
        c.execute("delete from flow_run where flow = %s and result ->> 'file' = %s", (inbox.FLOW, path.name))


def _finish(run_id, status="ok"):
    with db.connect() as c:
        c.execute("update flow_run set status = %s, finished_at = now() where id = %s", (status, run_id))


def test_a_file_being_read_is_not_read_a_second_time(scan):
    path, tenant = scan
    inbox.start(tenant, path, "nimish")
    with pytest.raises(inbox.Refused) as no:
        inbox.start(tenant, path, "nimish")
    assert no.value.status == 409 and "already being read" in str(no.value)


def test_read_again_on_an_earlier_row_of_the_file_is_refused_while_a_later_one_reads(scan):
    path, tenant = scan
    first = inbox.start(tenant, path, "nimish")
    _finish(first, "error")  # the row of an earlier attempt, its "Read again" button shown
    inbox.start(tenant, path, "nimish")  # the reading going on now
    with db.connect() as c:
        tenant_again = inbox.again(c, first)[1]
    with pytest.raises(inbox.Refused, match="already being read"):
        inbox.start(tenant_again, path, "nimish")


def test_once_the_reading_is_over_the_file_may_be_read_again(scan):
    path, tenant = scan
    for status in ("ok", "error"):
        _finish(inbox.start(tenant, path, "nimish"), status)
    assert inbox.start(tenant, path, "nimish")


def test_two_presses_at_the_same_moment_start_one_reading(scan):
    path, tenant = scan
    out, gate = [], threading.Barrier(4)

    def press():
        gate.wait()
        try:
            out.append(inbox.start(tenant, path, "nimish"))
        except inbox.Refused as no:
            out.append(no)

    threads = [threading.Thread(target=press) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(isinstance(o, str) for o in out) == 1, out


def test_a_page_is_not_given_while_another_reading_of_the_file_goes_on(scan):
    path, tenant = scan
    done = inbox.start(tenant, path, "nimish")
    with db.connect() as c:  # the finished run has a page waiting for its child
        c.execute(
            "update flow_run set status = 'ok', result = result || %s::jsonb where id = %s",
            ('{"copies": [{"copy": 1, "child_id": "c1", "no_code": [3]}]}', done),
        )
    inbox.start(tenant, path, "nimish")
    with db.connect() as c, pytest.raises(inbox.Refused, match="already being read"):
        inbox.give(c, done, 3, "c1", "nimish")


def test_the_route_says_already_being_read(scan, monkeypatch):
    from fastapi.testclient import TestClient

    from engine.api import deps
    from engine.api.app import app

    path, tenant = scan
    monkeypatch.setenv("ENGINE_KEY", "k")
    monkeypatch.setattr(inbox, "read", lambda *a, **k: [])
    app.dependency_overrides[deps.get_tenant_id] = lambda: tenant
    try:
        with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
            earlier = inbox.start(tenant, path, "nimish")
            _finish(earlier)
            inbox.start(tenant, path, "nimish")
            res = client.post(f"/read/run/{earlier}/again", json={"by": "nimish"})
    finally:
        app.dependency_overrides.clear()
    assert res.status_code == 409 and "already being read" in res.json()["detail"]
