"""The gates CI holds every change to (goals/p1-the-gates-hold.yaml).

The code review of 2026-09-30 found CI running no web lint and no coverage floor, nothing holding a frozen
number to the commit before it, and 11 goal criteria that could never pass. These read the files that run CI
and the goals, the way test_deploy.py reads the deploy.
"""

import re
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
    # the shards measure, and the one engine job combines them and applies the floor to the whole suite
    # (goals/ci-engine-shards.yaml): no shard's part can pass for the whole, and no run lowers the floor
    assert [r for r in _runs("engine-shard") if "pytest" in r and "--cov=engine" in r], (
        "CI measures no coverage"
    )
    (report,) = [r for r in _runs("engine") if "coverage report" in r]
    assert "coverage combine" in report and "--fail-under" not in report, report


def test_ci_refuses_a_change_that_loosens_a_baseline():
    steps = CI["jobs"]["engine-checks"]["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout.get("with", {}).get("fetch-depth") == 0, "the job cannot see the commit it compares with"
    (ratchet,) = [r for r in _runs("engine-checks") if r.startswith("uv run engine ratchet --base")]
    assert "engine-checks" in CI["jobs"]["engine"]["needs"], "the engine result does not wait on the ratchet"
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


def test_ci_runs_every_browser_test_on_a_fresh_database_with_none_skipped():
    """29 browser spec files ran on a laptop against a copy of live, never in CI, and some leaned on live's classes
    (code review, 2026-09-30; goals/p1-browser-tests-in-ci.yaml)."""
    runs = _runs("browser-shard")
    assert [r for r in runs if 'bin/testdb fresh "$DATABASE_URL"' in r], (
        "the browser job does not build its own database"
    )
    (suite,) = [r for r in runs if r.startswith("npx playwright test")]
    assert "--grep" not in suite and "json" in suite, (
        f"not the whole suite, or no report to count skips in: {suite}"
    )
    assert [r for r in runs if "results.json" in r and "skipped" in r and "process.exit(1)" in r], (
        "a skipped test does not fail the job"
    )


def test_a_browser_test_that_fails_is_run_once_more_in_ci_and_flaky_ones_are_listed():
    """Twice in one day main's browser job failed once for a reason that was not the product's, and a person re-ran the
    whole job while the release waited (Nimish, 2026-10-23; docs/adr/0094). A retry is once, in CI only; a test that
    then passes is listed, not hidden; one that fails twice, or skips, still fails the job."""
    config = (db.REPO_ROOT / "apps" / "web" / "playwright.config.ts").read_text()
    assert "retries: retriesFor(process.env.CI)" in config
    assert "(ci ? 1 : 0)" in (db.REPO_ROOT / "apps" / "web" / "tests" / "retries.ts").read_text()
    runs = _runs("browser-shard")
    assert "bin/ci-flaky-summary apps/web/results.json" in runs, "the flaky tests are not listed in the job"
    (check,) = [r for r in runs if "results.json" in r and "process.exit(1)" in r]
    assert "s.skipped || s.unexpected" in check and "flaky" not in check, check


def test_no_browser_test_can_skip_itself():
    """A test that skips itself when the database lacks its rows proves nothing on a database that lacks them; it
    builds them instead (apps/web/tests/rows.ts)."""
    specs = sorted((db.REPO_ROOT / "apps" / "web" / "tests").glob("*.ts"))
    assert len(specs) > 20, "found too few browser tests; the search reads nothing"
    found = [
        f"{p.name}:{n}"
        for p in specs
        for n, line in enumerate(p.read_text().splitlines(), 1)
        if re.search(r"\b(test|describe)\.(skip|fixme|only)\(", line)
    ]
    assert found == []


def test_ci_runs_every_browser_test_as_the_services_own_roles():
    """A role's grants are wide enough only if its service works as it: CI gives both roles a password for the run and
    starts the website and the engine as them, while each spec writes its own rows as the owner
    (goals/p1-the-roles-hold.yaml)."""
    runs = _runs("browser-shard")
    built = next(i for i, r in enumerate(runs) if "bin/testdb fresh" in r)
    (given,) = [i for i, r in enumerate(runs) if "alter role app_web password" in r]
    (suite,) = [i for i, r in enumerate(runs) if r.startswith("npx playwright test")]
    assert built < given < suite and "alter role app_engine password" in runs[given]
    env = CI["jobs"]["browser-shard"]["steps"][suite].get("env", {})
    assert env.get("TEST_WEB_DATABASE_URL", "").startswith("postgresql://app_web:"), env
    assert env.get("TEST_ENGINE_DATABASE_URL", "").startswith("postgresql://app_engine:"), env
    config = (db.REPO_ROOT / "apps" / "web" / "playwright.config.ts").read_text()
    assert "DATABASE_URL: AS_ENGINE" in config and "DATABASE_URL: AS_WEB" in config
