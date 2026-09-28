"""The curriculum crosswalk, started from the documents in hand (goals/crosswalk-start.yaml, ADR 0041).

Nimish, 2026-09-28: "no approver needs to actually write … have a proper prompt that we can align on, which creates
these learning objectives in a certain way with a consistent thought process … a sample which you can send to
Akanksha, which becomes an approval mechanism for the curriculum structure. At least start building the entire data
structure and the information structure that you have from the documents that you have already downloaded, even if
they are not from the Cambridge official website. Once I have that, we can just compare once I have the real
documents also". And earlier the same day: "What should the child be able to do at what age should be our baseline".

These tests read the tracked docs/crosswalk/ files that research/crosswalk_build.py writes, so no PDF, no network and
no database is needed.
"""

import copy
import importlib
import json
import sys

import pytest

from engine.core import db

RESEARCH = db.REPO_ROOT / "research"
CROSSWALK = db.REPO_ROOT / "docs" / "crosswalk"


def research(name):
    if str(RESEARCH) not in sys.path:
        sys.path.insert(0, str(RESEARCH))
    return importlib.import_module(name)


checks, compare, decisions, drafts, views = (
    research(m)
    for m in (
        "crosswalk_checks",
        "crosswalk_compare",
        "crosswalk_decisions",
        "crosswalk_drafts",
        "crosswalk_views",
    )
)


@pytest.fixture(scope="module")
def t():
    return {p.stem: json.loads(p.read_text()) for p in (CROSSWALK / "tables").glob("*.json")}


@pytest.fixture(scope="module")
def design():
    return json.loads((CROSSWALK / "design.json").read_text())


@pytest.fixture(scope="module")
def objectives():
    return json.loads((db.REPO_ROOT / "supabase/seed/registry.json").read_text())["learning_objectives"]


@pytest.fixture(scope="module")
def draft():
    return json.loads((CROSSWALK / "drafts" / "math-number-8.json").read_text())


def test_every_statement_in_the_documents_in_hand_is_a_row_with_its_page_level_and_document(t):
    assert checks.statements(t) == []
    assert checks.counts(t) == []  # as many rows as the importers found word for word on their pages
    frameworks = {f["code"] for f in t["framework"]}
    assert {
        "NCF-SE-2023",
        "NCERT-LO-2017",
        "CAM-PRI-MAT-0096",
        "CAM-PRI-ENG-0058",
        "CAM-PRI-SCI-0097",
    } <= frameworks
    learning = [s for s in t["framework_statement"] if s["kind"] not in ("strand", "substrand", "note")]
    assert len(learning) > 2700
    assert all(s["pdf_page"] >= 1 and ((s["text"] or "").strip() or s.get("text_sha256")) for s in learning)


def test_the_cambridge_copies_are_recorded_as_copies_with_their_address_and_fingerprint(t):
    sources = {s["framework"]: s for s in json.loads((CROSSWALK / "sources.json").read_text())}
    cambridge = [d for d in t["framework_document"] if d["framework_code"].startswith("CAM-")]
    assert len(cambridge) == 3
    for d in cambridge:
        assert d["provenance"] == "third_party_copy"
        assert d["url"].startswith("https://") and len(d["sha256"]) == 64 and d["bytes"] > 0
        assert sources[d["framework_code"]]["kind"] == "copy"
        assert sources[d["framework_code"]]["sha256"] == d["sha256"]
    # this repository is public, and Cambridge lets a registered centre copy its words for internal use only: the
    # tracked rows keep each statement's place and a fingerprint of its words; the words stay in the school's copy
    closed = [
        s
        for s in t["framework_statement"]
        if s["framework_code"].startswith("CAM-") and s["kind"] not in ("strand", "substrand")
    ]
    assert len(closed) == 1190 and all(s["text"] is None and len(s["text_sha256"]) == 64 for s in closed)
    assert all(f["text_in_repo"] is False for f in t["framework"] if f["code"].startswith("CAM-"))
    ncf = next(d for d in t["framework_document"] if d["framework_code"] == "NCF-SE-2023")
    assert ncf["provenance"] == "publisher" and ncf["url"].startswith("https://ncert.nic.in/")


