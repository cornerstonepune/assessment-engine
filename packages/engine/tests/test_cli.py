"""The command line, which is everything a person actually types.

It sat at 0% coverage while the logic behind it was at 90%+, and all three test failures in the
session of 2026-09-20 were in exactly that blind spot: a command's arguments changed and nothing
noticed until a person ran it. These tests are cheap on purpose — they check that every command
exists, takes the arguments the documentation and the goal files claim, and fails loudly rather
than silently when given something wrong. They do not re-test the logic underneath.
"""

import os
import re

import pytest
from typer.testing import CliRunner

from engine.cli import app

runner = CliRunner()


def run(*args):
    """The command, with its help text as plain words. Typer draws help with rich, and in CI rich
    styles each dash of an option on its own — "--paper" arrives as escape codes around "-" and
    "-paper" — so a check that passed on a laptop failed on every run in GitHub."""
    result = runner.invoke(app, list(args), env={"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "200"})
    result.output_plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    return result


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
    ("report", "parents", "--help"),  # the write-reports workflow runs it on the server
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
    out = run("legacy", "import", "--help").output_plain
    for flag in ("--paper", "--child", "--section", "--pages", "--mask", "--again"):
        assert flag in out, f"{flag} is documented but the command no longer takes it"


def test_read_eval_offers_both_readers_so_the_comparison_stays_one_command():
    """ADR 0019 chose Textract over a vision model on a measurement. That choice is only re-checkable
    while one command can still score either."""
    out = run("read", "eval", "--help").output_plain
    assert "--reader" in out
    assert "--runs" in out


def test_a_staff_password_is_hashed_exactly_as_the_web_app_checks_it():
    """The web app verifies with node's `scryptSync`. The expected value below is node's own output
    for this fixture (`node -e 'scryptSync("fixture-not-a-real-password", "0011…eeff", 64)'`), so a
    hash this command writes is one the sign-in form will accept — the only property that matters,
    and one no Python-only test could show."""
    from engine.cli import staff_hash

    assert staff_hash("fixture-not-a-real-password", "00112233445566778899aabbccddeeff") == (
        "scrypt$00112233445566778899aabbccddeeff$"
        "92cad9873f497b8ec938f72a226440454cd71d3477e50efc413b1521d5c320838873d38d868e41b58e3e3c897782"
        "bce759d39894350757661630bb4d5804b25c"
    )


def test_a_next_paper_prints_only_with_the_person_who_approves_it_named():
    """`week focus --make` is an approval (BUILD-ORDER, U2): without --by it refuses before touching the database."""
    r = run("week", "focus", "G2", "Asha", "2026-W39", "--make")
    assert r.exit_code != 0 and "--by" in r.output_plain


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
@pytest.mark.parametrize("purpose", ["mistake_guess", "story_shape", "week_skills"])
def test_a_jev_eval_jev_cannot_answer_fails_and_says_why(purpose, monkeypatch):
    """With no key, `engine eval week_skills` said "the exact skill sets on 0/24 notes" and exited 0, and so did
    story_shape ("left for a person 65"): a missing key looked like a poor score. It is an error, named."""
    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    r = run("eval", purpose)
    assert r.exit_code == 1, r.output_plain
    assert "not answered" in r.output_plain and "TYPESAFE_API_KEY" in r.output_plain


def test_read_report_says_each_kinds_standing_as_the_one_rule_gives_it(monkeypatch):
    """`engine read report` prints each kind's window and the right checks it still needs as the database's one rule
    gives them (`kind_trust`, ADR 0060) — never a 50 or a 95% of its own."""
    from contextlib import nullcontext

    from engine.core import db
    from engine.w3_read import profiles

    kind = {"checked": 9, "right": 7, "silently_wrong": 1, "gave_up": 1, "window_n": 8, "window_right": 7}
    report = {
        "total": {
            "checked": 18,
            "stood_behind": 16,
            "right": 14,
            "silently_wrong": 2,
            "gave_up": 2,
            "guess_right": 0,
        },
        "kinds": {
            "bare_sum": {**kind, "trusted": True, "to_trust": 0},
            "column_grid": {**kind, "trusted": False, "to_trust": 4},
        },
        "window": 8,
        "batches": [],
        "children": [],
    }
    monkeypatch.setattr(db, "connect", lambda: nullcontext(None))
    monkeypatch.setattr(profiles, "report", lambda conn: report)
    result = run("read", "report")
    assert result.exit_code == 0, result.output
    lines = result.output_plain.splitlines()
    assert any("last 8" in line for line in lines)
    assert [line.split()[-1] for line in lines if line.strip().startswith("bare_sum")] == ["trusted"]
    assert any(
        line.strip().startswith("column_grid")
        and line.endswith("not trusted (7 of 8; 4 more right checks to trust)")
        for line in lines
    )
