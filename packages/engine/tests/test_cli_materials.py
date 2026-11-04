"""`engine reminders --due` (task M1-10): it counts what is due and sends nothing, it does nothing while the educator's
screens are off, and the line the box's timer is given runs a command the engine has."""

import os
import re

import pytest
from typer.testing import CliRunner

from engine.cli import app
from engine.core import db

NOTE = db.REPO_ROOT / "docs" / "notes" / "m1-10-materials-list.md"


def test_every_line_the_box_timer_is_given_runs_a_command_the_engine_has():
    lines = re.findall(r"docker exec deploy-engine-1 engine ([a-z -]+?) >>", NOTE.read_text())
    assert lines == ["reminders --due"]
    for command in lines:
        out = CliRunner().invoke(app, [*command.split(), "--help"])
        assert out.exit_code == 0, (command, out.output)


def test_it_does_nothing_without_the_flag_it_is_asked_to_run():
    assert CliRunner().invoke(app, ["reminders"]).exit_code != 0


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_while_the_screens_are_off_it_says_so_and_counts_nothing(monkeypatch):
    monkeypatch.setattr("engine.w2_print.materials_list.enabled", lambda conn: False)
    out = CliRunner().invoke(app, ["reminders", "--due"])
    assert out.exit_code == 0, out.output
    assert "educator.timetable_enabled is off" in out.output


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_while_they_are_on_it_prints_the_counts(monkeypatch):
    monkeypatch.setattr("engine.w2_print.materials_list.enabled", lambda conn: True)
    out = CliRunner().invoke(app, ["reminders", "--due"])
    assert out.exit_code == 0, out.output
    assert re.search(r"due: \d+ reminders for \d+ lists \(educator \d+, team \d+\)", out.output), out.output


@pytest.mark.parametrize("command", ["materials month", "materials cost"])
def test_the_materials_commands_exist(command):
    out = CliRunner().invoke(app, [*command.split(), "--help"])
    assert out.exit_code == 0, out.output