def test_a_copy_and_the_official_file_are_compared_statement_by_statement():
    copy_rows = [
        {"code": "3Np.01", "text": "Understand place value.", "items": []},
        {"code": "3Np.02", "text": "Multiply by 10.", "items": []},
        {
            "code": "3Ni.02",
            "text": "Understand addition as:",
            "items": ["counting on", "combining two sets."],
        },
    ]
    official = [
        {"code": "3Np.01", "text": "Understand  place value.", "items": []},
        {"code": "3Ni.02", "text": "Understand addition as:", "items": ["counting on", "combining sets."]},
        {"code": "3Np.06", "text": "A new objective.", "items": []},
    ]
    diff = compare.compare(copy_rows, official)
    assert diff["same"] == ["3Np.01"]  # whitespace is not a difference; words are
    assert [c["code"] for c in diff["changed"]] == ["3Ni.02"]
    assert diff["only_in_copy"] == ["3Np.02"] and diff["only_in_official"] == ["3Np.06"]
    assert compare.compare(copy_rows, copy_rows)["changed"] == []


def test_age_is_the_anchor_every_level_and_step_has_ages_and_each_objective_sits_at_its_grades_age(t, design):
    assert all(
        lv["age_from"] < lv["age_to"] and lv["age_basis"] and lv["quote"] for lv in t["framework_level"]
    )
    ncf = {
        lv["code"]: (lv["age_from"], lv["age_to"])
        for lv in t["framework_level"]
        if lv["framework_code"] == "NCF-SE-2023"
    }
    assert ncf == {"Foundational": (3, 8), "Preparatory": (8, 11), "Middle": (11, 14), "Secondary": (14, 18)}
    steps = {s["code"]: s for s in t["progression_step"]}
    first = design["grade_age"]["grade_1_from"]
    los = {
        o["code"]: o
        for o in json.loads((db.REPO_ROOT / "supabase/seed/registry.json").read_text())["learning_objectives"]
    }
    for p in t["objective_step"]:
        assert steps[p["step_code"]]["age_from"] == first + int(los[p["lo_code"]]["band"][1:]) - 1
    at_8 = {
        (lv["framework_code"], lv["code"])
        for lv in t["framework_level"]
        if lv["age_from"] <= 8 < lv["age_to"]
    }
    assert {
        ("NCF-SE-2023", "Preparatory"),
        ("NCERT-LO-2017", "Class 3"),
        ("CAM-PRI-MAT-0096", "Stage 4"),
    } <= at_8


def test_every_school_objective_is_placed_on_a_strand_or_waits_for_the_method_and_none_is_lost(
    t, objectives, design
):
    assert checks.ladders(t, objectives, design) == []
    placed = {p["lo_code"] for p in t["objective_step"]}
    waiting = {w["lo_code"] for w in t["objective_waiting"]}
    assert placed | waiting == {o["code"] for o in objectives if o["band"].startswith("G")}
    assert not placed & waiting


def test_the_drafting_method_is_one_prompt_and_a_draft_that_breaks_it_is_refused(t, draft):
    assert drafts.check(draft, t) == []
    allowed, never = drafts.words()  # read from the method itself
    assert "understands" in never and "reads" in allowed
    bad = copy.deepcopy(draft)
    first = bad["objectives"][0]
    first["what_we_say"] = "Understands " + first["what_we_say"]
    first["alignments"][0]["relation"] = "similar"
    first["alignments"].append(
        {"framework_code": "CAM-PRI-MAT-0096", "statement_code": "6Ni.04", "relation": "meets", "reason": "x"}
    )
    bad["descriptors"] = bad["descriptors"][:3]
    faults = " | ".join(drafts.check(bad, t))
    assert "not what a child does" in faults and "uses 'understands'" in faults
    assert "relation 'similar'" in faults and "too far from the step's age" in faults
    assert "the rubric has lines for" in faults


