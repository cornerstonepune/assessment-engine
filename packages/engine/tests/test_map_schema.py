"""One bad reply costs one item, not the run (goals/m1-11c-one-bad-reply-costs-one-item.yaml).

2026-11-04, the first real model call: the mapping proposer (Sonnet 5.5) added a field its schema forbids
("confidence_note"), the reply was refused, and the whole eval stopped after 8 paid calls. The schema is only asked for in
the prompt (the adapter does not constrain the vendor), so a model may add a field. The validation stays strict; what
changes is that the prompt says "no other fields", a refused reply is one item left for a person, and the run stops only
when replies keep breaking in a row.
"""

import json
import os

import jsonschema
import pytest

from engine.adapters import llm
from engine.core import db
from engine.w1_bank import map_agents
from engine.w1_bank.map_agents import PROPOSE, VALIDATE, model_ask, propose, read_band
from tests.test_map_ledger import RULES, _band

SEED = db.REPO_ROOT / "supabase" / "seed"
PROMPTS = json.loads((SEED / "prompts.json").read_text())["prompts"]
GOOD = {
    "skills": ["NUM.CNT.01"],
    "objective_code": "",
    "objective_text": "",
    "levels": {},
    "confidence": 0.9,
    "reason": "counting",
}
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def row(purpose, version):
    return next(p for p in PROMPTS if p["purpose"] == purpose and p["version"] == version)


def test_the_proposers_schema_stays_strict_a_good_reply_passes_an_extra_or_missing_field_does_not():
    schema = row("curriculum_map_propose", 2)["json_schema"]
    jsonschema.validate(GOOD, schema)
    with pytest.raises(jsonschema.ValidationError, match="confidence_note"):
        jsonschema.validate({**GOOD, "confidence_note": "fairly sure"}, schema)
    with pytest.raises(jsonschema.ValidationError, match="reason"):
        jsonschema.validate({k: v for k, v in GOOD.items() if k != "reason"}, schema)


def test_the_new_proposer_version_forbids_other_fields_in_words_and_keeps_the_first_as_it_was():
    new, old = row("curriculum_map_propose", 2), row("curriculum_map_propose", 1)
    text = (SEED / new["text_file"]).read_text()
    assert "no other field" in text.lower() and '"reason"' in text, (
        "anything else the model wants to say goes in reason"
    )
    assert "no other field" not in (SEED / old["text_file"]).read_text().lower(), (
        "v1 is left as it was (rule 2)"
    )
    assert (
        new["json_schema"] == old["json_schema"] and new["model"] == old["model"] and new["active"] is False
    )


