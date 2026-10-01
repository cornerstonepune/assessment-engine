"""The gates CI holds every change to (goals/p1-the-gates-hold.yaml).

The code review of 2026-09-30 found CI running no web lint and no coverage floor, nothing holding a frozen
number to the commit before it, and 11 goal criteria that could never pass. These read the files that run CI
and the goals, the way test_deploy.py reads the deploy.
"""

import tomllib

import yaml

from engine.checks import goal
from engine.core import db

CI = yaml.safe_load((db.REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
PYPROJECT = tomllib.loads((db.REPO_ROOT / "packages" / "engine" / "pyproject.toml").read_text())


def _runs(job):
    return [s.get("run", "") for s in CI["jobs"][job]["steps"]]


def test_ci_lints_the_website_with_no_warning_allowed():
    assert [r for r in _runs("web") if r.startswith("npx eslint") and "--max-warnings 0" in r], (
        "CI does not lint the website, or lets a warning through"
    )


def test_ci_holds_the_engine_to_its_coverage_floor():
    floor = PYPROJECT["tool"]["coverage"]["report"]["fail_under"]
    assert floor >= 79, "the floor sits below the 79% the engine measured when it was set"
    assert [r for r in _runs("engine") if "pytest" in r and "--cov=engine" in r], "CI measures no coverage"


def test_ci_refuses_a_change_that_loosens_a_baseline():
    steps = CI["jobs"]["engine"]["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout.get("with", {}).get("fetch-depth") == 0, "the job cannot see the commit it compares with"
    (ratchet,) = [r for r in _runs("engine") if r.startswith("uv run engine ratchet --base")]
    assert "pull_request.base.sha" in ratchet and "github.event.before" in ratchet, ratchet


def test_a_goal_criterion_that_runs_pytest_quietly_can_pass():
    """`pytest -q` and the pyproject's own `-q` made `-qq`, which never prints "passed": 11 goal criteria could
    never pass, and no one ran them (code review, 2026-09-30)."""
    assert "-q" not in PYPROJECT["tool"]["pytest"]["ini_options"].get("addopts", "").split()
    passed, out = goal.run_criterion(
        {
            "run": "cd packages/engine && .venv/bin/python -m pytest -q -p no:cacheprovider"
            " tests/test_layout.py::test_every_step_says_whether_it_works_for_any_subject",
            "expect": "passed",
        }
    )
    assert passed, out
