"""`engine read voice switch screens|recording on|off --by <email>` (engine/w3_read/voice_switch.py): the two K2 voice
switches turned by a command that says who turned them, never by hand on live. Recording does not go on without the
reference of Sarvam's written confirmation of "No retention" (D-065). Placeholder rows only (tests/voice_rows.py)."""

import os

import pytest
from typer.testing import CliRunner

from engine.cli import app
from engine.core import db, settings
from engine.w3_read import voice_switch
from tests.voice_rows import a_k2_class

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


class _held:
    """The test's own connection, handed to the command; never closed or committed by it."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


def _logged(conn, staff) -> list[str]:
    return [
        r["action"]
        for r in conn.execute(
            "select action from access_log where actor = %s and action like 'voice.%%' order by occurred_at, id",
            (str(staff),),
        ).fetchall()
    ]


def test_a_member_of_staff_turns_the_screens_on_and_off_and_each_turn_is_logged_by_staff_id(conn):
    k = a_k2_class(conn)
    said = voice_switch.switch(conn, "screens", True, k["email"])
    assert settings.config(conn, "voice.screens_enabled", False) is True
    assert k["email"] not in said
    voice_switch.switch(conn, "screens", False, k["email"])
    assert settings.config(conn, "voice.screens_enabled", True) is False
    assert _logged(conn, k["staff"]) == ["voice.screens_enabled on", "voice.screens_enabled off"]


def test_recording_does_not_go_on_without_the_written_no_retention_reference(conn):
    k = a_k2_class(conn)
    conn.execute("delete from config where key = 'voice.recording_enabled'")
    for ref in (None, "", "   "):
        with pytest.raises(ValueError, match="retention-ref"):
            voice_switch.switch(conn, "recording", True, k["email"], ref)
    assert settings.config(conn, "voice.recording_enabled", False) is False
    assert _logged(conn, k["staff"]) == []
    voice_switch.switch(conn, "recording", True, k["email"], "Sarvam email 2026-11-10")
    assert settings.config(conn, "voice.recording_enabled", False) is True
    assert _logged(conn, k["staff"]) == ["voice.recording_enabled on, retention-ref: Sarvam email 2026-11-10"]
    voice_switch.switch(conn, "recording", False, k["email"])  # off needs no reference
    assert settings.config(conn, "voice.recording_enabled", True) is False


def test_someone_not_on_the_staff_tables_changes_nothing(conn):
    before = settings.config(conn, "voice.screens_enabled", False)
    with pytest.raises(ValueError, match="--by must be the email you sign in with"):
        voice_switch.switch(conn, "screens", not before, "nobody@example.test")
    assert settings.config(conn, "voice.screens_enabled", False) is before


def test_the_command_turns_a_switch_and_prints_no_email(conn, monkeypatch):
    monkeypatch.setattr(db, "connect", lambda *a, **k: _held(conn))
    k = a_k2_class(conn)
    out = CliRunner().invoke(app, ["read", "voice", "switch", "screens", "on", "--by", k["email"]])
    assert out.exit_code == 0, out.output
    assert "voice.screens_enabled: on" in out.output and k["email"] not in out.output
    refused = CliRunner().invoke(app, ["read", "voice", "switch", "recording", "on", "--by", k["email"]])
    assert refused.exit_code != 0 and "retention-ref" in refused.output
    wrong = CliRunner().invoke(app, ["read", "voice", "switch", "lights", "on", "--by", k["email"]])
    assert wrong.exit_code != 0
