"""Which of CI's jobs a change needs (`bin/ci-plan`, goals/ci-fast-paths.yaml).

On 2026-11-05 a docs-only pull request took about two hours to clear: every pull request started 19 jobs, GitHub ran 20 at
once, and 13 open pull requests queued behind each other (docs/notes/ci-fast-paths.md). `bin/ci-plan` decides, from the
changed files alone, which jobs a pull request starts; `.github/workflows/ci.yml` runs only those. These read both, so the
rules are held without GitHub: the script's decision for sample changed-file lists, and the workflow that obeys it.
The rule that matters most is the default: a change the script cannot place runs everything.
"""

import importlib.machinery
import importlib.util
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[3]
_loader = importlib.machinery.SourceFileLoader("ci_plan", str(REPO / "bin" / "ci-plan"))
_spec = importlib.util.spec_from_loader("ci_plan", _loader)
assert _spec
plan = importlib.util.module_from_spec(_spec)
_loader.exec_module(plan)

CI = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
# GitHub's YAML 1.1 reads the key `on` as true
TRIGGERS = CI.get("on") or CI[True]

FAST = {"engine": False, "web": False, "browser": False, "web_reads": False}
FULL = {"engine": True, "web": True, "browser": True, "web_reads": False}
WEB_ONLY = {"engine": False, "web": True, "browser": True, "web_reads": True}
DOCS = [
    "docs/notes/ci-fast-paths.md",
    "HANDOFF.md",
    "docs/adr/0099-x.md",
    "docs/sources/cornerstone-blueprint-v2.html",
]
WEB = [
    "apps/web/app/page.tsx",
    "apps/web/lib/db.ts",
    "apps/web/tests/today.spec.ts",
    "apps/web/package-lock.json",
]
SENSITIVE = [
    "supabase/migrations/20261105000000_x.sql",
    "supabase/seed/levels.json",
    "packages/engine/engine/checks/rules.json",
    "rules.json",
    "packages/engine/engine/assess/graph.py",
    "packages/engine/tests/test_x.py",
    "workflows.json",
    "bin/check",
    ".github/workflows/ci.yml",
]


def jobs(event="pull_request", draft=False, files=()):
    return {k: v for k, v in plan.decide(event, draft, list(files)).items() if k in FAST}


# --- the five rules, one test each -----------------------------------------------------------------------------------


@pytest.mark.parametrize("files", [WEB, DOCS, WEB + DOCS, ["goals/x.yaml"]])
def test_1_a_draft_runs_only_the_fast_checks_and_the_website_when_it_changed(files):
    got = jobs(draft=True, files=files)
    assert not (got["engine"] or got["browser"] or got["web_reads"]), got
    assert got["web"] == (files != DOCS), got


def test_1_a_pull_request_marked_ready_runs_the_full_suite_and_so_does_each_push_after():
    # the same files, a draft and then ready: the second is the `ready_for_review` run, and a later `synchronize` decides alike
    files = ["goals/x.yaml"]
    assert jobs(draft=True, files=files) == FAST | {"web": True}
    assert jobs(draft=False, files=files) == FULL
    assert "ready_for_review" in TRIGGERS["pull_request"]["types"]
    assert {"opened", "synchronize", "reopened"} <= set(TRIGGERS["pull_request"]["types"])


@pytest.mark.parametrize("files", [DOCS[:1], DOCS, ["STATE.md", "docs/athena/learnings.md"]])
def test_2_a_pull_request_of_docs_alone_skips_the_engine_and_the_browser(files):
    assert jobs(files=files) == FAST


def test_2_the_docs_list_is_explicit_and_holds_nothing_a_test_reads():
    """A docs-only change skips the engine's tests, so nothing on the list may be a file one of them reads."""
    assert plan.reads_of(plan.DOCS_PREFIXES + plan.DOCS_FILES) == []
    # docs/adr is read by `engine promises`, which bin/check runs on every pull request, draft or not
    assert "tests/test_promises.py" in (REPO / "bin" / "check").read_text()
    # the files under a listed folder that a browser spec reads is carved out, so a change to it runs the suite
    for read in plan.READ_BY_TESTS:
        assert jobs(files=[read]) == FULL, read
        assert any(read.startswith(p) for p in plan.DOCS_PREFIXES), (
            f"{read} is on no list; delete the carve-out"
        )
    # and these are read by tests, so they are not on it
    for read in ("BUILD-ORDER.md", "DECISIONS-LOG.md", "docs/design/multiplication-division-cases.json",
                 "docs/sources/assessment-workflow-v1.md", "docs/crosswalk/sources.json", "docs/spine/plan.json",
                 "docs/ux-rules.md", "docs/md-taxonomy.md"):  # fmt: skip
        assert jobs(files=[read]) == FULL, read


