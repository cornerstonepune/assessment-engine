"""No promise without a command, and a done-report the machine writes (goals/promises-kept.yaml).

Nimish, 2026-09-22: "Despite putting all of this in the handoffs and Claude MDs, you keep on forgetting …
Make it a hook or a syntax or something that you check or you give it to me." These hold the rules in
code, and hold the hooks that run them.
"""

import json

import yaml

from engine.checks import done, promises
from engine.core import db


def test_every_goal_line_is_a_command_or_one_of_nimishs_sentences_with_its_test():
    assert promises.problems() == []


def test_a_line_that_looks_like_a_check_but_runs_nothing_is_refused(tmp_path):
    """The shape that hid the unbuilt loop for three days: `correction_must_change_a_later_read: true`."""
    g = tmp_path / "a-new-goal.yaml"
    g.write_text(yaml.safe_dump({
        "name": "a-new-goal", "goal": "x",
        "loop": {"correction_must_change_a_later_read": True},
        "criteria": [{"name": "no command", "expect": "ok"}],
        "says": [{"words": "it learns", "proved_by": "packages/engine/tests/test_promises.py::test_that_is_not_there"}],
    }))  # fmt: skip
    found = promises.goal_problems(g)
    assert any("`loop` is not a command" in p for p in found)
    assert any("has no command to run" in p for p in found)
    assert any("not a test that exists" in p for p in found)
    g.write_text(yaml.safe_dump({"name": "a-new-goal", "goal": "x", "criteria": []}))
    assert any("says none of Nimish's words" in p for p in promises.goal_problems(g))


def test_a_proof_is_a_test_that_exists_in_python_or_on_the_website():
    assert promises.test_exists(
        "packages/engine/tests/test_promises.py::test_a_proof_is_a_test_that_exists_in_python_or_on_the_website"
    )
    assert promises.test_exists("apps/web/tests/workflows.spec.ts::the map fits a phone")
    assert not promises.test_exists("apps/web/tests/workflows.spec.ts::a test nobody wrote")
    assert not promises.test_exists("packages/engine/tests/test_promises.py")  # no name, no proof


def test_a_decision_record_from_0032_names_the_goal_that_proves_it(tmp_path, monkeypatch):
    adr = tmp_path / "0033-something.md"
    adr.write_text("# 0033\n\nStatus: accepted\n")
    assert promises.adr_problems(adr) == [
        "0033-something.md: names no goal (`Goal: goals/x.yaml`, or `Goal: none — why`)"
    ]
    adr.write_text("# 0033\n\nGoal: none — a naming decision, nothing to run\n")
    assert promises.adr_problems(adr) == []
    old = tmp_path / "0019-older.md"
    old.write_text("# 0019\n")
    assert promises.adr_problems(old) == []  # written before the rule


def test_the_done_report_names_each_sentence_its_test_and_what_is_not_live(tmp_path, monkeypatch):
    goals_dir = tmp_path / "goals"
    goals_dir.mkdir()
    (goals_dir / "x.yaml").write_text(yaml.safe_dump({
        "name": "x", "goal": "It learns.", "criteria": [],
        "says": [{"words": "it learns", "proved_by": "a::b"}, {"words": "it is fast", "proved_by": "c::d"}],
        "manual": ["Nimish runs engine read profile after a batch"],
    }))  # fmt: skip
    monkeypatch.setattr(done.goals, "GOALS", goals_dir)
    lines, ok = done.report(
        "x", run=lambda p: (p == "a::b", "1 passed"), live=lambda: ["2 migration(s) not on the live database"]
    )
    text = "\n".join(lines)
    assert not ok
    assert 'PROVED  "it learns"' in text and 'NOT PROVED  "it is fast"' in text
    assert "Nimish runs engine read profile after a batch" in text
    assert "2 migration(s) not on the live database" in text and text.endswith("NOT DONE")
    lines, ok = done.report("x", run=lambda p: (True, "1 passed"), live=lambda: [])
    assert ok and lines[-1] == "DONE" and "nothing: all of it is live" in "\n".join(lines)


def test_the_hooks_run_the_checks_before_a_commit_and_before_claude_says_it_is_finished():
    """The checks run whether or not anyone remembers them: git before every commit, and Claude Code
    before it may end a turn in this repository."""
    hook = db.REPO_ROOT / ".githooks" / "pre-commit"
    assert hook.exists() and hook.stat().st_mode & 0o111, "the git hook is missing or not executable"
    settings = json.loads((db.REPO_ROOT / ".claude" / "settings.json").read_text())
    stop = " ".join(h["command"] for group in settings["hooks"]["Stop"] for h in group["hooks"])
    for text in (hook.read_text(), stop):
        assert "bin/check" in text
    check = (db.REPO_ROOT / "bin" / "check").read_text()
    assert "test_layout.py" in check and "test_promises.py" in check
