"""The voice commands (engine/w3_read/cli_voice.py): what the box's timer runs exists, and with no retention decided
(O-14) nothing is deleted."""

import os
import re

import pytest
from typer.testing import CliRunner

from engine.cli import app
from engine.core import db

NOTE = db.REPO_ROOT / "docs" / "notes" / "m1-01-voice-intake.md"


def test_every_line_the_box_timer_is_given_runs_a_command_the_engine_has():
    lines = re.findall(r"docker exec deploy-engine-1 engine ([a-z ]+?) >>", NOTE.read_text())
    assert lines == ["read voice expire", "read voice retention"]
    for command in lines:
        out = CliRunner().invoke(app, [*command.split(), "--help"])
        assert out.exit_code == 0, (command, out.output)


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_with_no_retention_decided_every_recording_is_kept():
    out = CliRunner().invoke(app, ["read", "voice", "retention"])
    assert out.exit_code == 0, out.output
    assert "not decided (O-14); nothing deleted" in out.output
