"""The reader scored against what was said, and a typed transcript replayed (engine/w3_read/voice_check.py); the
retention of recordings (engine/w3_read/voice_store.py). Placeholder class, educator and children (tests/voice_rows.py),
in a rolled-back transaction: no school data."""

import json
import os

import pytest

from engine.core import db
from engine.w3_read import voice_check, voice_store
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(voice_store, "ROOT", tmp_path)
    with db.connect() as c:
        yield c
        c.rollback()


def test_each_note_is_scored_field_by_field_against_what_she_said(conn):
    k = a_k2_class(conn)
    right = a_note(conn, k, "Activity 12. Above 3. Absent 4. The rest did as expected.")
    misheard = a_note(conn, k, "Activity 12. Above 5. Below 1.")
    expected = [
        {
            "note_id": str(right["id"]),
            "activity": k["activity"],
            "above": ["3"],
            "absent": ["4"],
            "rest": True,
        },
        {"note_id": str(misheard["id"]), "activity": k["activity"], "above": ["2"], "below": ["1"]},
        {"note_id": "00000000-0000-0000-0000-000000000000", "activity": k["activity"]},
    ]
    s = voice_check.score(conn, expected)
    assert (s.notes, s.whole) == (2, 1)
    assert s.agreed["activity"] == 2 and s.agreed["above"] == 1 and s.agreed["below"] == 2
    assert s.wrong == {str(misheard["id"]): ["above"]}
    assert s.missing == ["00000000-0000-0000-0000-000000000000"]


def test_the_score_says_no_transcript_and_no_name(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3. She hummed the whole song to number 5.")
    lines = voice_check.score(
        conn, [{"note_id": str(note["id"]), "activity": k["activity"], "above": ["2"]}]
    ).lines()
    text = "\n".join(lines)
    assert "hummed" not in text and "Placeholder" not in text and "Activity 12" not in text
    assert f"{note['id']}: above" in text


def test_a_typed_transcript_is_read_against_the_class_and_writes_nothing(conn):
    k = a_k2_class(conn)
    before = conn.execute("select count(*) n from pii.educator_note").fetchone()["n"]
    found = voice_check.replay(conn, k["class"], "Activity 12. Above 3. Below 31. They built a tall tower.")
    assert found.activity == k["activity"] and found.problems == ["#31 is not in this class. Which child?"]
    lines = voice_check.replay_lines(found)
    assert "above: 3" in lines and "sentence: (5 words)" in lines
    assert not any("tower" in line for line in lines)
    assert conn.execute("select count(*) n from pii.educator_note").fetchone()["n"] == before


def test_with_no_retention_decided_every_recording_is_kept(conn, tmp_path):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3.", hours_ago=24 * 400)
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (note["id"],))
    voice_store.save(note["audio_key"], b"placeholder-audio")
    assert voice_store.retention(conn) == (None, 0)
    assert (tmp_path / note["audio_key"]).exists()


def test_a_retention_deletes_only_finished_recordings_older_than_it(conn, tmp_path):
    k = a_k2_class(conn)
    old = a_note(conn, k, "Activity 12. Above 3.", hours_ago=24 * 40)
    waiting = a_note(conn, k, "Activity 12. Above 4.", hours_ago=24 * 40)  # still drafted: kept
    young = a_note(conn, k, "Activity 12. Above 5.", hours_ago=24 * 5)
    for n in (old, young):
        conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (n["id"],))
    for n in (old, waiting, young):
        voice_store.save(n["audio_key"], b"placeholder-audio")
    conn.execute("update config set value = '30'::jsonb where key = 'voice.audio_retention_days'")
    assert voice_store.retention(conn) == (30, 1)
    assert [(tmp_path / n["audio_key"]).exists() for n in (old, waiting, young)] == [False, True, True]
    assert conn.execute(
        "select audio_key from pii.educator_note where id = %s", (old["id"],)
    ).fetchone()  # row kept


def test_the_expected_file_is_plain_json_a_person_can_write():
    entry = {"note_id": "x", "activity": "ACT-K2-0002", "above": ["3"], "rest": True}
    assert json.loads(json.dumps([entry]))[0]["above"] == ["3"]
    assert voice_check.FIELDS == ("activity", "above", "below", "not_willing", "absent", "rest")