@pytest.mark.parametrize("files", [WEB, WEB[:1], WEB + DOCS])
def test_3_a_pull_request_of_the_website_alone_skips_the_engines_shards(files):
    assert jobs(files=files) == WEB_ONLY


@pytest.mark.parametrize("other", ["packages/engine/engine/cli.py", "supabase/migrations/1.sql", "supabase/seed/a.json",
                                   "workflows.json", "bin/check", ".github/workflows/ci.yml", "goals/a.yaml",
                                   "n8n/workflows/a.json", "package.json"])  # fmt: skip
def test_3_the_website_with_anything_else_runs_everything(other):
    assert jobs(files=[*WEB, other]) == FULL
    assert jobs(files=[other, *WEB, *DOCS]) == FULL


def test_3_the_engine_tests_that_read_the_website_still_run_when_only_the_website_changed():
    """27 of the engine's test files read apps/web (the UX rules, the auth gate, the school's words…) and 87 of their tests need
    the database. Skipping every shard would let a website change break them unseen, so one runner runs just those files."""
    chosen = plan.web_tests(REPO / "packages" / "engine" / "tests")
    assert {"tests/test_ux_rules.py", "tests/test_web_gate.py", "tests/test_school_words.py"} <= set(chosen)
    for path in (REPO / "packages" / "engine" / "tests").rglob("test_*.py"):
        if "apps/web" in path.read_text():
            assert path.relative_to(REPO / "packages" / "engine").as_posix() in chosen, path


@pytest.mark.parametrize("sensitive", SENSITIVE)
def test_5_what_the_engine_the_database_or_the_gates_are_made_of_runs_everything_once_ready(sensitive):
    """Even beside a docs file or a website file."""
    for files in ([sensitive], [sensitive, *DOCS], [*WEB, sensitive]):
        assert jobs(files=files) == FULL, (sensitive, files)


@pytest.mark.parametrize("sensitive", SENSITIVE)
def test_5_a_draft_of_them_waits_for_ready_like_any_other_draft(sensitive):
    """All 10 drafts open on 2026-11-05 touched packages/engine or bin: if a draft ran everything for those, no draft would
    save a job. The suite they skip runs when each is marked ready (above), which is when it can be merged."""
    assert jobs(draft=True, files=[sensitive]) == FAST | {"web": True}
    assert jobs(draft=True, files=[sensitive, *DOCS]) == FAST | {"web": True}


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch", "something_new"])
@pytest.mark.parametrize("files", [DOCS, WEB, []])
def test_4_main_the_nightly_run_and_a_run_by_hand_run_everything_whatever_changed(event, files):
    assert jobs(event=event, files=files) == FULL
    assert jobs(event=event, draft=True, files=files) == FULL


def test_4_main_cancels_a_superseded_run_but_never_skips_one_and_the_suite_runs_nightly():
    assert CI["concurrency"]["cancel-in-progress"] is True
    assert "github.ref" in CI["concurrency"]["group"]
    assert TRIGGERS["push"]["branches"] == ["main"]
    (nightly,) = TRIGGERS["schedule"]
    assert re.fullmatch(r"\d+ \d+ \* \* \*", nightly["cron"]), "once a day"
    # the plan job reads the event; nothing keys a job on the branch name, so a push to main has no way to skip
    assert "plan" in CI["jobs"] and "needs.plan.outputs" in str(CI["jobs"]["engine-shard"]["if"])


# --- the default: what the script cannot place runs everything -----------------------------------------------------------


@pytest.mark.parametrize(
    "files",
    [
        [],
        [""],
        ["   "],
        ["apps/web/../../supabase/migrations/1.sql"],
        ["apps/webx/a.ts"],
        ["apps/web"],
        ["/apps/web/a.ts"],
        ['"apps/web/caf\\303\\251.ts"'],
        ["apps/web/./a.ts", "docs/notes/../../bin/check"],
        ["Apps/web/a.ts"],
        ["docs/notes"],
        ["docs/notesx/a.md"],
        ["docs/notes/a.md", "somewhere/new.txt"],
    ],
)
def test_a_change_the_script_cannot_place_runs_everything(files):
    assert jobs(files=files) == FULL, files


def test_nothing_is_on_two_lists():
    for p in plan.DOCS_PREFIXES + plan.DOCS_FILES:
        assert not plan.forces_full(p), p
        assert not p.startswith(plan.WEB_PREFIX), p
    assert plan.WEB_PREFIX == "apps/web/"


