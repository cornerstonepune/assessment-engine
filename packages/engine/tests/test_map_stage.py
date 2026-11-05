"""M1-11: the mapping agents' eval spends from the same campaign, and its stages govern it
(goals/m1-11-k2-complete-v1.yaml). `engine eval curriculum_map` is the held-out score ("held_out"); with `--dev` it is the
dev set ("dev_eval"); `--validate-version` names the checker's version, as `--version` names the proposer's."""

from typer.testing import CliRunner

from engine import cli
from engine.adapters import llm
from engine.checks import evals
from engine.w1_bank import map_agents

GOOD = {"n": 427.0, "skill_all_right": 1.0, "skill_found": 1.0, "auto_passed": 1.0}


class Conn:
    pass


def test_every_question_of_the_agents_goes_through_the_adapter_with_its_version_and_its_stage(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(
        llm, "generate", lambda conn, purpose, variables, **k: seen.append({"purpose": purpose, **k}) or {}
    )
    ask = map_agents.model_ask(Conn(), 1, 2, stage="dev_eval")  # type: ignore[arg-type]
    ask(map_agents.PROPOSE, "A", {})
    ask(map_agents.VALIDATE, "A", {})
    assert seen == [
        {"purpose": map_agents.PROPOSE, "version": 1, "stage": "dev_eval", "about": "A"},
        {"purpose": map_agents.VALIDATE, "version": 2, "stage": "dev_eval", "about": "A"},
    ]


def test_without_a_stage_the_agents_ask_as_they_always_did(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(llm, "generate", lambda conn, purpose, variables, **k: seen.append(k) or {})
    map_agents.model_ask(Conn(), None, None)(map_agents.PROPOSE, "A", {})  # type: ignore[arg-type]
    assert seen == [{"version": None, "stage": None, "about": "A"}]


def _run(monkeypatch, *args):
    got: dict = {}

    def fake_ask(conn, propose_version=None, validate_version=None, stage=None, say=None):
        got["says"] = say is not None
        got.update(propose=propose_version, validate=validate_version, stage=stage)
        return lambda *a, **k: {}

    def fake_evaluate(conn, ask, band="", dev=False):
        got["dev"] = dev
        return GOOD

    monkeypatch.setattr(evals, "model_ask", fake_ask)
    monkeypatch.setattr(evals.cli_map, "evaluate", fake_evaluate)
    result = CliRunner().invoke(cli.app, ["eval", "curriculum_map", *args])
    return result, got


def test_the_held_out_score_is_the_held_out_stage_and_asks_for_the_versions_it_is_given(monkeypatch):
    result, got = _run(monkeypatch, "--version", "1", "--validate-version", "2")
    assert result.exit_code == 0, result.output
    assert got == {"propose": 1, "validate": 2, "stage": "held_out", "dev": False, "says": True}


def test_the_dev_set_is_the_dev_eval_stage(monkeypatch):
    result, got = _run(monkeypatch, "--dev", "--version", "1", "--validate-version", "2")
    assert result.exit_code == 0, result.output
    assert got == {"propose": 1, "validate": 2, "stage": "dev_eval", "dev": True, "says": True}


def test_with_no_versions_named_the_active_rows_answer_as_before(monkeypatch):
    result, got = _run(monkeypatch)
    assert result.exit_code == 0 and got["propose"] is None and got["validate"] is None


def test_every_scorer_engine_eval_can_call_takes_the_same_three_arguments():
    import inspect

    for purpose, scorer in evals.BY_VERSION.items():
        inspect.signature(scorer).bind(
            1, False, 0
        )  # TypeError here names the scorer that would break `engine eval`
        assert purpose
