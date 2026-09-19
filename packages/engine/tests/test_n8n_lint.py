"""n8n never thinks (CLAUDE.md rule 3) — and `n8n/lint.py` is what keeps that true.

A linter nobody has seen fail is a linter nobody should trust, so each test breaks the real
exported workflow in one specific way and expects it caught. The last test runs the linter over
what is actually committed, which is the check gate 5 records.
"""

import json
import sys

import pytest

from engine import db

sys.path.insert(0, str(db.REPO_ROOT / "n8n"))
import lint

WORKFLOWS = sorted((db.REPO_ROOT / "n8n" / "workflows").glob("*.json"))


@pytest.fixture
def f1():
    return json.loads((db.REPO_ROOT / "n8n" / "workflows" / "f1-build-the-bank.json").read_text())


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_committed_workflow_passes(path):
    assert lint.problems(json.loads(path.read_text())) == []


def test_a_code_node_is_refused(f1):
    f1["nodes"].append(
        {
            "name": "Decide",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "parameters": {"jsCode": "return items"},
        }
    )
    assert any("thinking node" in p for p in lint.problems(f1))


def test_a_language_model_node_is_refused(f1):
    f1["nodes"].append(
        {"name": "Think", "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 3, "parameters": {}}
    )
    assert any("thinking node" in p for p in lint.problems(f1))


def test_prompt_text_in_a_request_body_is_refused(f1):
    http = next(n for n in f1["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")
    http["parameters"]["jsonBody"] = "You are a maths teacher. Return JSON only."
    assert any("prompt" in p for p in lint.problems(f1))


def test_a_literal_credential_in_an_auth_header_is_refused(f1):
    http = next(n for n in f1["nodes"] if n["type"] == "n8n-nodes-base.httpRequest")
    http["parameters"]["headerParameters"] = {
        "parameters": [{"name": "X-Engine-Key", "value": "sk-live-abcdefgh12345"}]
    }
    assert lint.problems(f1) != []


def test_an_expression_in_an_auth_header_is_fine(f1):
    """A reference to a credential is not a credential. The Idempotency-Key header the real flow
    sends is an expression, and must not be mistaken for a secret."""
    http = next(n for n in f1["nodes"] if n["name"] == "Top up the bank")
    http["parameters"]["headerParameters"] = {
        "parameters": [{"name": "Authorization", "value": "={{ $credentials.token }}"}]
    }
    assert lint.problems(f1) == []


def test_a_workflow_with_no_trigger_is_refused(f1):
    f1["nodes"] = [n for n in f1["nodes"] if "Trigger" not in n["type"] and "webhook" not in n["type"]]
    assert "no trigger node" in lint.problems(f1)


def test_a_sticky_note_may_hold_long_prose(f1):
    """Documentation on the canvas is not a rule: nothing executes it. The real flow's own note
    explains why the flow is boring, and the linter must not flag it."""
    note = next(n for n in f1["nodes"] if n["type"] == "n8n-nodes-base.stickyNote")
    note["parameters"]["content"] = "## A very long explanation\n\n" + ("word " * 300)
    assert lint.problems(f1) == []


def test_the_flow_only_reaches_the_engine_and_the_mail_server(f1):
    """Rule 3 in its positive form: every HTTP call goes to the engine. A workflow that calls a
    model vendor directly has moved the thinking back into n8n by another route."""
    urls = [n["parameters"]["url"] for n in f1["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
    assert urls and all(u.startswith("http://engine:8000/") for u in urls), urls
