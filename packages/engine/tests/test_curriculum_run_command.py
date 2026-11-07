"""The fixed commands the `curriculum run` workflow can run on the server (.github/curriculum/command.py).

Nobody can run the K2 drafting commands on the box by hand, so a manual workflow does, from a choice of FIXED runs. Free
text never reaches the shell: the run is a choice checked against a list here, the person who runs it is looked up in a
repository variable (never typed), and the cap and the order of the stages stay in the engine (adapters/llm_budget.py),
so this file can raise no limit. Dispatching the workflow is the go for a spend; a run that spends nothing says so.
"""

import importlib.util
import json
import re

import pytest
import yaml

from engine.core import db

SCRIPT = db.REPO_ROOT / ".github" / "curriculum" / "command.py"
spec = importlib.util.spec_from_file_location("curriculum_command", SCRIPT)
cmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmd)
WORKFLOW = db.REPO_ROOT / ".github" / "workflows" / "curriculum-run.yml"
STAFF = json.dumps({"someone": "someone@school.invalid"})


def lines(run, actor="someone", staff=STAFF):
    return cmd.commands(run, actor, staff)


def test_the_forecast_makes_no_call_and_needs_nobody_to_have_run_it():
    got = lines("forecast", actor="", staff="")
    assert got and all("--dry-run" in c or "--estimate" in c for c in got), (
        "each is a count or a price, never a call"
    )
    assert all("--by" not in c for c in got), "a forecast is a read; it keeps no row"
    assert cmd.RUNS["forecast"]["spends"] is False


def test_the_key_check_prints_whether_the_key_is_there_and_never_the_key():
    (c,) = lines("key", actor="", staff="")
    assert "ANTHROPIC_API_KEY" in c and "bool(" in c and "print(os.getenv" not in c
    assert cmd.RUNS["key"]["spends"] is False


@pytest.mark.parametrize("run", [r for r, v in cmd.RUNS.items() if v["spends"]])
def test_a_run_that_spends_is_for_a_named_person_and_its_page_commands_name_their_stage_and_who(run):
    for c in lines(run):
        if c.startswith("engine curriculum map-probe"):
            assert c == "engine curriculum map-probe --version 3", (
                c
            )  # its stage, dev_eval, is fixed in the engine
        elif c.startswith("engine curriculum"):
            assert "--stage" in c and c.endswith("--by someone@school.invalid"), c
        else:
            assert c.startswith("engine eval curriculum_map"), (
                c
            )  # the eval takes its stage from --dev, in the engine


def test_the_map_evals_are_the_two_stages_of_the_mapping_agents():
    assert lines("map_dev")[0].startswith("engine eval curriculum_map --dev --version 3 --validate-version 2")
    assert lines("map_held_out")[0].startswith("engine eval curriculum_map --version 3 --validate-version 2")
    assert "--dev" not in lines("map_held_out")[0]


def test_the_held_out_replay_reads_the_kept_replies_free_and_the_proposing_run_is_priced_before_it_is_paid():
    assert cmd.RUNS["map_replay_held_out"] == {
        "spends": False,
        "commands": [["engine", "curriculum", "map-replay", "--stage", "held_out"]],
    }
    (paid,) = lines("map_propose")
    assert paid == (
        "engine curriculum propose --stage draft --version 3 --validate-version 2 --apply --by someone@school.invalid"
    ), (
        "proposed for the gaps from the draft stage, at the versions the held-out eval scored, recorded by the dispatcher"
    )
    assert cmd.RUNS["map_propose"]["spends"] is True
    assert [
        "engine",
        "curriculum",
        "propose",
        "--version",
        "3",
        "--validate-version",
        "2",
        "--estimate",
    ] in cmd.RUNS["forecast"]["commands"], "the forecast prices the proposing run without making a call"


def test_the_analysis_of_the_passes_is_a_free_run_that_makes_no_call():
    assert cmd.RUNS["map_why"] == {"spends": False, "commands": [["engine", "curriculum", "map-why"]]}


def test_the_page_runs_are_the_dev_stage_with_a_limit_and_the_draft_stage_without():
    dev, full = lines("draft_dev")[0], lines("draft_all")[0]
    assert "--stage dev_eval" in dev and "--dev" in dev and "--limit" not in dev
    assert "--stage draft" in full and "--limit" not in full
    assert lines("materials_all")[0].startswith("engine curriculum materials --stage draft")


