"""K2 voice notes (goals/m1-01-voice-intake.yaml). Step 1: the recording never reaches git."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIO = (".m4a", ".mp3", ".wav", ".ogg", ".opus", ".webm", ".aac", ".flac")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def test_git_refuses_every_kind_of_voice_recording_and_holds_none():
    for ext in AUDIO:
        assert _git("check-ignore", "-q", f"anywhere/note{ext}").returncode == 0, (
            f"git would keep a {ext} file"
        )
    tracked = _git("ls-files").stdout.splitlines()
    assert [p for p in tracked if p.lower().endswith(AUDIO)] == []


# --- the note from the phone to a draft (needs a database: placeholder rows, rolled back) ---

import os  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

from engine.core import db  # noqa: E402
from engine.w3_read import voice_intake, voice_store  # noqa: E402
from tests.voice_rows import a_k2_class, a_note  # noqa: E402

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(
        voice_store, "ROOT", tmp_path
    )  # a recording in a test never lands in the repo's data/
    with db.connect() as c:
        yield c
        c.rollback()


@needs_db
def test_a_recording_is_kept_on_the_private_side_and_only_its_key_is_in_the_row(conn, tmp_path):
    k = a_k2_class(conn)
    note = voice_intake.receive(conn, k["email"], k["class"], "note.m4a", b"placeholder-audio")
    assert note["status"] == "received" and note["transcript"] is None
    assert note["audio_key"] == f"voice/{note['received_at'].year}/{note['id']}.m4a"
    assert (tmp_path / note["audio_key"]).read_bytes() == b"placeholder-audio"
    with pytest.raises(voice_store.Refused, match="not on the staff list"):
        voice_intake.receive(conn, "nobody@example.test", k["class"], "note.m4a", b"x")
    other = a_k2_class(conn)  # an educator who does not hold this class
    with pytest.raises(voice_store.Refused, match="do not hold this class"), conn.transaction():
        voice_intake.receive(conn, other["email"], k["class"], "note.m4a", b"x")
    with pytest.raises(voice_store.Refused, match="not a recording"):
        voice_intake.receive(conn, k["email"], k["class"], "note.pdf", b"x")
    before = sorted(p.name for p in tmp_path.rglob("*") if p.is_file())
    for cls in ("00000000-0000-0000-0000-000000000000", "not-a-class"):
        with pytest.raises(voice_store.Refused), conn.transaction():
            voice_intake.receive(conn, k["email"], cls, "note.m4a", b"placeholder-audio")
    assert (
        sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == before
    )  # a refused note keeps no recording


@needs_db
def test_the_words_come_from_speech_to_text_and_the_note_is_drafted(conn, monkeypatch):
    k = a_k2_class(conn)
    note = voice_intake.receive(conn, k["email"], k["class"], "note.m4a", b"placeholder-audio")
    reply = {"request_id": "r", "transcript": "Activity 12. Above 3.", "language_code": "en-IN"}
    stub = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=reply)))
    monkeypatch.setenv("SARVAM_API_KEY", "stub")  # the stub answers; no live call is made
    assert voice_intake.transcribe(conn, str(note["id"]), stub) == "Activity 12. Above 3."
    after = conn.execute(
        "select status, transcript from pii.educator_note where id = %s", (note["id"],)
    ).fetchone()
    assert after == {"status": "drafted", "transcript": "Activity 12. Above 3."}


@needs_db
def test_the_activity_and_every_number_are_found_in_the_class_and_a_stranger_is_a_problem(conn):
    k = a_k2_class(conn)
    found = voice_intake.resolve(
        conn, a_note(conn, k, "Activity 12. Above 3. Below 1, 31. The rest did as expected.")
    )
    assert found.activity == k["activity"]
    assert found.children == {"3": k["children"]["3"], "1": k["children"]["1"]}
    assert found.problems == ["#31 is not in this class. Which child?"] and found.blocked
    assert found.count_line() == "1 above, 2 below, 3 as expected = 6"
    lost = voice_intake.resolve(conn, a_note(conn, k, "Activity 99. Above 2."))
    assert lost.problems == ["Activity 99 is not on the list. Search by number or name."]
    assert voice_intake.resolve(conn, a_note(conn, k, "Activity 12. Above 2.")).count_line() == (
        "1 named; the other 4 not seen"
    )


@needs_db
def test_a_note_waits_48_hours_then_is_left_unconfirmed_and_leaves_the_queue(conn):
    k = a_k2_class(conn)
    fresh = a_note(conn, k, "Activity 12. Above 3.")
    old = a_note(conn, k, "Activity 12. Above 4.", hours_ago=49)
    assert [n["id"] for n in voice_intake.queue(conn, str(k["staff"]))] == [fresh["id"]]
    assert voice_intake.expire(conn) >= 1
    status = conn.execute("select status from pii.educator_note where id = %s", (old["id"],)).fetchone()[
        "status"
    ]
    assert status == "left_unconfirmed"
    assert (
        conn.execute(
            "select count(*) n from activity_observation where note_id = %s", (old["id"],)
        ).fetchone()["n"]
        == 0
    )


def test_a_key_that_is_not_a_recordings_names_no_file():
    for bad in ("../../.env", "voice/2026/x.m4a", "scans/2026/" + "0" * 36 + ".pdf"):
        with pytest.raises(voice_store.Refused):
            voice_store.path(bad)


@needs_db
def test_a_note_is_about_the_day_on_the_schools_clock_not_the_servers(conn):
    """Heard at 03:54 in Pune on 4 Nov is 22:24 UTC on 3 Nov: the note is about 4 Nov."""
    import datetime as dt

    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 2.")
    conn.execute("alter table pii.educator_note disable trigger educator_note_clock")
    conn.execute(
        "update pii.educator_note set received_at = '2026-11-03 22:24:00+00' where id = %s", (note["id"],)
    )
    conn.execute("alter table pii.educator_note enable trigger educator_note_clock")
    note = conn.execute("select * from pii.educator_note where id = %s", (note["id"],)).fetchone()
    assert voice_intake.resolve(conn, note).taught_on == dt.date(2026, 11, 4)