def test_every_cambridge_objective_at_the_steps_age_is_aligned_or_listed_as_not_covered(t, draft):
    bad = copy.deepcopy(draft)
    bad["not_covered"] = [g for g in bad["not_covered"] if g["statement_code"] != "3Np.04"]
    assert any("3Np.04" in f and "neither aligned nor listed" in f for f in drafts.check(bad, t))


def test_nobody_writes_the_sheet_asks_only_for_a_decision_and_only_the_signatory_decides(t):
    ids = json.loads((CROSSWALK / "review" / "math-number-8.rows.json").read_text())
    header = ["Row", "What we say (draft)", "Decision", "Comment"]
    grid = [
        ["The curriculum crosswalk: a sample for approval"],
        header,
        ["O03", "Reads and writes numbers to 1000 …", "Approve", ""],
        ["R4", "Alone and consistently …", "Change", "Say 'regroup' as well as 'exchange'"],
        ["G14", "Leave it out at this step", "Reject", ""],
        ["O05", "Adds and subtracts …", "", ""],
    ]
    got, faults = decisions.read_decisions(
        [("sheet", grid)], ids, "Akanksha", "test.csv", now="2026-09-28T08:00:00Z"
    )
    assert faults == []
    by_row = {}
    for d in got:
        by_row.setdefault(d["source"].split("row ")[-1], set()).add(d["decision"])
    assert by_row == {"O03": {"approved"}, "R4": {"revised"}, "G14": {"rejected"}}  # O05 stays a proposal
    assert len([d for d in got if d["source"].endswith("O03")]) == len(ids["O03"]) > 5
    wrong, faults = decisions.read_decisions(
        [("sheet", [header, ["O03", "", "Maybe", ""]])], ids, "Akanksha", "t"
    )
    assert wrong == [] and faults
    with pytest.raises(SystemExit):
        decisions.decisions("MATH.NUMBER.8", "unused.csv", "Somebody else")


def test_the_sample_sent_to_akanksha_becomes_the_approval_of_the_structure(t):
    sent = json.loads((CROSSWALK / "review" / "math-number-8.sent.json").read_text())
    ids = json.loads((CROSSWALK / "review" / "math-number-8.rows.json").read_text())
    claims = {c["id"] for c in t["claim"]}
    assert set(sent["rows"]) <= set(ids) and all(set(ids[r]) <= claims for r in sent["rows"])
    before = next(r for r in views.readiness(t) if r["step"] == "MATH.NUMBER.8")
    assert before["statement_approved"] == 0 and not before["outcome_approved"]
    approve = [
        {
            "claim_id": c,
            "decision": "approved",
            "decided_by": "Akanksha",
            "decided_at": "2026-09-29T09:00:00Z",
        }
        for r in sent["rows"]
        for c in ids[r]
    ]
    after_t = dict(t, claim_decision=approve)
    assert checks.claims(after_t) == []
    after = next(r for r in views.readiness(after_t) if r["step"] == "MATH.NUMBER.8")
    assert after["statement_approved"] == 10 and after["outcome_approved"] and after["rubric_complete"]


def test_a_model_never_signs_every_claim_has_one_proposer_and_nothing_is_decided_yet(t):
    assert checks.claims(t) == []
    by_prompt = [c for c in t["claim"] if c["prompt_purpose"]]
    assert by_prompt and all(c["prompt_purpose"] == "crosswalk_draft" for c in by_prompt)
    assert t["claim_decision"] == [] or all(d["decided_by"] == "Akanksha" for d in t["claim_decision"])
    assert {s["educator"] for s in t["signatory"]} == {"Akanksha"}