@pytest.mark.parametrize(
    "run, actor, staff, said",
    [
        ("nothing", "someone", STAFF, "no run called"),
        ("forecast; rm -rf /", "someone", STAFF, "no run called"),
        ("map_dev", "nobody", STAFF, "not on the list"),
        ("map_dev", "someone", "", "not on the list"),
        ("map_dev", "someone", "not json", "not on the list"),
        ("draft_dev", "someone", json.dumps({"someone": "a;b@x.invalid"}), "not an email"),
        ("draft_dev", "someone", json.dumps({"someone": "a b@x.invalid"}), "not an email"),
        ("draft_dev", "someone", json.dumps({"someone": "$(id)@x.invalid"}), "not an email"),
        ("draft_dev", "someone", json.dumps({"someone": "-x@x.invalid"}), "not an email"),
    ],
)
def test_an_unknown_run_or_a_person_not_on_the_list_or_an_email_with_shell_in_it_is_refused(
    run, actor, staff, said
):
    with pytest.raises(SystemExit, match=said):
        cmd.commands(run, actor, staff)


def test_the_list_of_people_is_a_repository_variable_not_a_file_in_git():
    text = SCRIPT.read_text() + WORKFLOW.read_text()
    assert not re.search(r"[\w.+-]+@[\w-]+\.\w", text.replace("@school.invalid", "")), (
        "no email in the repository"
    )
    assert "vars.CURRICULUM_STAFF" in WORKFLOW.read_text()


def test_every_stage_a_run_names_is_a_stage_of_the_campaign_whose_cap_and_order_the_engine_holds():
    seeded = next(
        c
        for c in json.loads((db.REPO_ROOT / "supabase/seed/config.json").read_text())["config"]
        if c["key"] == "llm.campaigns"
    )["value"]["m1-11"]
    for run in cmd.RUNS:
        for c in lines(run, staff=STAFF):
            stage = re.search(r"--stage (\w+)", c)
            if stage:
                assert stage.group(1) in seeded["stages"], c


def test_no_run_can_carry_a_flag_that_changes_a_limit_only_the_known_ones_with_their_known_values():
    """The cap, margin, stage caps and order are config the engine reads; a run is only ever these flags."""
    allowed = {
        "--stage",
        "--dry-run",
        "--by",
        "--dev",
        "--version",
        "--validate-version",
        "--tranche",
        "--settings",
        "--use-kept",  # reads a draft already paid for; it raises no limit
        "--estimate",  # counts and prices; it calls nothing
        "--apply",  # records the proposals (only with --by); it raises no limit
    }  # no --limit: the size is a row
    for run in cmd.RUNS:
        for c in lines(run, staff=STAFF):
            words = c.split()
            if words[:2] == ["python", "-c"]:
                continue
            flags = [w for w in words if w.startswith("--")]
            assert set(flags) <= allowed, (run, flags)
    assert re.search(r"\bcap\b", SCRIPT.read_text().lower()) is None, "no limit is named, let alone set, here"


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
    assert flow["concurrency"]["group"] and flow["concurrency"]["cancel-in-progress"] is False


def test_no_input_or_person_is_written_into_a_shell_script_only_passed_as_environment():
    for job in _flow()["jobs"].values():
        for step in job["steps"]:
            script = step.get("run", "")
            assert "${{" not in script, (
                f"an expression inside a script is how text reaches a shell: {script[:60]!r}"
            )


def test_the_person_is_the_one_who_dispatched_or_re_ran_it_not_the_first_to_start_the_workflow():
    env = next(
        st["env"] for job in _flow()["jobs"].values() for st in job["steps"] if "ACTOR" in st.get("env", {})
    )
    assert "github.triggering_actor" in env["ACTOR"], "a re-run by someone else is that someone else"


def test_the_loop_over_the_commands_does_not_let_ssh_swallow_the_commands_still_to_run():
    script = next(
        st["run"]
        for job in _flow()["jobs"].values()
        for st in job["steps"]
        if "while IFS= read" in st.get("run", "")
    )
    assert "ssh -n" in script, "ssh reads the loop's stdin unless it is given -n"


def test_the_tranche_run_drafts_the_next_pages_in_the_draft_stage_and_the_size_is_a_row_not_text():
    (c,) = lines("draft_tranche")
    assert c == "engine curriculum draft --stage draft --tranche --by someone@school.invalid"
    assert cmd.RUNS["draft_tranche"]["spends"] is True and "--limit" not in c


def test_loading_the_settings_is_a_fixed_command_that_spends_nothing_and_needs_no_person():
    assert lines("load_settings") == ["engine load --settings"]
    assert cmd.RUNS["load_settings"]["spends"] is False
