"""The K2 voice-note routes (engine/api/routes/voice.py): each refuses while voice.screens_enabled is off, and when on,
a draft, a confirmation and her own recording reach only her. The website's calls run on the test's own transaction,
rolled back; the rows are placeholders (tests/voice_rows.py)."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db
from engine.w3_read import voice_note, voice_store
from tests.test_upload import token
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"


@pytest.fixture
def engine(monkeypatch):
    """→ (the website's client, the test's connection). The routes read and write on that connection only."""
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with db.connect() as conn:
        app.dependency_overrides[deps.get_conn] = lambda: conn
        try:
            with TestClient(app) as client:
                yield client, conn
        finally:
            app.dependency_overrides.clear()
            conn.rollback()


def _switch(conn, on: bool):
    conn.execute(
        "update config set value = %s::jsonb where key = 'voice.screens_enabled'",
        ("true" if on else "false",),
    )


def _record(conn, on: bool | None):
    """`voice.recording_enabled`: on, off, or (None) no row at all, which reads as off."""
    conn.execute("delete from config where key = 'voice.recording_enabled'")
    if on is not None:
        conn.execute(
            "insert into config (tenant_id, key, value, description) select id, 'voice.recording_enabled', %s::jsonb,"
            " 'test' from tenant",
            ("true" if on else "false",),
        )


def _post(client, path, body):
    return client.post(path, json=body, headers={"X-Engine-Key": KEY})


def test_every_route_refuses_while_voice_notes_are_switched_off(engine):
    client, conn = engine
    k = a_k2_class(conn)
    _switch(conn, False)
    for path, body in (
        ("/voice/queue", {"actor": k["email"]}),
        ("/voice/notes/draft", {"actor": k["email"], "note_id": "00000000-0000-0000-0000-000000000000"}),
        ("/voice/class", {"actor": k["email"], "class_id": k["class"]}),
        ("/voice/form", {"actor": k["email"], "class_id": k["class"], "activity": k["activity"], "level": 2}),
    ):
        r = _post(client, path, body)
        assert (r.status_code, r.json()["detail"]) == (403, "Voice notes are not switched on."), path


def test_a_draft_shows_each_line_beside_its_words_and_confirm_writes_her_rows(engine):
    client, conn = engine
    k = a_k2_class(conn)
    _switch(conn, True)
    note = a_note(conn, k, "Activity 12. Above 3. Below 31.")
    me = {"actor": k["email"], "note_id": str(note["id"])}
    draft = _post(client, "/voice/notes/draft", me).json()
    assert draft["activity"] == k["activity"] and draft["blocked"] is True
    assert [(x["section"], x["words"]) for x in draft["lines"]] == [
        ("activity", "Activity 12"), ("above", "Above 3"), ("below", "Below 31"),
    ]  # fmt: skip
    assert draft["problems"] == ["#31 is not in this class. Which child?"]
    assert draft["enrolled"] == ["1", "2", "3", "4", "5"]
    done = _post(
        client,
        "/voice/notes/confirm",
        me | {"activity": k["activity"], "level": 2, "lists": {"above": ["3"]}},
    )
    assert done.status_code == 200, done.text
    n = conn.execute(
        "select count(*) n from activity_observation where confirmation_id = %s",
        (done.json()["confirmation_id"],),
    ).fetchone()["n"]
    assert n == 1


def test_a_note_and_its_recording_reach_only_the_educator_who_made_it(engine):
    client, conn = engine
    mine, theirs = a_k2_class(conn), a_k2_class(conn)
    _switch(conn, True)
    _record(conn, True)  # the recording is reached only with recording on; this test is about whose it is
    note = a_note(conn, theirs, "Activity 12. Above 3.")
    for path in ("/voice/notes/draft", "/voice/notes/audio"):
        r = _post(client, path, {"actor": mine["email"], "note_id": str(note["id"])})
        assert r.status_code == 404, path
    r = _post(client, "/voice/queue", {"actor": "nobody@example.test"})
    assert r.status_code == 403


def test_a_recording_needs_the_sites_token_and_voice_notes_switched_on(engine, monkeypatch):
    client, conn = engine
    monkeypatch.setattr(db, "connect", lambda *a, **k: _held(conn))
    k = a_k2_class(conn)
    _switch(conn, False)
    files = {"file": ("note.m4a", b"placeholder-audio")}
    assert client.post("/voice/notes", files=files, data={"class_id": k["class"]}).status_code == 401
    r = client.post(
        "/voice/notes",
        files=files,
        data={"class_id": k["class"]},
        headers={"X-Upload-Token": token(k["email"], key=KEY)},
    )
    assert r.status_code == 403


class _held:
    """The test's own connection, handed to a route that opens one itself; never closed or committed by it."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