@pytest.mark.parametrize(
    "purpose, list_name",
    [("k2_page_draft", "pages"), ("k2_page_validate", "verdicts"), ("k2_materials_split", "lists")],
)
def test_a_stray_field_on_one_item_of_a_batched_reply_does_not_fail_the_other_items(purpose, list_name):
    """The batched rows (v3) are judged item by item by code; the schema asks for the list and each item's key."""
    schema = row(purpose, 3)["json_schema"]
    item = {"key": "A", "verdict": "agree", "why": "w", "items": [], "reason": "r"}
    jsonschema.validate({list_name: [item, {**item, "key": "B", "note": "an extra the model liked"}]}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({list_name: [item], "note": "an extra at the top"}, schema)
    with pytest.raises(jsonschema.ValidationError, match="key"):
        jsonschema.validate({list_name: [{"verdict": "agree"}]}, schema)


def test_the_batched_rows_keep_their_earlier_version_and_say_no_other_fields():
    for purpose in ("k2_page_draft", "k2_page_validate", "k2_materials_split"):
        text = (SEED / row(purpose, 3)["text_file"]).read_text().lower()
        assert "no other field" in text, purpose
        assert row(purpose, 3)["active"] is False and row(purpose, 3)["model"] == row(purpose, 2)["model"]


@needs_db
def test_a_reply_that_breaks_its_schema_is_that_activity_left_for_a_person_and_the_others_go_on(conn_band):
    conn, t = conn_band
    b = read_band(conn, t, "KX")

    def ask(purpose, about, variables):
        if (purpose, about) == (PROPOSE, "ACT-KX-0101"):
            raise llm.LLMSchemaError(
                "curriculum_map_propose output failed its schema: 'confidence_note' was unexpected"
            )
        if purpose == PROPOSE:
            return {**GOOD, "skills": []}
        return {"verdict": "agree", "why": "ok"}

    made = {(p.kind, p.subject_code): p for p in propose(b, sorted(b.gaps), ask, RULES)}
    bad = made[("skill", "ACT-KX-0101")]
    assert bad.status == "rejected" and bad.confidence == 0.0 and bad.proposal == {}
    # rejected, not needs_person: a person approving an EMPTY skill proposal would confirm "no skill" for the activity
    assert bad.problems == ["the proposer's reply broke its schema, so nothing is proposed for this activity"]
    assert ("skill", "ACT-KX-0102") in made, "the next activity was still asked"


@needs_db
def test_a_checker_reply_that_breaks_its_schema_leaves_that_one_proposal_for_a_person_and_says_why(conn_band):
    conn, t = conn_band
    b = read_band(conn, t, "KX")

    def ask(purpose, about, variables):
        if purpose == VALIDATE:
            raise llm.LLMSchemaError("curriculum_map_validate output failed its schema")
        return {**GOOD, "skills": ["NUM.CNT.01"]}

    made = propose(b, ["ACT-KX-0101"], ask, RULES)
    skill = next(p for p in made if p.kind == "skill")
    assert skill.status == "needs_person", (
        "nothing was found wrong with it: it is not checked, so a person looks"
    )
    assert skill.problems == [] and "the checker's reply broke its schema" in skill.reason


@needs_db
def test_replies_that_keep_breaking_in_a_row_end_the_run_and_a_good_one_starts_the_count_again(
    conn_band, monkeypatch
):
    conn, _ = conn_band
    limit = map_agents._bad_replies_allowed(conn)
    monkeypatch.setattr(llm, "generate", lambda *a, **k: (_ for _ in ()).throw(llm.LLMSchemaError("x")))
    ask = model_ask(conn, 2, 2)
    for _ in range(limit - 1):
        with pytest.raises(llm.LLMSchemaError):
            ask(PROPOSE, "A", {})
    with pytest.raises(llm.LLMError, match="in a row") as stop:
        ask(PROPOSE, "A", {})
    assert not isinstance(stop.value, llm.LLMSchemaError), "the run ends: propose() does not swallow this one"

    fresh = model_ask(conn, 2, 2)
    seq = iter(["bad", "bad", "good", "bad", "bad"])

    def flaky(*a, **k):
        if next(seq) == "bad":
            raise llm.LLMSchemaError("x")
        return {"ok": 1}

    monkeypatch.setattr(llm, "generate", flaky)
    for step in range(5):
        if step == 2:
            assert fresh(PROPOSE, "A", {}) == {"ok": 1}
        else:
            with pytest.raises(llm.LLMSchemaError):
                fresh(PROPOSE, "A", {})


@pytest.fixture
def conn_band():
    with db.connect() as c:
        t = _band(c)
        yield c, t
        c.rollback()


@needs_db
def test_the_count_of_broken_replies_is_kept_for_each_prompt_so_alternating_prompts_cannot_hide_a_broken_one(
    conn_band, monkeypatch
):
    conn, _ = conn_band
    outcomes = iter(["bad", "good", "bad", "good", "bad"])  # proposer: bad; checker: good; proposer: bad; ...

    def alternate(conn_, purpose, *a, **k):
        if next(outcomes) == "bad":
            raise llm.LLMSchemaError("x")
        return {"ok": 1}

    monkeypatch.setattr(llm, "generate", alternate)
    ask = model_ask(conn, 2, 2)
    for purpose in (PROPOSE, VALIDATE, PROPOSE, VALIDATE):
        try:
            ask(purpose, "A", {})
        except llm.LLMSchemaError:
            pass
    with pytest.raises(llm.LLMError, match="in a row"):
        # the proposer's third broken reply in a row, though the checker answered well in between
        monkeypatch.setattr(llm, "generate", lambda *a, **k: (_ for _ in ()).throw(llm.LLMSchemaError("x")))
        ask(PROPOSE, "A", {})
        ask(PROPOSE, "A", {})
        ask(PROPOSE, "A", {})


def test_a_reply_the_batched_schema_lets_through_is_still_judged_bad_by_code_and_never_crashes_the_run():
    """v3 asks the schema for the list and each key; types and completeness are k2_batch's to judge, item by item."""
    from engine.w1_bank import k2_batch as batch

    assert batch.judge_verdicts([{"key": "A", "verdict": 5, "why": "w"}], ["A"]) == (
        {},
        {"A": "verdict is not agree or disagree"},
    )
    assert batch.judge_materials("x", "2 cubes") == ([], []), "items that are not a list are no items"
    assert batch.judge_materials([{"name": 7, "quantity": "ten", "unit": None}], "2 cubes")[0] == []
    good, bad = batch.judge_pages(
        [{"key": "A", "objective": 3, "steps": ["a"], "level_0": None}], {"A": ["objective"]}
    )
    assert good == {} and bad == {"A": "objective is empty"}
