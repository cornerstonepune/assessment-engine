"""The fixed commands the `timetable run` workflow runs on the server (.github/timetable/command.py).

The K2 timetable reaches the live database by a logged command on the server, not by pasting SQL through a connector.
Same pattern as the curriculum run: a manual choice of two FIXED runs (a dry run that writes nothing, and the apply),
no free text reaches a shell, the person is looked up in the repository variable CURRICULUM_STAFF, the files are the
committed exports, and the load prints its rows before and after.
"""

import importlib.util
import json
import re

import pytest
import yaml

from engine.core import db

SCRIPT = db.REPO_ROOT / ".github" / "timetable" / "command.py"
spec = importlib.util.spec_from_file_location("timetable_command", SCRIPT)
cmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmd)
WORKFLOW = db.REPO_ROOT / ".github" / "workflows" / "timetable-run.yml"
STAFF = json.dumps({"someone": "someone@school.invalid"})


def lines(run, actor="someone", staff=STAFF):
    return cmd.commands(run, actor, staff)


def test_there_are_two_runs_a_dry_one_that_writes_nothing_and_the_apply():
    assert list(cmd.RUNS) == ["dry", "apply"]
    assert cmd.RUNS["dry"]["writes"] is False and cmd.RUNS["apply"]["writes"] is True
    assert all("--apply" not in c for c in lines("dry", actor="", staff="")), (
        "a dry run needs nobody and writes nothing"
    )
    assert all("--apply" in c for c in lines("apply"))


def test_the_apply_runs_twice_so_the_log_shows_the_second_adding_nothing():
    assert len(lines("apply")) == 2 and lines("apply")[0] == lines("apply")[1]


def test_every_run_loads_the_committed_exports_for_the_k2_class_with_the_undecided_day():
    for run in cmd.RUNS:
        for c in lines(run):
            assert c.startswith("engine timetable load ")
            for name in ("frame.csv", "frame_spans.json", "planner.csv", "calendar.csv"):
                path = re.search(rf"/app/(supabase/seed/k2_tabs_2026_11_04/{re.escape(name)})", c)
                assert path and (db.REPO_ROOT / path.group(1)).is_file(), name
            assert "--grade K2" in c and "--section A" in c and "--undecided 2026-12-07=" in c


@pytest.mark.parametrize(
    "run, actor, staff, said",
    [
        ("nothing", "someone", STAFF, "no run called"),
        ("dry; rm -rf /", "someone", STAFF, "no run called"),
        ("apply", "nobody", STAFF, "not on the list"),
        ("apply", "someone", "", "not on the list"),
        ("apply", "someone", "not json", "not on the list"),
        ("apply", "someone", json.dumps({"someone": "a;b@x.invalid"}), "not an email"),
    ],
)
def test_an_unknown_run_or_a_person_not_on_the_list_is_refused_before_anything_is_written(
    run, actor, staff, said
):
    with pytest.raises(SystemExit, match=said):
        cmd.commands(run, actor, staff)


def test_no_run_carries_a_flag_outside_the_known_ones():
    allowed = {
        "--frame",
        "--spans",
        "--planner",
        "--calendar",
        "--section",
        "--grade",
        "--undecided",
        "--apply",
    }
    for run in cmd.RUNS:
        for c in lines(run):
            assert {w for w in c.split() if w.startswith("--")} <= allowed, (run, c)


def test_the_list_of_people_is_a_repository_variable_not_a_file_in_git():
    text = SCRIPT.read_text() + WORKFLOW.read_text()
    assert not re.search(r"[\w.+-]+@[\w-]+\.\w", text.replace("@school.invalid", "")), (
        "no email in the repository"
    )
    assert "vars.CURRICULUM_STAFF" in WORKFLOW.read_text()


def _flow():
    return yaml.safe_load(WORKFLOW.read_text())


def test_the_workflow_is_a_manual_choice_of_the_fixed_runs_and_nothing_else():
    flow = _flow()
    on = flow.get("on") or flow[True]
    assert list(on) == ["workflow_dispatch"], "only by hand"
    inputs = on["workflow_dispatch"]["inputs"]
    assert list(inputs) == ["run"] and inputs["run"]["type"] == "choice"
    assert inputs["run"]["options"] == list(cmd.RUNS), "the choice and the allowlist are one list"


def test_it_can_read_the_repository_and_nothing_more_and_two_runs_never_overlap():
    flow = _flow()
    assert flow["permissions"] == {"contents": "read"}
    assert (
        flow["concurrency"]["group"] == "timetable-run" and flow["concurrency"]["cancel-in-progress"] is False
    )


def test_no_input_or_person_is_written_into_a_shell_script_only_passed_as_environment():
    for job in _flow()["jobs"].values():
        for step in job["steps"]:
            assert "${{" not in step.get("run", ""), step.get("name")


def test_the_person_is_the_one_who_dispatched_or_re_ran_it():
    env = next(
        st["env"] for j in _flow()["jobs"].values() for st in j["steps"] if "ACTOR" in st.get("env", {})
    )
    assert "github.triggering_actor" in env["ACTOR"]


def test_the_loop_over_the_commands_does_not_let_ssh_swallow_the_commands_still_to_run():
    script = next(
        st["run"]
        for j in _flow()["jobs"].values()
        for st in j["steps"]
        if "while IFS= read" in st.get("run", "")
    )
    assert "ssh -n" in script
