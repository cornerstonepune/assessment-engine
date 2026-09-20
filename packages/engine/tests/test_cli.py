"""The command line, which is everything a person actually types.

It sat at 0% coverage while the logic behind it was at 90%+, and all three test failures in the
session of 2026-09-20 were in exactly that blind spot: a command's arguments changed and nothing
noticed until a person ran it. These tests are cheap on purpose — they check that every command
exists, takes the arguments the documentation and the goal files claim, and fails loudly rather
than silently when given something wrong. They do not re-test the logic underneath.
"""

import pytest
from typer.testing import CliRunner

from engine.cli import app

runner = CliRunner()


def run(*args):
    return runner.invoke(app, list(args))


# Every command a person or a goal file is told to run. A name changing without this list changing
# is the failure these catch: `goals/*.yaml` and `HANDOFF.md` both hand out commands as text, and
# nothing else checks that the text still resolves.
COMMANDS = [
    (),
    ("bank",),
    ("week",),
    ("legacy",),
    ("read",),
    ("audit", "--help"),
    ("goal", "--help"),
    ("load", "--help"),
    ("read", "map", "--help"),
    ("read", "eval", "--help"),
    ("read", "stability", "--help"),
    ("legacy", "import", "--help"),
    ("legacy", "paper", "--help"),
]


@pytest.mark.parametrize("args", COMMANDS, ids=lambda a: " ".join(a) or "(root)")
def test_every_command_resolves_and_describes_itself(args):
    r = run(*args)
    assert r.exit_code in (0, 2), r.output  # 2 is typer's "here is the help" for a group
    assert "No such command" not in r.output
    assert "Usage" in r.output or "Commands" in r.output


def test_an_unknown_command_fails_loudly():
    r = run("definitely-not-a-command")
    assert r.exit_code != 0
    assert "No such command" in r.output


def test_goal_names_the_goals_it_has_when_asked_for_none():
    """`engine goal` with no argument lists them — the goal files are the definition of done, and a
    session that cannot find them cannot say whether anything is finished."""
    r = run("goal")
    assert r.exit_code == 0
    for name in ("w1-build-the-bank", "w2-assemble-and-print", "w3-read-and-graph"):
        assert name in r.output


def test_goal_refuses_a_name_it_does_not_have_and_says_which_it_does():
    r = run("goal", "w9-not-a-goal")
    assert r.exit_code != 0
    assert "w1-build-the-bank" in r.output or "no goal" in r.output.lower()


def test_read_map_needs_a_paper_to_read():
    r = run("read", "map")
    assert r.exit_code != 0
    assert "Missing argument" in r.output or "Usage" in r.output


def test_legacy_import_names_every_option_the_handoff_tells_people_to_pass():
    """`--again` exists because a corrected paper leaves earlier readings short; `--mask` because a
    name band must not reach a model (rule 6). Both are handed out as instructions in HANDOFF.md."""
    out = run("legacy", "import", "--help").output
    for flag in ("--paper", "--child", "--section", "--pages", "--mask", "--again"):
        assert flag in out, f"{flag} is documented but the command no longer takes it"


def test_read_eval_offers_both_readers_so_the_comparison_stays_one_command():
    """ADR 0019 chose Textract over a vision model on a measurement. That choice is only re-checkable
    while one command can still score either."""
    out = run("read", "eval", "--help").output
    assert "--reader" in out
    assert "--runs" in out
