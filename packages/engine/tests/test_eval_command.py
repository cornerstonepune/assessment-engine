"""The `engine eval` command the engine-eval workflow runs on the server (.github/eval/command.py). Run 40469097359
(2026-10-27) built it with every input, used or not, so `english_generate --version 1` also carried the parent
report's two options; and its version list was typed by hand, so a new version could not be scored until it was."""

import importlib.util
import json

import pytest
import yaml

from engine.core import db

SCRIPT = db.REPO_ROOT / ".github" / "eval" / "command.py"
spec = importlib.util.spec_from_file_location("eval_command", SCRIPT)
cmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmd)
SEED = json.loads((db.REPO_ROOT / "supabase/seed/prompts.json").read_text())["prompts"]


def test_a_purpose_is_passed_only_the_options_it_uses():
    assert cmd.command("english_generate", "2", "", "") == [
        "engine",
        "eval",
        "english_generate",
        "--version",
        "2",
    ]
    assert cmd.command("parent_report", "12", "5", "") == [
        "engine", "eval", "parent_report", "--version", "12", "--review-version", "5"
    ]  # fmt: skip
    assert cmd.command("parent_review", "5", "", "1") == [
        "engine", "eval", "parent_review", "--version", "5", "--jev-version", "1"
    ]  # fmt: skip
    assert cmd.command("parent_review", "", "", "") == [
        "engine",
        "eval",
        "parent_review",
    ]  # its active version


@pytest.mark.parametrize(
    "args, said",
    [
        (("english_generate", "1", "5", ""), "only parent_report"),
        (("english_generate", "", "", "1"), "only parent_review"),
        (("english_generate", "1 ; rm -rf /", "", ""), "a whole number"),
        (("english_generate", "99", "", ""), "no version 99"),
        (("parent_report", "12", "99", ""), "no parent_review version 99"),
        (("nobody", "1", "", ""), "no prompt"),
    ],
)
def test_an_input_the_purpose_cannot_use_is_refused_in_words(args, said):
    with pytest.raises(SystemExit, match=said):
        cmd.command(*args)


def test_every_version_the_seed_holds_can_be_scored_and_none_is_typed_in_the_workflow():
    for r in SEED:
        if r["purpose"] in cmd.PURPOSES:
            assert cmd.command(r["purpose"], str(r["version"]), "", "")[-1] == str(r["version"])
    flow = yaml.safe_load((db.REPO_ROOT / ".github/workflows/engine-eval.yml").read_text())
    inputs = (flow.get("on") or flow[True])["workflow_dispatch"]["inputs"]
    assert set(cmd.PURPOSES) | {"read_with_examples"} == set(inputs["purpose"]["options"])
    for name in ("version", "review_version", "jev_version"):
        assert inputs[name]["type"] == "string" and "options" not in inputs[name]
    run = "\n".join(s.get("run", "") for s in flow["jobs"]["score"]["steps"])
    assert ".github/eval/command.py" in run and "--review-version" not in run