def test_her_classes_come_from_her_grant_today_and_a_draft_carries_the_level_she_expected_and_whether_anything_was_heard(
    engine,
):
    """The Record row lists the classes she records for today: an open grant in a role that records (config
    `voice.roles_that_record`), on a class whose grade has activities; never one she typed, never a role that does not
    record, never a grant that has ended. The draft says the level she expected, or the template's default."""
    client, conn = engine
    k, assisted, ended = a_k2_class(conn), a_k2_class(conn), a_k2_class(conn)
    _switch(conn, True)
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)"
        " values (%s, %s, 'assistant', %s, current_date - 1, 'test')",
        (k["tenant"], k["staff"], assisted["class"]),
    )
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, valid_to,"
        " granted_by) values (%s, %s, 'cover_educator', %s, current_date - 9, current_date - 2, 'test')",
        (k["tenant"], k["staff"], ended["class"]),
    )
    got = _post(client, "/voice/queue", {"actor": k["email"]}).json()
    assert [c["id"] for c in got["classes"]] == [k["class"]]
    assert got["classes"][0]["grade"] == "K2"
    said = a_note(conn, k, "Activity 12, level 3. Above 3.")
    plain = a_note(conn, k, "Activity 12. Above 3.")

    def draft(note) -> dict:
        me = {"actor": k["email"], "note_id": str(note["id"])}
        return _post(client, "/voice/notes/draft", me).json()

    assert draft(said)["level"] == 3
    assert draft(plain)["level"] == voice_note.template().default_level
    assert draft(plain)["heard"] is True and draft(a_note(conn, k, ""))["heard"] is False


@pytest.mark.parametrize("recording", [None, False])
def test_with_recording_off_no_route_takes_or_gives_a_recording_and_the_form_still_works(
    engine, monkeypatch, recording
):
    """D-065: no child's voice is kept or sent on until Nimish turns recording on, separately from the screens. With
    the screens on and recording off (or its row missing), the upload and the playback refuse in words, nothing is
    written to disk, and the form, the class and the queue answer; the queue says recording is off."""
    client, conn = engine
    monkeypatch.setattr(db, "connect", lambda *a, **k: _held(conn))
    kept = []
    monkeypatch.setattr(voice_store, "save", lambda key, data: kept.append(key))
    k = a_k2_class(conn)
    _switch(conn, True)
    _record(conn, recording)
    up = client.post(
        "/voice/notes",
        files={"file": ("note.m4a", b"placeholder-audio")},
        data={"class_id": k["class"]},
        headers={"X-Upload-Token": token(k["email"], key=KEY)},
    )
    assert (up.status_code, up.json()["detail"]) == (403, "Recording is not switched on.")
    assert kept == []
    note = a_note(conn, k, "Activity 12. Above 3.")
    heard = _post(client, "/voice/notes/audio", {"actor": k["email"], "note_id": str(note["id"])})
    assert (heard.status_code, heard.json()["detail"]) == (403, "Recording is not switched on.")
    queued = _post(client, "/voice/queue", {"actor": k["email"]})
    assert queued.status_code == 200 and queued.json()["recording"] is False
    assert _post(client, "/voice/class", {"actor": k["email"], "class_id": k["class"]}).status_code == 200
    saved = _post(
        client,
        "/voice/form",
        {
            "actor": k["email"],
            "class_id": k["class"],
            "activity": k["activity"],
            "level": 2,
            "lists": {"above": ["3"]},
        },
    )
    assert saved.status_code == 200, saved.text


def test_with_both_switches_on_a_recording_is_taken_and_the_queue_says_so(engine, monkeypatch):
    client, conn = engine
    monkeypatch.setattr(db, "connect", lambda *a, **k: _held(conn))
    kept = []
    monkeypatch.setattr(voice_store, "save", lambda key, data: kept.append(key))
    k = a_k2_class(conn)
    _switch(conn, True)
    _record(conn, True)
    up = client.post(
        "/voice/notes",
        files={"file": ("note.m4a", b"placeholder-audio")},
        data={"class_id": k["class"]},
        headers={"X-Upload-Token": token(k["email"], key=KEY)},
    )
    assert up.status_code == 200, up.text
    assert len(kept) == 1
    assert _post(client, "/voice/queue", {"actor": k["email"]}).json()["recording"] is True