def test_the_output_is_lines_the_workflow_can_append_to_github_output():
    out = plan.render(plan.decide("pull_request", True, DOCS))
    for line in out.splitlines():
        key, _, value = line.partition("=")
        assert key in {*FAST, "reason"} and "\n" not in value
        assert key == "reason" or value in {"true", "false"}


# --- the workflow obeys the script ---------------------------------------------------------------------------------------


def _if(job):
    return str(CI["jobs"][job].get("if", ""))


def _runs(job):
    return "\n".join(s.get("run", "") for s in CI["jobs"][job]["steps"])


GATES = {  # job -> the plan output that starts it
    "engine-shard": "engine",
    "web": "web",
    "browser-shard": "browser",
    "engine-web-reads": "web_reads",
}


def started(outputs):
    """The jobs the workflow starts for a plan's outputs, reading each job's own `if`."""
    result = {"engine-checks", "plan"}
    for job, key in GATES.items():
        if f"needs.plan.outputs.{key} == 'true'" in _if(job) and outputs[key]:
            result.add(job)
    return result


def test_each_job_starts_on_exactly_its_own_output():
    for job, key in GATES.items():
        assert _if(job) == f"needs.plan.outputs.{key} == 'true'", job
        assert "plan" in CI["jobs"][job]["needs"], job
    assert "needs" not in CI["jobs"]["engine-checks"], "the fast checks wait for nothing and never skip"
    assert "if" not in CI["jobs"]["engine-checks"]


@pytest.mark.parametrize(
    ("files", "draft", "expected"),
    [
        (DOCS, False, {"engine-checks", "plan"}),
        (DOCS, True, {"engine-checks", "plan"}),
        (WEB, True, {"engine-checks", "plan", "web"}),
        (WEB, False, {"engine-checks", "plan", "web", "browser-shard", "engine-web-reads"}),
        (["bin/check"], True, {"engine-checks", "plan", "web"}),
        (["bin/check"], False, {"engine-checks", "plan", "web", "browser-shard", "engine-shard"}),
        (
            ["packages/engine/engine/cli.py", *DOCS],
            False,
            {"engine-checks", "plan", "web", "browser-shard", "engine-shard"},
        ),
    ],
)
def test_the_workflow_starts_only_the_jobs_the_plan_names(files, draft, expected):
    assert started(plan.decide("pull_request", draft, files)) == expected


def test_a_skipped_job_still_reports_the_names_the_gates_wait_on():
    """`engine` and `browser` run whatever the plan said, and say success when their shards were skipped on purpose; a plan
    that failed is a failure (the shards would be skipped for that too, which must not read as a pass)."""
    for name, shards in (("engine", "engine-shard"), ("browser", "browser-shard")):
        job = CI["jobs"][name]
        assert job["if"] == "always()", name
        assert {"plan", shards} <= set(job["needs"])
        last = job["steps"][-1]
        assert last["if"] == "always()" and "needs.plan.result" in last["run"], name
        assert "success" in last["run"]
        # with the checkout skipped there is no packages/engine folder, so a step that runs there cannot even start (#412, 2026-11-05)
        assert "working-directory" in last or "defaults" not in job, name
    assert {"engine-checks"} <= set(CI["jobs"]["engine"]["needs"])
    for job in ("engine-checks", "engine", "web", "browser"):
        assert job in CI["jobs"], f"the required check '{job}' must keep its name"
    assert CI["name"] == "ci"
    assert CI["jobs"]["engine-shard"]["name"] == "engine shard ${{ matrix.shard }}"
    assert CI["jobs"]["browser-shard"]["name"] == "browser shard ${{ matrix.shard }}"


def test_the_plan_job_falls_back_to_everything_when_it_cannot_decide():
    steps = CI["jobs"]["plan"]["steps"]
    assert steps[0]["uses"].startswith("actions/checkout") and steps[0]["with"]["fetch-depth"] == 0
    run = _runs("plan")
    assert "bin/ci-plan" in run and "--no-renames" in run, (
        "a file moved out of bin/ must show as a change to bin/"
    )
    assert "|| " in run and "engine=true" in run and "web=true" in run and "browser=true" in run, run
    assert "pull_request.draft" in str(steps) and "github.event_name" in str(steps)
    assert set(CI["jobs"]["plan"]["outputs"]) == {*FAST, "reason"}
    assert all(
        CI["jobs"]["plan"]["outputs"][k] == f"${{{{ steps.plan.outputs.{k} }}}}"
        for k in CI["jobs"]["plan"]["outputs"]
    )


def test_the_draft_runs_the_layout_map_and_the_other_checks_that_need_no_database():
    assert "../../bin/check" in _runs("engine-checks")
