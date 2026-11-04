"""`engine read voice retention` (engine/w3_read/cli_voice.py): with no retention decided (O-14), nothing is deleted."""

import os

import pytest
from typer.testing import CliRunner

from engine.cli import app

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def test_with_no_retention_decided_every_recording_is_kept():
    out = CliRunner().invoke(app, ["read", "voice", "retention"])
    assert out.exit_code == 0, out.output
    assert "not decided (O-14); nothing deleted" in out.output
